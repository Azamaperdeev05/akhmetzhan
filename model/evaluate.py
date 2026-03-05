from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model.training_utils import (
    compute_binary_metrics,
    read_processed_splits,
    threshold_sweep,
    write_json,
)


def evaluate_baseline(
    model_path: Path,
    test_texts: list[str],
    test_labels: list[int],
) -> dict[str, float]:
    model = joblib.load(model_path)
    started = time.perf_counter()
    probabilities = model.predict_proba(test_texts)[:, 1]
    elapsed = time.perf_counter() - started

    predictions = (probabilities >= 0.5).astype(int)
    metrics = compute_binary_metrics(test_labels, predictions, probabilities)
    metrics["latency_per_email_ms"] = (elapsed / max(len(test_texts), 1)) * 1000.0
    return metrics


def evaluate_bert(
    model_dir: Path,
    test_texts: list[str],
    test_labels: list[int],
    batch_size: int = 16,
    max_length: int = 512,
    use_gpu: bool = True,
) -> dict[str, float]:
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - optional heavy deps
        raise RuntimeError(
            "BERT evaluation dependencies are missing. Install transformers and torch."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)

    if use_gpu and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    model.to(device)
    model.eval()

    probabilities: list[float] = []
    started = time.perf_counter()
    with torch.no_grad():
        for idx in range(0, len(test_texts), batch_size):
            batch = test_texts[idx : idx + batch_size]
            inputs = tokenizer(
                batch,
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt",
            )
            inputs = {key: value.to(device) for key, value in inputs.items()}
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=1)[:, 1].detach().cpu().numpy().tolist()
            probabilities.extend(probs)
    elapsed = time.perf_counter() - started

    probs_np = np.asarray(probabilities, dtype=float)
    predictions = (probs_np >= 0.5).astype(int)
    metrics = compute_binary_metrics(test_labels, predictions, probs_np)
    metrics["latency_per_email_ms"] = (elapsed / max(len(test_texts), 1)) * 1000.0
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate trained phishing detection model.")
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory with train/val/test splits.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("model/saved_model"),
        help="Directory containing trained model artifacts.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "baseline", "bert"),
        default="auto",
        help="Choose model backend for evaluation.",
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--use-gpu", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _, _, test_df = read_processed_splits(args.processed_dir)
    test_texts = test_df["text"].tolist()
    test_labels = test_df["label"].tolist()

    baseline_path = args.model_dir / "baseline.joblib"
    bert_path = args.model_dir / "bert_model"

    mode = args.mode
    if mode == "auto":
        mode = "bert" if bert_path.exists() else "baseline"

    if mode == "baseline":
        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline model not found: {baseline_path}")
        metrics = evaluate_baseline(baseline_path, test_texts, test_labels)
        probabilities = joblib.load(baseline_path).predict_proba(test_texts)[:, 1]
    else:
        if not bert_path.exists():
            raise FileNotFoundError(f"BERT model directory not found: {bert_path}")
        metrics = evaluate_bert(
            bert_path,
            test_texts,
            test_labels,
            batch_size=args.batch_size,
            max_length=args.max_length,
            use_gpu=args.use_gpu,
        )
        # For threshold sweep, recompute once using prediction helper.
        from model.predict import PhishingPredictor

        predictor = PhishingPredictor(model_dir=args.model_dir, mode="bert", threshold=0.5, prefer_gpu=args.use_gpu)
        probabilities = np.asarray([predictor.predict_proba(text) for text in test_texts], dtype=float)

    sweep = threshold_sweep(test_labels, probabilities.tolist())
    report = {"mode": mode, "metrics": metrics, "threshold_sweep": sweep}
    write_json(args.model_dir / "evaluation_report.json", report)

    print(f"Evaluation mode: {mode}")
    print(metrics)


if __name__ == "__main__":
    main()
