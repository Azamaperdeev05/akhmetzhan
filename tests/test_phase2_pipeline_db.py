from __future__ import annotations

from pathlib import Path

from analyzer.pipeline import PhishGuardPipeline
from gmail.fetch_emails import load_sample_emails
from utils.database import Database


class RuleBasedPredictor:
    def predict_proba(self, text: str) -> float:
        lowered = (text or "").lower()
        risky_tokens = ("verify", "password", "login", "urgent", "security")
        score = 0.15
        if any(token in lowered for token in risky_tokens):
            score = 0.91
        return score


def test_phase2_pipeline_writes_sample_emails_to_database(tmp_path: Path) -> None:
    db_path = tmp_path / "phase2.sqlite3"
    db = Database(f"sqlite:///{db_path}")
    predictor = RuleBasedPredictor()
    pipeline = PhishGuardPipeline(predictor=predictor, threshold=0.75, expand_short_urls=False)

    sample_path = Path("data/raw/sample_inbox.json")
    emails = load_sample_emails(sample_path)
    assert emails, "Sample inbox must contain at least one email for integration test."

    run_id = db.start_scan_run()
    phishing_count = 0
    for email in emails:
        result = pipeline.scan_email(email)
        db.save_scan_result(email, result, run_id=run_id)
        if result.label == "PHISHING":
            phishing_count += 1

    db.finish_scan_run(run_id=run_id, scanned_count=len(emails), phishing_count=phishing_count)

    assert db.count_results() == len(emails)

    summary = db.get_summary(days=30)
    assert summary["total_scans"] == len(emails)
    assert summary["phishing_count"] == phishing_count

    rows = db.list_recent_results(limit=10)
    assert len(rows) == len(emails)
    assert all("message_id" in row for row in rows)
    assert any(row["label"] == "PHISHING" for row in rows)

