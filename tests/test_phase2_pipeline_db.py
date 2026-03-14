from __future__ import annotations

import sqlite3
from pathlib import Path

from analyzer.pipeline import PhishGuardPipeline
from gmail.fetch_emails import load_sample_emails
from scripts.db_upgrade import is_legacy_sqlite_database, migrate_legacy_sqlite_database
from utils.database import Database, should_auto_create_schema


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


def test_schema_auto_create_policy_matches_database_backend() -> None:
    assert should_auto_create_schema("sqlite:///phishguard.db") is True
    assert should_auto_create_schema("sqlite:///C:/tmp/phishguard.db") is True
    assert should_auto_create_schema("postgresql+psycopg://user:pass@localhost:5432/phishguard") is False


def test_save_scan_result_if_new_skips_duplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "phase2-dedupe.sqlite3"
    db = Database(f"sqlite:///{db_path}")
    predictor = RuleBasedPredictor()
    pipeline = PhishGuardPipeline(predictor=predictor, threshold=0.75, expand_short_urls=False)
    email = load_sample_emails(Path("data/raw/sample_inbox.json"))[0]
    result = pipeline.scan_email(email)

    first_id, first_created = db.save_scan_result_if_new(email, result)
    second_id, second_created = db.save_scan_result_if_new(email, result)

    assert first_created is True
    assert second_created is False
    assert first_id == second_id
    assert db.count_results() == 1


def test_legacy_sqlite_migration_deduplicates_scan_results(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(
            """
            CREATE TABLE emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id VARCHAR(255) NOT NULL UNIQUE,
                thread_id VARCHAR(255),
                subject TEXT NOT NULL DEFAULT '',
                body_preview TEXT NOT NULL DEFAULT '',
                sender VARCHAR(512) NOT NULL DEFAULT '',
                sender_domain VARCHAR(255) NOT NULL DEFAULT '',
                received_at TEXT NOT NULL,
                raw_headers TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                scanned_count INTEGER NOT NULL DEFAULT 0,
                phishing_count INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE scan_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER NOT NULL,
                scan_run_id INTEGER,
                phishing_probability FLOAT NOT NULL DEFAULT 0,
                label VARCHAR(50) NOT NULL DEFAULT 'LEGITIMATE',
                risk_level VARCHAR(20) NOT NULL DEFAULT 'LOW',
                reasons TEXT NOT NULL DEFAULT '[]',
                spf_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
                dkim_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
                scanned_at TEXT NOT NULL
            );
            CREATE TABLE url_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_result_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                final_url TEXT NOT NULL DEFAULT '',
                domain VARCHAR(255) NOT NULL DEFAULT '',
                suspicious BOOLEAN NOT NULL DEFAULT 0,
                reason TEXT NOT NULL DEFAULT ''
            );
            """
        )
        connection.execute(
            """
            INSERT INTO emails
            (id, message_id, thread_id, subject, body_preview, sender, sender_domain, received_at, raw_headers, created_at)
            VALUES
            (1, 'msg-legacy', 't1', 'Legacy subject', 'Legacy body', 'sender@example.com', 'example.com',
             '2026-03-14 10:00:00+00:00', '{}', '2026-03-14 10:00:00+00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO scan_runs (id, started_at, finished_at, scanned_count, phishing_count, notes)
            VALUES (1, '2026-03-14 10:00:00+00:00', '2026-03-14 10:01:00+00:00', 2, 1, 'legacy')
            """
        )
        connection.execute(
            """
            INSERT INTO scan_results
            (id, email_id, scan_run_id, phishing_probability, label, risk_level, reasons, spf_status, dkim_status, scanned_at)
            VALUES
            (1, 1, 1, 0.25, 'LEGITIMATE', 'LOW', '[]', 'pass', 'pass', '2026-03-14 10:00:01+00:00'),
            (2, 1, 1, 0.95, 'PHISHING', 'HIGH', '[]', 'fail', 'fail', '2026-03-14 10:00:02+00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO url_findings
            (id, scan_result_id, url, final_url, domain, suspicious, reason)
            VALUES
            (1, 1, 'http://example.com', 'http://example.com', 'example.com', 0, ''),
            (2, 2, 'http://bad.test', 'http://bad.test', 'bad.test', 1, 'legacy duplicate')
            """
        )
        connection.commit()
    finally:
        connection.close()

    assert is_legacy_sqlite_database(db_path) is True

    project_root = Path(__file__).resolve().parents[1]
    result = migrate_legacy_sqlite_database(project_root=project_root, db_path=db_path)

    assert result.backup_path.exists()
    assert result.kept_scan_results == 1
    assert result.dropped_scan_results == 1

    migrated = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in migrated.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        assert "alembic_version" in tables

        scan_count = migrated.execute("SELECT COUNT(*) FROM scan_results").fetchone()[0]
        url_count = migrated.execute("SELECT COUNT(*) FROM url_findings").fetchone()[0]
        assert scan_count == 1
        assert url_count == 1

        kept_label = migrated.execute("SELECT label FROM scan_results").fetchone()[0]
        assert kept_label == "PHISHING"

        with_duplicate = False
        try:
            migrated.execute(
                """
                INSERT INTO scan_results
                (email_id, scan_run_id, phishing_probability, label, risk_level, reasons, spf_status, dkim_status, scanned_at)
                VALUES (1, 1, 0.10, 'LEGITIMATE', 'LOW', '[]', 'pass', 'pass', '2026-03-14 10:00:03+00:00')
                """
            )
            migrated.commit()
        except sqlite3.IntegrityError:
            with_duplicate = True

        assert with_duplicate is True
    finally:
        migrated.close()
