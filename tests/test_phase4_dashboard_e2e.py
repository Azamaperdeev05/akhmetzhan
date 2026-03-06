from __future__ import annotations

from pathlib import Path

from analyzer.pipeline import PhishGuardPipeline
from dashboard.app import create_app
from gmail.fetch_emails import load_sample_emails
from utils.config import reload_settings, update_env_values
from utils.database import Database


class FixedPredictor:
    def __init__(self, score: float) -> None:
        self.score = score

    def predict_proba(self, text: str) -> float:
        return self.score


def test_phase4_e2e_scan_to_dashboard(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "phase4.sqlite3"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    reload_settings()

    db = Database(db_url)
    pipeline = PhishGuardPipeline(
        predictor=FixedPredictor(0.9),
        threshold=0.75,
        expand_short_urls=False,
    )
    emails = load_sample_emails(Path("data/raw/sample_inbox.json"))
    assert emails

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

    assert client.get("/").status_code == 200
    assert client.get("/emails").status_code == 200
    assert client.get("/stats").status_code == 200
    assert client.get("/api/stats").status_code == 200
    assert client.get("/settings").status_code == 200


def test_settings_update_changes_env_file(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / "phase4.env"
    env_path.write_text("PHISHING_THRESHOLD=0.75\nSCAN_INTERVAL_MINUTES=5\n", encoding="utf-8")
    monkeypatch.setenv("PHISHGUARD_ENV_PATH", str(env_path))

    update_env_values({"PHISHING_THRESHOLD": "0.66", "SCAN_INTERVAL_MINUTES": "9"})
    content = env_path.read_text(encoding="utf-8")
    assert "PHISHING_THRESHOLD=0.66" in content
    assert "SCAN_INTERVAL_MINUTES=9" in content

