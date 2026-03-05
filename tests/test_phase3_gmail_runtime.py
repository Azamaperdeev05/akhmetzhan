from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import main as main_module
from analyzer.pipeline import PhishGuardPipeline
from gmail.fetch_emails import fetch_recent_emails
from utils.database import Database, ScanRunRecord
from utils.schemas import EmailMessage


class DummySettings:
    phishing_threshold = 0.75
    gmail_query = "in:inbox"
    gmail_label_name = "PHISHING"


class FixedPredictor:
    def __init__(self, score: float) -> None:
        self.score = score

    def predict_proba(self, text: str) -> float:
        return self.score


def _mock_message(mid: str) -> dict:
    return {
        "id": mid,
        "threadId": f"t-{mid}",
        "payload": {
            "headers": [
                {"name": "Subject", "value": f"subject-{mid}"},
                {"name": "From", "value": "Tester <test@example.com>"},
            ],
            "body": {},
        },
    }


def test_fetch_recent_emails_pagination_and_dedup() -> None:
    service = MagicMock()
    messages_api = service.users.return_value.messages.return_value
    messages_api.list.return_value.execute.side_effect = [
        {"messages": [{"id": "m1"}, {"id": "m2"}], "nextPageToken": "p2"},
        {"messages": [{"id": "m2"}, {"id": "m3"}]},
    ]

    def get_side_effect(userId: str, id: str, format: str):
        request = MagicMock()
        request.execute.return_value = _mock_message(id)
        return request

    messages_api.get.side_effect = get_side_effect
    seen_ids = {"m1"}
    output = fetch_recent_emails(service, seen_ids=seen_ids, max_results=3)
    ids = [item.message_id for item in output]

    assert ids == ["m2", "m3"]
    assert messages_api.list.call_count == 2


def test_run_with_retry_non_retryable_stops_immediately() -> None:
    logger = logging.getLogger("phase3.retry.nonretry")
    attempts = {"n": 0}

    def fail_once():
        attempts["n"] += 1
        raise ValueError("validation failed")

    with pytest.raises(ValueError):
        main_module.run_with_retry(logger, fail_once, retries=3, base_delay=0.0)
    assert attempts["n"] == 1


def test_run_with_retry_retries_transient_errors(monkeypatch) -> None:
    logger = logging.getLogger("phase3.retry.retryable")
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("503 service unavailable")
        return "ok"

    monkeypatch.setattr(main_module.time, "sleep", lambda _: None)
    result = main_module.run_with_retry(logger, flaky, retries=4, base_delay=0.0)
    assert result == "ok"
    assert attempts["n"] == 3


def test_scan_once_continues_when_label_apply_fails(monkeypatch, tmp_path: Path) -> None:
    db = Database(f"sqlite:///{tmp_path / 'phase3.sqlite3'}")
    predictor = FixedPredictor(0.95)
    pipeline = PhishGuardPipeline(predictor=predictor, threshold=0.75, expand_short_urls=False)
    logger = logging.getLogger("phase3.scan")

    email = EmailMessage(
        message_id="msg-1",
        subject="Verify account",
        body="urgent verify password now",
        sender="SOC <soc@example.com>",
        sender_domain="example.com",
        received_at=datetime.now(timezone.utc),
        headers={"Authentication-Results": "mx.google.com; spf=pass; dkim=pass"},
    )

    monkeypatch.setattr(main_module, "fetch_recent_emails", lambda **kwargs: [email])
    monkeypatch.setattr(
        main_module,
        "mark_as_phishing",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("503 service unavailable")),
    )
    monkeypatch.setattr(main_module.time, "sleep", lambda _: None)

    scanned, phishing = main_module.scan_once(
        db=db,
        pipeline=pipeline,
        logger=logger,
        settings=DummySettings(),
        service=object(),
        max_results=20,
        seen_ids=set(),
        sample_path=Path("data/raw/sample_inbox.json"),
    )

    assert scanned == 1
    assert phishing == 1
    assert db.count_results() == 1

    with db.session_scope() as session:
        run = session.query(ScanRunRecord).order_by(ScanRunRecord.id.desc()).first()
        assert run is not None
        assert "label_failures=1" in (run.notes or "")

