from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass


def read_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Split file not found: {path}")
    frame = pd.read_csv(path)
    if "text" not in frame.columns or "label" not in frame.columns:
        raise ValueError(f"Split file must contain 'text' and 'label' columns: {path}")
    frame["text"] = frame["text"].fillna("").astype(str)
    frame["label"] = frame["label"].astype(int)
    return frame


def read_processed_splits(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_df = read_split(processed_dir / "train.csv")
    val_df = read_split(processed_dir / "val.csv")
    test_df = read_split(processed_dir / "test.csv")
    return train_df, val_df, test_df


def compute_binary_metrics(y_true: Iterable[int], y_pred: Iterable[int], y_proba: Iterable[float]) -> dict[str, float]:
    y_true_arr = np.asarray(list(y_true), dtype=int)
    y_pred_arr = np.asarray(list(y_pred), dtype=int)
    y_proba_arr = np.asarray(list(y_proba), dtype=float)

    metrics: dict[str, float] = {
        "accuracy": float(accuracy_score(y_true_arr, y_pred_arr)),
        "precision": float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
    }

    try:
        metrics["auc_roc"] = float(roc_auc_score(y_true_arr, y_proba_arr))
    except ValueError:
        metrics["auc_roc"] = 0.0

    tn, fp, fn, tp = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1]).ravel()
    metrics.update({"tn": float(tn), "fp": float(fp), "fn": float(fn), "tp": float(tp)})
    return metrics


def threshold_sweep(y_true: Iterable[int], y_proba: Iterable[float]) -> list[dict[str, float]]:
    y_true_arr = np.asarray(list(y_true), dtype=int)
    y_proba_arr = np.asarray(list(y_proba), dtype=float)
    thresholds = np.linspace(0.1, 0.9, 9)

    output: list[dict[str, float]] = []
    for threshold in thresholds:
        y_pred = (y_proba_arr >= threshold).astype(int)
        metrics = compute_binary_metrics(y_true_arr, y_pred, y_proba_arr)
        output.append(
            {
                "threshold": float(threshold),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
            }
        )
    return output


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

