from __future__ import annotations

from pathlib import Path

import pandas as pd

from data.preprocess import prepare_dataset
from model.evaluate import evaluate_baseline
from model.train import train_baseline


def _write_raw_dataset(tmp_path: Path) -> tuple[Path, Path]:
    phishing = pd.DataFrame(
        {
            "text": [
                "verify your account now",
                "urgent password reset",
                "click to confirm login",
                "security alert account blocked",
                "bank update required",
                "vpn expired login now",
                "verify payroll details",
                "authenticate immediately",
            ]
        }
    )
    legitimate = pd.DataFrame(
        {
            "text": [
                "team meeting starts at nine",
                "invoice paid successfully",
                "project roadmap update",
                "lunch menu for friday",
                "onboarding session details",
                "new sprint planning agenda",
                "engineering weekly update",
                "vacation request approved",
            ]
        }
    )
    phishing_path = tmp_path / "phishing.csv"
    legitimate_path = tmp_path / "legitimate.csv"
    phishing.to_csv(phishing_path, index=False)
    legitimate.to_csv(legitimate_path, index=False)
    return phishing_path, legitimate_path


def test_prepare_dataset_and_baseline_training(tmp_path: Path) -> None:
    phishing_path, legitimate_path = _write_raw_dataset(tmp_path)
    processed_dir = tmp_path / "processed"
    stats = prepare_dataset(
        phishing_path=phishing_path,
        legitimate_path=legitimate_path,
        output_dir=processed_dir,
        seed=42,
    )

    assert stats["total"] == 16
    assert (processed_dir / "train.csv").exists()
    assert (processed_dir / "val.csv").exists()
    assert (processed_dir / "test.csv").exists()

    train_df = pd.read_csv(processed_dir / "train.csv")
    val_df = pd.read_csv(processed_dir / "val.csv")
    test_df = pd.read_csv(processed_dir / "test.csv")

    output_dir = tmp_path / "saved_model"
    metrics = train_baseline(
        train_texts=train_df["text"].tolist(),
        train_labels=train_df["label"].tolist(),
        val_texts=val_df["text"].tolist(),
        val_labels=val_df["label"].tolist(),
        output_dir=output_dir,
        seed=42,
    )

    assert (output_dir / "baseline.joblib").exists()
    assert 0.0 <= metrics["f1"] <= 1.0

    eval_metrics = evaluate_baseline(
        model_path=output_dir / "baseline.joblib",
        test_texts=test_df["text"].tolist(),
        test_labels=test_df["label"].tolist(),
    )
    assert "latency_per_email_ms" in eval_metrics
    assert 0.0 <= eval_metrics["accuracy"] <= 1.0

