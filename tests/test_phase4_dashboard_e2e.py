from __future__ import annotations

from pathlib import Path

from analyzer.pipeline import PhishGuardPipeline
import dashboard.app as dashboard_app_module
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
    settings = reload_settings()

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
    # Protected routes must redirect to login before auth.
    assert client.get("/").status_code in {302, 303}

    login_response = client.post(
        "/login",
        data={
            "username": settings.dashboard_username,
            "password": settings.dashboard_password,
        },
        follow_redirects=False,
    )
    assert login_response.status_code in {302, 303}

    assert client.get("/").status_code == 200
    assert client.get("/emails").status_code == 200
    assert client.get("/stats").status_code == 200
    assert client.get("/api/stats").status_code == 200
    assert client.get("/settings").status_code == 200


def test_settings_update_changes_env_file(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / "phase4.env"
    env_path.write_text(
        "PHISHING_THRESHOLD=0.75\nSCAN_INTERVAL_MINUTES=5\nDASHBOARD_USERNAME=admin\nDASHBOARD_PASSWORD=admin12345\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PHISHGUARD_ENV_PATH", str(env_path))

    update_env_values({"PHISHING_THRESHOLD": "0.66", "SCAN_INTERVAL_MINUTES": "9"})
    content = env_path.read_text(encoding="utf-8")
    assert "PHISHING_THRESHOLD=0.66" in content
    assert "SCAN_INTERVAL_MINUTES=9" in content


def test_login_failure_returns_200_with_error(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "phase4-auth.sqlite3"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("DASHBOARD_USERNAME", "guard")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret123")
    reload_settings()

    app = create_app()
    client = app.test_client()
    response = client.post(
        "/login",
        data={"username": "guard", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Логин немесе құпиясөз қате.".encode("utf-8") in response.data


def test_scan_routes_work_with_authenticated_user(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / "phase4-scan.env"
    env_path.write_text(
        (
            "DATABASE_URL=sqlite:///phase4-scan.sqlite3\n"
            "PHISHING_THRESHOLD=0.75\n"
            "SCAN_INTERVAL_MINUTES=5\n"
            "DASHBOARD_USERNAME=admin\n"
            "DASHBOARD_PASSWORD=admin12345\n"
            "AUTO_SCAN_ENABLED=0\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHISHGUARD_ENV_PATH", str(env_path))

    db_path = tmp_path / "phase4-scan.sqlite3"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    settings = reload_settings()

    class DummyScanner:
        def __init__(self) -> None:
            self._auto = False

        def is_auto_enabled(self) -> bool:
            return self._auto

        def get_last_status(self) -> dict[str, object]:
            return {"timestamp": "", "scanned": 0, "phishing": 0, "source": "n/a", "trigger": "none", "error": ""}

        def run_scan_cycle(self, trigger: str = "manual") -> dict[str, object]:
            return {"scanned": 3, "phishing": 1, "source": "sample"}

        def set_auto_enabled(self, enabled: bool) -> None:
            self._auto = enabled

    monkeypatch.setattr(dashboard_app_module, "DashboardScannerService", DummyScanner)
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
    assert login_response.status_code in {302, 303}

    run_response = client.post("/scan/run", follow_redirects=False)
    assert run_response.status_code in {302, 303}

    auto_response = client.post("/scan/auto", data={"enabled": "1"}, follow_redirects=False)
    assert auto_response.status_code in {302, 303}
