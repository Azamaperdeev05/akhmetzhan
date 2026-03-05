from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PHISHING_KEYWORDS = {
    "verify",
    "password",
    "urgent",
    "account",
    "login",
    "suspended",
    "security alert",
    "bank",
    "confirm",
    "click here",
}


class PhishingPredictor:
    def __init__(
        self,
        model_dir: Path | str = Path("model/saved_model"),
        mode: str = "auto",
        threshold: float = 0.75,
        prefer_gpu: bool = True,
        max_length: int = 512,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.mode = mode
        self.threshold = threshold
        self.prefer_gpu = prefer_gpu
        self.max_length = max_length
        self.backend = "heuristic"
        self._baseline_model = None
        self._bert_tokenizer = None
        self._bert_model = None
        self._bert_device = None

        self._load_model()

    def _load_model(self) -> None:
        baseline_path = self.model_dir / "baseline.joblib"
        bert_path = self.model_dir / "bert_model"

        if self.mode in {"auto", "bert"} and bert_path.exists():
            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                self._bert_tokenizer = AutoTokenizer.from_pretrained(bert_path)
                self._bert_model = AutoModelForSequenceClassification.from_pretrained(bert_path)
                if self.prefer_gpu and torch.cuda.is_available():
                    self._bert_device = torch.device("cuda")
                else:
                    self._bert_device = torch.device("cpu")
                self._bert_model.to(self._bert_device)
                self._bert_model.eval()
                self.backend = "bert"
                return
            except Exception:
                if self.mode == "bert":
                    raise

        if self.mode in {"auto", "baseline"} and baseline_path.exists():
            self._baseline_model = joblib.load(baseline_path)
            self.backend = "baseline"
            return

        if self.mode not in {"auto", "heuristic"} and self.backend == "heuristic":
            raise FileNotFoundError(
                f"Requested mode '{self.mode}' could not be loaded from {self.model_dir}."
            )

    def predict_proba(self, text: str) -> float:
        if self.backend == "bert":
            return self._predict_with_bert(text)
        if self.backend == "baseline":
            probability = self._baseline_model.predict_proba([text])[0, 1]
            return float(probability)
        return self._predict_with_heuristic(text)

    def predict(self, text: str) -> tuple[str, float]:
        proba = self.predict_proba(text)
        label = "PHISHING" if proba > self.threshold else "LEGITIMATE"
        return label, proba

    def predict_many(self, texts: list[str]) -> list[tuple[str, float]]:
        return [self.predict(item) for item in texts]

    def _predict_with_bert(self, text: str) -> float:
        import torch

        encoded = self._bert_tokenizer(
            text or "",
            truncation=True,
            padding=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._bert_device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = self._bert_model(**encoded).logits
            probability = torch.softmax(logits, dim=1)[0, 1].item()
        return float(probability)

    def _predict_with_heuristic(self, text: str) -> float:
        lowered = (text or "").lower()
        if not lowered:
            return 0.01

        score = 0.0
        for keyword in PHISHING_KEYWORDS:
            if keyword in lowered:
                score += 1.0

        if "http://" in lowered:
            score += 0.5
        if "https://" in lowered:
            score += 0.25
        if any(token in lowered for token in ["!", "immediately", "urgent"]):
            score += 0.3

        return float(1 / (1 + math.exp(-score + 2.5)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phishing prediction for a single email text.")
    parser.add_argument("text", help="Email text to classify.")
    parser.add_argument("--model-dir", type=Path, default=Path("model/saved_model"))
    parser.add_argument("--mode", choices=("auto", "baseline", "bert", "heuristic"), default="auto")
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--no-gpu", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    predictor = PhishingPredictor(
        model_dir=args.model_dir,
        mode=args.mode,
        threshold=args.threshold,
        prefer_gpu=not args.no_gpu,
    )
    label, score = predictor.predict(args.text)
    print({"backend": predictor.backend, "label": label, "phishing_probability": score})


if __name__ == "__main__":
    main()
