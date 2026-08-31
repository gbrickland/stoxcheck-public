"""Roll individual predictions into the hourly, daily and weekly figures."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .domain import Observation

NEW_YORK = ZoneInfo("America/New_York")


def directional_score(observation: Observation) -> float:
    """Return a signed -1..1 score by balancing positive against negative evidence."""
    values = observation.prediction.probabilities
    return values["positive"] - values["negative"]


def market_windows(published_at: datetime) -> dict[str, tuple[datetime, datetime]]:
    """Place a headline into US-market hourly, daily and weekly reporting windows."""
    local = published_at.astimezone(NEW_YORK)
    market_open = datetime.combine(local.date(), time(9, 30), tzinfo=NEW_YORK)
    minutes = max(0, int((local - market_open).total_seconds() // 60))
    hourly_start = market_open + timedelta(minutes=(minutes // 60) * 60)
    market_close = datetime.combine(local.date(), time(16, 0), tzinfo=NEW_YORK)
    hourly_end = min(hourly_start + timedelta(hours=1), market_close)
    daily_start, daily_end = market_open, market_close
    weekly_start_date = local.date() - timedelta(days=local.weekday())
    weekly_start = datetime.combine(weekly_start_date, time(9, 30), tzinfo=NEW_YORK)
    weekly_end = weekly_start + timedelta(days=4, hours=6, minutes=30)
    return {
        "hourly": (hourly_start.astimezone(timezone.utc), hourly_end.astimezone(timezone.utc)),
        "daily": (daily_start.astimezone(timezone.utc), daily_end.astimezone(timezone.utc)),
        "weekly": (weekly_start.astimezone(timezone.utc), weekly_end.astimezone(timezone.utc)),
    }


def aggregate_delta(observation: Observation, start: datetime, end: datetime) -> dict:
    """Describe the atomic increments produced by one newly accepted observation."""
    probabilities = observation.prediction.probabilities
    score = directional_score(observation)
    label = observation.prediction.sentiment
    return {
        "ticker": observation.headline.ticker,
        "window_start": start,
        "window_end": end,
        "headline_count": 1,
        "positive_probability_sum": probabilities["positive"],
        "neutral_probability_sum": probabilities["neutral"],
        "negative_probability_sum": probabilities["negative"],
        "sentiment_score_sum": score,
        "sentiment_score_squared_sum": score * score,
        # A running sum is enough; there is no need to keep the old headline here.
        "confidence_sum": observation.prediction.confidence,
        "positive_count": int(label == "positive"),
        "neutral_count": int(label == "neutral"),
        "negative_count": int(label == "negative"),
        "model_versions": [observation.prediction.model_version],
    }


def present_aggregate(value: dict | None) -> dict | None:
    """Convert stored sums into the stable, browser-facing aggregate representation."""
    if not value or not value.get("headline_count"):
        return None
    count = value["headline_count"]
    score = value["sentiment_score_sum"] / count
    variance = max(0.0, value["sentiment_score_squared_sum"] / count - score * score)
    average_probabilities = {
        "positive": value["positive_probability_sum"] / count,
        "neutral": value["neutral_probability_sum"] / count,
        "negative": value["negative_probability_sum"] / count,
    }
    return {
        **value,
        "average_sentiment": score,
        "sentiment_volatility": variance ** 0.5,
        # Old Firestore rows don't have confidence_sum, so use their strongest class.
        "average_confidence": value.get(
            "confidence_sum",
            max(average_probabilities.values()) * count,
        ) / count,
        "average_probabilities": average_probabilities,
    }
