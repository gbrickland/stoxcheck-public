"""Storage adapters for local memory and transactional Cloud Firestore persistence."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Protocol

from .analytics import aggregate_delta, market_windows, present_aggregate
from .domain import Observation


def document_id(ticker: str, start: datetime) -> str:
    """Build a stable aggregate ID so retries update rather than duplicate a window."""
    return f"{ticker}_{start.strftime('%Y%m%dT%H%M%SZ')}"


class Storage(Protocol):
    def has_seen(self, headline_hash: str) -> bool: ...
    def store(self, observation: Observation, hash_expires_at: datetime) -> bool: ...
    def snapshot(self, ticker: str) -> dict: ...
    def history(self, ticker: str, period: str, limit: int) -> list[dict]: ...


class MemoryStorage:
    """Process-local adapter used only for tests and connection-free development."""

    def __init__(self) -> None:
        self.observations: dict[str, Observation] = {}
        self.hashes: set[str] = set()
        self.aggregates: dict[str, dict[str, dict]] = defaultdict(dict)

    def has_seen(self, headline_hash: str) -> bool:
        return headline_hash in self.hashes

    def store(self, observation: Observation, hash_expires_at: datetime) -> bool:
        """Store once and update every reporting period, mirroring Firestore semantics."""
        if observation.observation_id in self.observations:
            return False
        self.observations[observation.observation_id] = observation
        self.hashes.add(observation.headline_hash)
        for period, (start, end) in market_windows(observation.headline.published_at).items():
            key = document_id(observation.headline.ticker, start)
            delta = aggregate_delta(observation, start, end)
            current = self.aggregates[period].get(key)
            if current is None:
                self.aggregates[period][key] = delta
            else:
                for field, value in delta.items():
                    if field.endswith("_sum") or field.endswith("_count") or field == "headline_count":
                        current[field] += value
                current["model_versions"] = sorted(set(current["model_versions"] + delta["model_versions"]))
        return True

    def snapshot(self, ticker: str) -> dict:
        now = datetime.now(timezone.utc)
        observations = sorted(
            (
                item for item in self.observations.values()
                if item.headline.ticker == ticker and item.expires_at > now
            ),
            key=lambda item: item.headline.published_at,
            reverse=True,
        )[:10]
        summaries = {}
        for period in ("hourly", "daily", "weekly"):
            values = [
                item for item in self.aggregates[period].values()
                if item["ticker"] == ticker
            ]
            latest = max(values, key=lambda item: item["window_start"]) if values else None
            summaries[period] = present_aggregate(latest)
        return {
            "ticker": ticker,
            "generated_at": now,
            "recent_headlines": [item.to_dict() for item in observations],
            **summaries,
        }

    def history(self, ticker: str, period: str, limit: int) -> list[dict]:
        values = [
            present_aggregate(item) for item in self.aggregates[period].values()
            if item["ticker"] == ticker
        ]
        return sorted(values, key=lambda item: item["window_start"], reverse=True)[:limit]


class FirestoreStorage:
    """Production adapter with idempotent observation and aggregate writes."""

    def __init__(self, project: str | None = None) -> None:
        from google.cloud import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter
        self.firestore = firestore
        self.FieldFilter = FieldFilter
        self.db = firestore.Client(project=project or None)

    def has_seen(self, headline_hash: str) -> bool:
        return self.db.collection("recent_headline_hashes").document(headline_hash).get().exists

    def store(self, observation: Observation, hash_expires_at: datetime) -> bool:
        """Atomically record a new observation, its hash and aggregate increments."""
        firestore = self.firestore
        transaction = self.db.transaction()
        observation_ref = self.db.collection("temporary_observations").document(observation.observation_id)
        hash_ref = self.db.collection("recent_headline_hashes").document(observation.headline_hash)

        @firestore.transactional
        def commit(transaction):
            if observation_ref.get(transaction=transaction).exists:
                return False
            transaction.set(observation_ref, observation.to_dict())
            transaction.set(hash_ref, {
                "headline_hash": observation.headline_hash,
                "first_seen_at": observation.retrieved_at,
                "expires_at": hash_expires_at,
            }, merge=True)
            for period, (start, end) in market_windows(observation.headline.published_at).items():
                aggregate_ref = self.db.collection(f"{period}_sentiment").document(
                    document_id(observation.headline.ticker, start)
                )
                delta = aggregate_delta(observation, start, end)
                transaction.set(aggregate_ref, {
                    "ticker": delta["ticker"],
                    "window_start": start,
                    "window_end": end,
                    "headline_count": firestore.Increment(1),
                    "positive_probability_sum": firestore.Increment(delta["positive_probability_sum"]),
                    "neutral_probability_sum": firestore.Increment(delta["neutral_probability_sum"]),
                    "negative_probability_sum": firestore.Increment(delta["negative_probability_sum"]),
                    "sentiment_score_sum": firestore.Increment(delta["sentiment_score_sum"]),
                    "sentiment_score_squared_sum": firestore.Increment(delta["sentiment_score_squared_sum"]),
                    "confidence_sum": firestore.Increment(delta["confidence_sum"]),
                    "positive_count": firestore.Increment(delta["positive_count"]),
                    "neutral_count": firestore.Increment(delta["neutral_count"]),
                    "negative_count": firestore.Increment(delta["negative_count"]),
                    "model_versions": firestore.ArrayUnion(delta["model_versions"]),
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }, merge=True)
            return True

        stored = commit(transaction)
        if stored:
            self.rebuild_snapshot(observation.headline.ticker)
        return stored

    def _latest_aggregate(self, ticker: str, period: str) -> dict | None:
        query = (
            self.db.collection(f"{period}_sentiment")
            .where(filter=self.FieldFilter("ticker", "==", ticker))
            .order_by("window_start", direction=self.firestore.Query.DESCENDING)
            .limit(1)
        )
        documents = list(query.stream())
        return present_aggregate(documents[0].to_dict()) if documents else None

    def rebuild_snapshot(self, ticker: str) -> None:
        now = datetime.now(timezone.utc)
        query = (
            self.db.collection("temporary_observations")
            .where(filter=self.FieldFilter("ticker", "==", ticker))
            .where(filter=self.FieldFilter("expires_at", ">", now))
            .order_by("expires_at", direction=self.firestore.Query.DESCENDING)
            .limit(10)
        )
        headlines = [document.to_dict() for document in query.stream()]
        self.db.collection("latest_stock_snapshots").document(ticker).set({
            "ticker": ticker,
            "generated_at": self.firestore.SERVER_TIMESTAMP,
            "recent_headlines": headlines,
            "hourly": self._latest_aggregate(ticker, "hourly"),
            "daily": self._latest_aggregate(ticker, "daily"),
            "weekly": self._latest_aggregate(ticker, "weekly"),
        })

    def snapshot(self, ticker: str) -> dict:
        document = self.db.collection("latest_stock_snapshots").document(ticker).get()
        return document.to_dict() if document.exists else {"ticker": ticker, "recent_headlines": []}

    def history(self, ticker: str, period: str, limit: int) -> list[dict]:
        query = (
            self.db.collection(f"{period}_sentiment")
            .where(filter=self.FieldFilter("ticker", "==", ticker))
            .order_by("window_start", direction=self.firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [present_aggregate(document.to_dict()) for document in query.stream()]


def create_storage(backend: str, project: str = "") -> Storage:
    return FirestoreStorage(project) if backend == "firestore" else MemoryStorage()


def stable_hash(*values: str) -> str:
    """Create a case/whitespace-insensitive identifier without storing source text."""
    content = "\x1f".join(value.strip().casefold() for value in values)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
