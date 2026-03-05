from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzer.preprocessor import normalize_text

TEXT_COLUMN_CANDIDATES = ("text", "email", "message", "body", "content")


def _resolve_text_column(df: pd.DataFrame) -> str:
    lowered = {column.lower(): column for column in df.columns}
    for candidate in TEXT_COLUMN_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    raise ValueError(f"Could not find text column in dataset. Available columns: {list(df.columns)}")


def _read_labeled_dataset(csv_path: Path, label: int) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    text_column = _resolve_text_column(frame)
    output = frame[[text_column]].copy()
    output.rename(columns={text_column: "text"}, inplace=True)
    output["text"] = output["text"].fillna("").astype(str).map(normalize_text)
    output["label"] = int(label)
    output = output[output["text"].str.len() > 0]
    return output


def build_demo_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    phishing_samples = [
        "Urgent: verify your payroll account now at http://bit.ly/verify-payroll",
        "Security alert! Your mailbox is blocked. Confirm password immediately.",
        "Final warning: account suspended unless you login at http://192.168.1.20/login",
        "Please update banking details to avoid service interruption.",
        "Action required: invoice attached. Confirm credentials to open.",
        "Dear customer, unusual sign-in detected. Click secure link to verify.",
        "Your VPN access expired. Re-enter your password to continue.",
        "Payment failure notice. Validate company card via the secure portal.",
        "Important: HR docs pending. Sign in to approve benefits update.",
        "Mailbox storage exceeded. Reauthenticate now to prevent deletion.",
        "Authentication expired. Verify your account within 24 hours.",
        "Critical notification: confirm login from unknown country.",
    ]
    legitimate_samples = [
        "Reminder: team stand-up starts at 09:30 in meeting room A.",
        "Quarterly report draft is ready for review in the shared folder.",
        "Please review the sprint backlog updates before tomorrow.",
        "Lunch menu for Friday is now available in the portal.",
        "Your leave request for next Monday has been approved.",
        "Weekly newsletter: engineering achievements and roadmap.",
        "Client meeting moved to Thursday 14:00 due to timezone conflict.",
        "Invoice #4431 has been paid successfully.",
        "Welcome aboard! Here is your onboarding schedule.",
        "Code freeze starts tonight at 20:00, deployment tomorrow morning.",
        "Security training session recording is now uploaded.",
        "Please submit your OKRs by end of day Friday.",
    ]

    phishing_df = pd.DataFrame({"text": phishing_samples, "label": 1})
    legitimate_df = pd.DataFrame({"text": legitimate_samples, "label": 0})
    return phishing_df, legitimate_df


def prepare_dataset(
    phishing_path: Path,
    legitimate_path: Path,
    output_dir: Path,
    seed: int = 42,
) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)

    if phishing_path.exists() and legitimate_path.exists():
        phishing_df = _read_labeled_dataset(phishing_path, label=1)
        legitimate_df = _read_labeled_dataset(legitimate_path, label=0)
    else:
        phishing_df, legitimate_df = build_demo_dataset()

    combined = pd.concat([phishing_df, legitimate_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["text"]).sample(frac=1.0, random_state=seed).reset_index(drop=True)

    train_frame, holdout = train_test_split(
        combined,
        test_size=0.2,
        random_state=seed,
        stratify=combined["label"],
    )
    val_frame, test_frame = train_test_split(
        holdout,
        test_size=0.5,
        random_state=seed,
        stratify=holdout["label"],
    )

    train_frame.to_csv(output_dir / "train.csv", index=False)
    val_frame.to_csv(output_dir / "val.csv", index=False)
    test_frame.to_csv(output_dir / "test.csv", index=False)

    return {
        "total": len(combined),
        "train": len(train_frame),
        "val": len(val_frame),
        "test": len(test_frame),
        "phishing": int(combined["label"].sum()),
        "legitimate": int((1 - combined["label"]).sum()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare phishing datasets for model training.")
    parser.add_argument(
        "--phishing-path",
        type=Path,
        default=Path("data/raw/phishing_emails.csv"),
        help="Path to phishing CSV dataset.",
    )
    parser.add_argument(
        "--legitimate-path",
        type=Path,
        default=Path("data/raw/legitimate_emails.csv"),
        help="Path to legitimate CSV dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory where train/val/test files will be written.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible split.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = prepare_dataset(
        phishing_path=args.phishing_path,
        legitimate_path=args.legitimate_path,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    print("Dataset prepared successfully.")
    print(stats)


if __name__ == "__main__":
    main()
