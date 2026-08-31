"""Environment-driven runtime configuration shared by API and collector processes."""

from __future__ import annotations

import os
from dataclasses import dataclass


STOCKS = {
    # Fixed from the US publicly traded company ranking by market
    # capitalisation on 30 July 2026. This is intentionally not dynamic:
    # changing the research universe would make long-term series incomparable.
    "AAPL": "Apple",
    "NVDA": "Nvidia",
    "GOOG": "Alphabet",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "AVGO": "Broadcom",
    "META": "Meta Platforms",
    "SPCX": "SpaceX",
    "TSLA": "Tesla",
    "LLY": "Eli Lilly",
}



@dataclass(frozen=True)
class Settings:
    """Read deployment settings once, with safe local-development defaults."""
    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "")
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "memory")
    model_path: str = os.getenv(
        "MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "artifacts", "stoxcheck_sentiment_model.joblib")
    )
    stagger_seconds: float = float(os.getenv("STAGGER_SECONDS", "2"))
    observation_ttl_minutes: int = int(os.getenv("OBSERVATION_TTL_MINUTES", "90"))
    hash_ttl_days: int = int(os.getenv("HASH_TTL_DAYS", "7"))
    allowed_origin: str = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")
    force_market_open: bool = os.getenv("FORCE_MARKET_OPEN", "").lower() in {"1", "true", "yes"}
    require_firebase_auth: bool = os.getenv("REQUIRE_FIREBASE_AUTH", "").lower() in {"1", "true", "yes"}

    def validate_collection(self) -> None:
        if not self.finnhub_api_key:
            raise RuntimeError("FINNHUB_API_KEY is required for headline collection.")


settings = Settings()
