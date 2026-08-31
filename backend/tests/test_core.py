"""Fast contract tests for aggregation, stock-universe and deduplication behaviour."""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from stoxcheck import api
from stoxcheck.api import PredictionRequest
from stoxcheck.analytics import directional_score, present_aggregate
from stoxcheck.config import STOCKS
from stoxcheck.domain import Headline, Observation, Prediction
from stoxcheck.storage import MemoryStorage, stable_hash
from stoxcheck.security import MAX_REQUEST_BYTES, SecurityMiddleware


def observation() -> Observation:
    now = datetime(2026, 7, 28, 14, 0, tzinfo=timezone.utc)
    prediction = Prediction(
        sentiment="positive", confidence=.7, is_positive=True, positive_threshold=.3,
        probabilities={"positive": .7, "neutral": .2, "negative": .1}, model_version="1.0.0",
    )
    headline = Headline("finnhub-1", "AAPL", "Apple raises guidance", "Example", "https://example.com/a", now)
    return Observation("obs-1", "hash-1", headline, prediction, now, now + timedelta(minutes=90))


def test_fixed_top_ten_stocks():
    assert len(STOCKS) == 10
    assert tuple(STOCKS) == (
        "AAPL", "NVDA", "GOOG", "MSFT", "AMZN",
        "AVGO", "META", "SPCX", "TSLA", "LLY",
    )


def test_directional_score():
    assert abs(directional_score(observation()) - .6) < 1e-9


def test_storage_is_idempotent_and_updates_all_periods():
    store = MemoryStorage()
    item = observation()
    assert store.store(item, item.retrieved_at + timedelta(days=7))
    assert not store.store(item, item.retrieved_at + timedelta(days=7))
    for period in ("hourly", "daily", "weekly"):
        history = store.history("AAPL", period, 10)
        assert len(history) == 1
        assert history[0]["headline_count"] == 1
        assert abs(history[0]["average_sentiment"] - .6) < 1e-9
        assert abs(history[0]["average_confidence"] - .7) < 1e-9


def test_stable_hash_is_deterministic():
    assert stable_hash("A", "B") == stable_hash(" a ", "b")


def test_prediction_request_bounds_each_headline():
    assert PredictionRequest(headlines=["  Company raises guidance  "]).headlines == ["Company raises guidance"]
    for invalid in ([""], ["x" * 1001], ["valid"] * 51):
        try:
            PredictionRequest(headlines=invalid)
            assert False, "invalid prediction request was accepted"
        except ValidationError:
            pass


def test_security_middleware_headers_and_size_limit():
    small_app = FastAPI()
    small_app.add_middleware(SecurityMiddleware)

    @small_app.post("/echo")
    def echo():
        return {"ok": True}

    client = TestClient(small_app)
    response = client.post("/echo", content=b"{}")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    oversized = client.post("/echo", content=b"x" * (MAX_REQUEST_BYTES + 1))
    assert oversized.status_code == 413


def test_read_api_starts_without_loading_finbert():
    assert api.model is None
    assert api.health()["model_loaded"] is False
    assert len(api.stocks()["stocks"]) == 10


def test_production_auth_rejects_missing_firebase_token():
    """A hidden frontend alone is not security; protected API routes must enforce the token."""
    object.__setattr__(api.settings, "require_firebase_auth", True)
    try:
        client = TestClient(api.app)
        assert client.get("/health").status_code == 200
        response = client.get("/v1/stocks")
        assert response.status_code == 401
        assert "Firebase sign-in token" in response.json()["detail"]
    finally:
        object.__setattr__(api.settings, "require_firebase_auth", False)
