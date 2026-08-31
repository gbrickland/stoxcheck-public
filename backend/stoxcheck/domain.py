"""Small typed records passed between news, model, storage and API boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True)
class Headline:
    """A normalized provider story associated with one tracked stock."""
    provider_id: str
    ticker: str
    title: str
    source: str
    url: str
    published_at: datetime


@dataclass(frozen=True)
class Prediction:
    """The complete model decision retained for aggregation and recent display."""
    sentiment: str
    confidence: float
    is_positive: bool
    positive_threshold: float
    probabilities: dict[str, float]
    model_version: str


@dataclass(frozen=True)
class Observation:
    """A headline and prediction joined with deduplication and expiry metadata."""
    observation_id: str
    headline_hash: str
    headline: Headline
    prediction: Prediction
    retrieved_at: datetime
    expires_at: datetime

    def to_dict(self) -> dict:
        value = asdict(self)
        value.update({
            "ticker": self.headline.ticker,
            "headline": self.headline.title,
            "source": self.headline.source,
            "url": self.headline.url,
            "published_at": self.headline.published_at,
            "sentiment": self.prediction.sentiment,
            "confidence": self.prediction.confidence,
            "probabilities": self.prediction.probabilities,
            "model_version": self.prediction.model_version,
        })
        value.pop("prediction")
        return value
