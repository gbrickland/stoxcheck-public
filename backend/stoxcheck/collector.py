"""Scheduled collection job: fetch, deduplicate, classify and persist company news."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from .config import STOCKS, settings
from .domain import Observation
from .market import is_regular_session
from .model import SentimentModel
from .news import FinnhubClient
from .storage import create_storage, stable_hash


def run_collection() -> dict:
    """Run one complete, independently reportable pass over the fixed stock universe."""
    settings.validate_collection()
    if not settings.force_market_open and not is_regular_session():
        return {"status": "skipped", "reason": "US regular market session is closed"}

    started = datetime.now(timezone.utc)
    news = FinnhubClient(settings.finnhub_api_key)
    model = SentimentModel(settings.model_path)
    storage = create_storage(settings.storage_backend, settings.google_cloud_project)
    totals = {"tickers": len(STOCKS), "fetched": 0, "new": 0, "model_predictions": 0, "errors": []}

    # One broken ticker shouldn't throw away the other nine.
    for index, ticker in enumerate(STOCKS):
        try:
            # Take all eligible results. The hashes below catch repeats.
            headlines = news.fetch(ticker)
            totals["fetched"] += len(headlines)
            unseen = []
            for headline in headlines:
                content_hash = stable_hash(headline.provider_id, headline.source, headline.title)
                ticker_hash = stable_hash(ticker, content_hash)
                if not storage.has_seen(ticker_hash):
                    unseen.append((headline, ticker_hash, content_hash))
            # A story can mean different things for different companies, so this cache is
            # only safe inside the current ticker pass.
            unique = {}
            for headline, _, content_hash in unseen:
                unique.setdefault(content_hash, headline.title)
            prediction_cache = {}
            if unique:
                items = list(unique.items())
                predictions = model.predict(
                    [text for _, text in items],
                    targets=STOCKS[ticker],
                )
                totals["model_predictions"] += len(predictions)
                prediction_cache.update({
                    key: result for (key, _), result in zip(items, predictions)
                })
            retrieved_at = datetime.now(timezone.utc)
            for headline, ticker_hash, content_hash in unseen:
                prediction = prediction_cache[content_hash]
                observation = Observation(
                    observation_id=stable_hash(ticker_hash, prediction.model_version)[:40],
                    headline_hash=ticker_hash,
                    headline=headline,
                    prediction=prediction,
                    retrieved_at=retrieved_at,
                    expires_at=retrieved_at + timedelta(minutes=settings.observation_ttl_minutes),
                )
                if storage.store(
                    observation,
                    retrieved_at + timedelta(days=settings.hash_ttl_days),
                ):
                    totals["new"] += 1
        except Exception as error:
            totals["errors"].append({"ticker": ticker, "error": str(error)})
        # Space the calls out to stay friendly to the Finnhub limit.
        if index < len(STOCKS) - 1:
            time.sleep(settings.stagger_seconds)

    totals.update({
        "status": "completed" if not totals["errors"] else "partial",
        "started_at": started.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model.version,
    })
    return totals


def main() -> None:
    print(json.dumps(run_collection(), indent=2))


if __name__ == "__main__":
    main()
