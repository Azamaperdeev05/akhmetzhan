from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzer.pipeline import PhishGuardPipeline
from dashboard.app import create_app
from gmail.fetch_emails import load_sample_emails
from model.predict import PhishingPredictor
from utils.config import reload_settings
from utils.database import Database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 4 E2E demo using sample inbox and dashboard routes.")
    parser.add_argument(
        "--db-url",
        default="sqlite:///phase4_demo.db",
        help="SQLite URL for this demo run.",
    )
    parser.add_argument(
        "--sample-path",
        type=Path,
        default=Path("data/raw/sample_inbox.json"),
        help="Sample inbox JSON path.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Threshold to classify phishing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["DATABASE_URL"] = args.db_url
    settings = reload_settings()

    db = Database(args.db_url)
    predictor = PhishingPredictor(mode="heuristic", threshold=args.threshold)
    pipeline = PhishGuardPipeline(
        predictor=predictor,
        threshold=args.threshold,
        expand_short_urls=False,
    )

    emails = load_sample_emails(args.sample_path)
    if not emails:
        raise FileNotFoundError(f"No sample emails found at {args.sample_path}")

    run_id = db.start_scan_run()
    phishing_count = 0
    for email in emails:
        result = pipeline.scan_email(email)
        db.save_scan_result(email, result, run_id=run_id)
        if result.label == "PHISHING":
            phishing_count += 1
    db.finish_scan_run(run_id, scanned_count=len(emails), phishing_count=phishing_count)

    app = create_app()
    client = app.test_client()
    login_response = client.post(
        "/login",
        data={
            "username": settings.dashboard_username,
            "password": settings.dashboard_password,
        },
        follow_redirects=False,
    )

    endpoints = ["/", "/emails", "/stats", "/api/stats", "/settings"]
    statuses = {endpoint: client.get(endpoint).status_code for endpoint in endpoints}

    payload = {
        "database_url": args.db_url,
        "emails_scanned": len(emails),
        "phishing_detected": phishing_count,
        "login_status": login_response.status_code,
        "dashboard_statuses": statuses,
        "all_dashboard_endpoints_ok": all(status == 200 for status in statuses.values())
        and login_response.status_code in {302, 303},
        "summary": db.get_summary(days=30),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
