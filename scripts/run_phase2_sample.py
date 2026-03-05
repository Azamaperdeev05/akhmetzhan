from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzer.pipeline import PhishGuardPipeline
from gmail.fetch_emails import load_sample_emails
from model.predict import PhishingPredictor
from utils.database import Database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 2 smoke: scan sample inbox and persist results to SQLite."
    )
    parser.add_argument(
        "--sample-path",
        type=Path,
        default=Path("data/raw/sample_inbox.json"),
        help="Path to JSON file with sample emails.",
    )
    parser.add_argument(
        "--db-url",
        default="sqlite:///phase2_demo.db",
        help="Database URL for saving scan results.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Phishing decision threshold.",
    )
    parser.add_argument(
        "--predictor-mode",
        choices=("auto", "baseline", "bert", "heuristic"),
        default="heuristic",
        help="Predictor backend used for the smoke run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    emails = load_sample_emails(args.sample_path)
    if not emails:
        raise FileNotFoundError(f"Sample inbox is empty or missing: {args.sample_path}")

    db = Database(args.db_url)
    predictor = PhishingPredictor(mode=args.predictor_mode, threshold=args.threshold)
    pipeline = PhishGuardPipeline(
        predictor=predictor,
        threshold=args.threshold,
        expand_short_urls=False,
    )

    run_id = db.start_scan_run()
    phishing_count = 0
    for email in emails:
        result = pipeline.scan_email(email)
        db.save_scan_result(email, result, run_id=run_id)
        if result.label == "PHISHING":
            phishing_count += 1

    db.finish_scan_run(run_id, scanned_count=len(emails), phishing_count=phishing_count)
    summary = db.get_summary(days=30)

    payload = {
        "database_url": args.db_url,
        "predictor_backend": predictor.backend,
        "processed_emails": len(emails),
        "phishing_detected": phishing_count,
        "summary": summary,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

