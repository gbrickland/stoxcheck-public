"""Read and prediction endpoints used by the website. Collector writes stay private."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, StringConstraints

from .config import STOCKS, settings
from .security import SecurityMiddleware, verified_firebase_user
from .storage import create_storage

if TYPE_CHECKING:
    from .model import SentimentModel

# Loading FinBERT is expensive. Normal dashboard reads don't need it.
model: "SentimentModel | None" = None
model_lock = Lock()


def get_model() -> "SentimentModel":
    """Load the model once, safely, on the first manual prediction request."""
    global model
    if model is None:
        with model_lock:
            if model is None:
                from .model import SentimentModel
                model = SentimentModel(settings.model_path)
    return model


app = FastAPI(title="Stoxcheck API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
# Added last so security checks also cover CORS preflights.
app.add_middleware(SecurityMiddleware)
storage = create_storage(settings.storage_backend, settings.google_cloud_project)


HeadlineText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
TargetText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class PredictionRequest(BaseModel):
    # Cap both the batch and each headline so this can't become a huge model request.
    headlines: list[HeadlineText] = Field(min_length=1, max_length=50)
    target: TargetText | None = Field(
        default=None,
        description="Optional company whose sentiment should be classified.",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc), "model_loaded": model is not None}


@app.get("/v1/stocks")
def stocks(_: dict = Depends(verified_firebase_user)) -> dict:
    return {"stocks": [{"ticker": ticker, "company": company} for ticker, company in STOCKS.items()]}


@app.get("/v1/stocks/{ticker}/latest")
def latest(ticker: str, _: dict = Depends(verified_firebase_user)) -> dict:
    """Return the pre-computed website snapshot for one supported stock."""
    ticker = ticker.upper()
    if ticker not in STOCKS:
        raise HTTPException(404, "Unsupported ticker")
    return {**storage.snapshot(ticker), "company": STOCKS[ticker]}


@app.get("/v1/stocks/{ticker}/history")
def history(
    ticker: str,
    period: str = Query("hourly", pattern="^(hourly|daily|weekly)$"),
    limit: int = Query(30, ge=1, le=100),
    _: dict = Depends(verified_firebase_user),
) -> dict:
    ticker = ticker.upper()
    if ticker not in STOCKS:
        raise HTTPException(404, "Unsupported ticker")
    return {"ticker": ticker, "period": period, "values": storage.history(ticker, period, limit)}


@app.post("/v1/predict")
def predict(request: PredictionRequest, _: dict = Depends(verified_firebase_user)) -> dict:
    """Classify manual headlines, optionally from one company's point of view."""
    active_model = get_model()
    predictions = active_model.predict(request.headlines, targets=request.target)
    return {
        "model_version": active_model.version,
        "predictions": [
            {
                "headline": headline,
                "target": request.target,
                "sentiment": result.sentiment,
                "confidence": result.confidence,
                "is_positive": result.is_positive,
                "positive_threshold": result.positive_threshold,
                "probabilities": result.probabilities,
            }
            for headline, result in zip(request.headlines, predictions)
        ],
    }
