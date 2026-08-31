"""Production inference wrapper for the calibrated FinBERT/sparse ensemble."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .domain import Prediction


class SentimentModel:
    """Serve the calibrated FinBERT + word/character ensemble.

    Both components are loaded when this wrapper is constructed. The collector constructs it at
    startup; the API waits until its first manual prediction. Stock-specific calls append the same
    [TARGET] marker used by the entity-level training datasets.
    """

    def __init__(self, path: str | Path) -> None:
        artifact = joblib.load(Path(path).resolve())
        if artifact.get("model_type") != "finbert_word_character_ensemble":
            raise ValueError("The final backend requires the version 2 FinBERT ensemble artifact.")

        self.sparse_pipeline = artifact["sparse_pipeline"]
        self.threshold = float(artifact["positive_threshold"])
        self.temperature = float(artifact["temperature"])
        self.finbert_weight = float(artifact["finbert_weight"])
        self.max_length = int(artifact["max_length"])
        self.version = artifact["model_version"]
        self.classes = list(artifact["classes"])
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model_name = artifact["finbert_model"]
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.finbert = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.finbert.to(self.device).eval()
        self.finbert_label_index = {
            label.casefold(): index
            for index, label in self.finbert.config.id2label.items()
        }

    @staticmethod
    def _model_text(headline: str, target: str | None) -> str:
        """Apply the entity-aware input convention learned from SEntFiN/FinEntity."""
        headline = " ".join(headline.split())
        if target is None or not target.strip():
            return headline
        return f"{headline} [TARGET] {' '.join(target.split())}"

    def predict(
        self,
        headlines: list[str],
        targets: str | Sequence[str | None] | None = None,
    ) -> list[Prediction]:
        """Classify a batch while preserving aligned optional company targets."""
        if not headlines or any(
            not isinstance(text, str) or not text.strip() for text in headlines
        ):
            raise ValueError("Every headline must be a non-empty string.")

        if isinstance(targets, str) or targets is None:
            target_values = [targets] * len(headlines)
        else:
            target_values = list(targets)
            if len(target_values) != len(headlines):
                raise ValueError("targets must contain one value per headline.")
        if any(target is not None and not isinstance(target, str) for target in target_values):
            raise ValueError("Every target must be a company-name string or null.")

        values = [
            self._model_text(headline, target)
            for headline, target in zip(headlines, target_values)
        ]
        sparse_raw = self.sparse_pipeline.predict_proba(values)
        sparse = np.column_stack([
            sparse_raw[:, np.where(self.sparse_pipeline.classes_ == label)[0][0]]
            for label in self.classes
        ])

        encoded = self.tokenizer(
            values, padding=True, truncation=True, max_length=self.max_length,
            return_tensors="pt",
        ).to(self.device)
        with torch.inference_mode():
            raw = torch.softmax(self.finbert(**encoded).logits, dim=1).cpu().numpy()
        finbert = np.column_stack([
            raw[:, self.finbert_label_index[label]] for label in self.classes
        ])
        logits = np.log(np.clip(finbert, 1e-9, 1.0)) / self.temperature
        logits -= logits.max(axis=1, keepdims=True)
        finbert = np.exp(logits)
        finbert /= finbert.sum(axis=1, keepdims=True)
        matrix = (1 - self.finbert_weight) * sparse + self.finbert_weight * finbert

        positive_index = self.classes.index("positive")
        output = []
        for row in matrix:
            winner = int(np.argmax(row))
            probabilities = {
                label: float(row[index]) for index, label in enumerate(self.classes)
            }
            output.append(Prediction(
                sentiment=self.classes[winner],
                confidence=float(row[winner]),
                is_positive=bool(row[positive_index] >= self.threshold),
                positive_threshold=self.threshold,
                probabilities=probabilities,
                model_version=self.version,
            ))
        return output
