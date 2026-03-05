from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzer.pipeline import PhishGuardPipeline
from gmail.auth import get_gmail_service
from main import scan_once
from model.predict import PhishingPredictor
from utils.config import get_settings
from utils.database import Database
from utils.logger import get_logger, setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 3 validator: process real Gmail inbox messages and summarize results."
    )
    parser.add_argument("--target-count", type=int, default=20, help="Minimum number of emails to process.")
    parser.add_argument("--max-cycles", type=int, default=10, help="Maximum scan cycles before stopping.")
    parser.add_argument("--max-results", type=int, default=20, help="Inbox fetch limit per cycle.")
    parser.add_argument("--sleep-seconds", type=int, default=30, help="Delay between cycles.")
    parser.add_argument(
        "--offline-samples",
        type=Path,
        default=Path("data/raw/sample_inbox.json"),
        help="Unused in normal path; required by scan_once signature.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger("phase3.validator")

    service = get_gmail_service(
        credentials_path=settings.gmail_credentials_path,
        token_path=settings.gmail_token_path,
    )
    db = Database(settings.database_url)
    predictor = PhishingPredictor(
        model_dir=settings.model_dir,
        mode="auto",
        threshold=settings.phishing_threshold,
        prefer_gpu=True,
    )
    pipeline = PhishGuardPipeline(
        predictor=predictor,
        threshold=settings.phishing_threshold,
        expand_short_urls=False,
    )

    seen_ids: set[str] = set()
    scanned_total = 0
    phishing_total = 0
    cycles_run = 0

    for cycle in range(1, args.max_cycles + 1):
        cycles_run = cycle
        scanned, phishing = scan_once(
            db=db,
            pipeline=pipeline,
            logger=logger,
            settings=settings,
            service=service,
            max_results=args.max_results,
            seen_ids=seen_ids,
            sample_path=args.offline_samples,
        )
        scanned_total += scanned
        phishing_total += phishing

        if scanned_total >= args.target_count:
            break
        if cycle < args.max_cycles:
            time.sleep(args.sleep_seconds)

    payload = {
        "target_count": args.target_count,
        "cycles_run": cycles_run,
        "scanned_total": scanned_total,
        "phishing_total": phishing_total,
        "target_reached": scanned_total >= args.target_count,
        "database_url": settings.database_url,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

