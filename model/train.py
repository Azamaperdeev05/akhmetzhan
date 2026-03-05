from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model.training_utils import compute_binary_metrics, read_processed_splits, set_seed, write_json


def train_baseline(
    train_texts: list[str],
    train_labels: list[int],
    val_texts: list[str],
    val_labels: list[int],
    output_dir: Path,
    seed: int = 42,
) -> dict[str, float]:
    set_seed(seed)

    model = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    max_features=50_000,
                    min_df=1,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2_000,
                    class_weight="balanced",
                    random_state=seed,
                ),
            ),
        ]
    )

    model.fit(train_texts, train_labels)
    probabilities = model.predict_proba(val_texts)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics = compute_binary_metrics(val_labels, predictions, probabilities)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "baseline.joblib")
    write_json(output_dir / "baseline_val_metrics.json", metrics)
    return metrics


def train_bert(
    train_texts: list[str],
    train_labels: list[int],
    val_texts: list[str],
    val_labels: list[int],
    output_dir: Path,
    model_name: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    max_length: int,
    seed: int,
    use_gpu: bool,
) -> dict[str, float]:
    try:
        import torch
        from datasets import Dataset
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:  # pragma: no cover - depends on optional heavyweight deps
        raise RuntimeError(
            "BERT training dependencies are missing. Install transformers, datasets, and torch."
        ) from exc

    set_seed(seed)
    train_dataset = Dataset.from_dict({"text": train_texts, "label": train_labels})
    val_dataset = Dataset.from_dict({"text": val_texts, "label": val_labels})

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize(batch: dict[str, list[str]]) -> dict[str, list[int]]:
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_length,
        )

    train_tokenized = train_dataset.map(tokenize, batched=True)
    val_tokenized = val_dataset.map(tokenize, batched=True)
    train_tokenized = train_tokenized.remove_columns(["text"])
    val_tokenized = val_tokenized.remove_columns(["text"])

    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    def compute_metrics(eval_pred) -> dict[str, float]:
        logits, labels = eval_pred
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exp_scores = np.exp(shifted)
        probs = exp_scores / exp_scores.sum(axis=1, keepdims=True)
        y_pred = np.argmax(logits, axis=1)
        metrics = compute_binary_metrics(labels, y_pred, probs[:, 1])
        return {
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "auc_roc": metrics["auc_roc"],
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    training_kwargs = {
        "output_dir": str(output_dir / "bert_checkpoints"),
        "save_strategy": "epoch",
        "learning_rate": learning_rate,
        "per_device_train_batch_size": batch_size,
        "per_device_eval_batch_size": batch_size,
        "num_train_epochs": epochs,
        "weight_decay": 0.01,
        "warmup_steps": 500,
        "logging_steps": 25,
        "load_best_model_at_end": True,
        "metric_for_best_model": "f1",
        "greater_is_better": True,
        "seed": seed,
        "report_to": [],
    }

    signatures = inspect.signature(TrainingArguments.__init__).parameters
    if "evaluation_strategy" in signatures:
        training_kwargs["evaluation_strategy"] = "epoch"
    else:
        training_kwargs["eval_strategy"] = "epoch"

    use_cpu = not (use_gpu and torch.cuda.is_available())
    if "use_cpu" in signatures:
        training_kwargs["use_cpu"] = use_cpu
    elif "no_cuda" in signatures:
        training_kwargs["no_cuda"] = use_cpu

    training_args = TrainingArguments(**training_kwargs)

    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": train_tokenized,
        "eval_dataset": val_tokenized,
        "data_collator": data_collator,
        "compute_metrics": compute_metrics,
    }
    trainer_signature = inspect.signature(Trainer.__init__).parameters
    if "tokenizer" in trainer_signature:
        trainer_kwargs["tokenizer"] = tokenizer
    else:
        trainer_kwargs["processing_class"] = tokenizer

    trainer = Trainer(**trainer_kwargs)

    trainer.train()
    metrics = trainer.evaluate()

    bert_dir = output_dir / "bert_model"
    trainer.save_model(str(bert_dir))
    tokenizer.save_pretrained(str(bert_dir))
    normalized_metrics = {
        "accuracy": float(metrics.get("eval_accuracy", 0.0)),
        "precision": float(metrics.get("eval_precision", 0.0)),
        "recall": float(metrics.get("eval_recall", 0.0)),
        "f1": float(metrics.get("eval_f1", 0.0)),
        "auc_roc": float(metrics.get("eval_auc_roc", 0.0)),
    }
    write_json(output_dir / "bert_val_metrics.json", normalized_metrics)
    return normalized_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train phishing detection model.")
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory with train.csv, val.csv, test.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("model/saved_model"),
        help="Directory where trained model artifacts are saved.",
    )
    parser.add_argument(
        "--mode",
        choices=("baseline", "bert", "both"),
        default="baseline",
        help="Training mode.",
    )
    parser.add_argument("--model-name", default="bert-base-uncased", help="HuggingFace model name for BERT mode.")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--use-gpu", action="store_true", help="Use GPU for BERT training if available.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_df, val_df, _ = read_processed_splits(args.processed_dir)

    results: dict[str, dict[str, float]] = {}
    if args.mode in {"baseline", "both"}:
        baseline_metrics = train_baseline(
            train_texts=train_df["text"].tolist(),
            train_labels=train_df["label"].tolist(),
            val_texts=val_df["text"].tolist(),
            val_labels=val_df["label"].tolist(),
            output_dir=args.output_dir,
            seed=args.seed,
        )
        results["baseline"] = baseline_metrics
        print("Baseline metrics:", baseline_metrics)

    if args.mode in {"bert", "both"}:
        bert_metrics = train_bert(
            train_texts=train_df["text"].tolist(),
            train_labels=train_df["label"].tolist(),
            val_texts=val_df["text"].tolist(),
            val_labels=val_df["label"].tolist(),
            output_dir=args.output_dir,
            model_name=args.model_name,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            max_length=args.max_length,
            seed=args.seed,
            use_gpu=args.use_gpu,
        )
        results["bert"] = bert_metrics
        print("BERT metrics:", bert_metrics)

    write_json(args.output_dir / "train_summary.json", results)


if __name__ == "__main__":
    main()
