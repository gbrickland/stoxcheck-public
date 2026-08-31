"""Minimal Finnhub adapter that validates and normalizes company-news responses."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .domain import Headline


class FinnhubClient:
    """Fetch recent stories without leaking provider-specific payloads downstream."""
    base_url = "https://finnhub.io/api/v1/company-news"

    def __init__(self, api_key: str, timeout: int = 15) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def fetch(self, ticker: str, day: date | None = None) -> list[Headline]:
        """Return unique, newest-first headlines for a ticker and two-day date window."""
        day = day or datetime.now(timezone.utc).date()
        query = urlencode({
            "symbol": ticker,
            "from": (day - timedelta(days=1)).isoformat(),
            "to": day.isoformat(),
            "token": self.api_key,
        })
        request = Request(
            f"{self.base_url}?{query}",
            headers={"User-Agent": "Stoxcheck/1.0", "Accept": "application/json"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read())
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(payload["error"])
        if not isinstance(payload, list):
            raise RuntimeError("Finnhub returned an unexpected response.")

        results = {}
        for item in payload:
            title, url = str(item.get("headline", "")).strip(), str(item.get("url", "")).strip()
            source = str(item.get("source", "Unknown source")).strip()
            if not title or not url:
                continue
            provider_id = str(item.get("id", "")) or f"{ticker}-{item.get('datetime')}-{title}"
            results[provider_id] = Headline(
                provider_id=provider_id,
                ticker=ticker,
                title=title,
                source=source,
                url=url,
                published_at=datetime.fromtimestamp(int(item.get("datetime", 0)), tz=timezone.utc),
            )
        return sorted(results.values(), key=lambda item: item.published_at, reverse=True)
