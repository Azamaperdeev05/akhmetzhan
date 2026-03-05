from __future__ import annotations

import base64
from unittest.mock import MagicMock

from gmail.fetch_emails import fetch_recent_emails, parse_gmail_message
from gmail.label_manager import apply_label, ensure_label


def _encode_body(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8").rstrip("=")


def test_parse_gmail_message() -> None:
    message = {
        "id": "abc123",
        "threadId": "t1",
        "internalDate": "1700000000000",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "Subject", "value": "Hello"},
                {"name": "From", "value": "Team <team@example.com>"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _encode_body("Body text")}},
            ],
        },
    }

    parsed = parse_gmail_message(message)
    assert parsed.message_id == "abc123"
    assert parsed.subject == "Hello"
    assert parsed.sender_domain == "example.com"
    assert "Body text" in parsed.body


def test_fetch_recent_emails_deduplicates_seen_ids() -> None:
    service = MagicMock()
    messages_api = service.users.return_value.messages.return_value
    messages_api.list.return_value.execute.return_value = {"messages": [{"id": "m1"}, {"id": "m2"}]}
    messages_api.get.return_value.execute.return_value = {
        "id": "m2",
        "payload": {"headers": [], "body": {}},
    }

    seen_ids = {"m1"}
    output = fetch_recent_emails(service, seen_ids=seen_ids, max_results=10)
    assert len(output) == 1
    assert output[0].message_id == "m2"


def test_ensure_label_and_apply_label() -> None:
    service = MagicMock()
    labels_api = service.users.return_value.labels.return_value
    labels_api.list.return_value.execute.return_value = {"labels": [{"id": "L1", "name": "PHISHING"}]}
    label_id = ensure_label(service, "PHISHING")
    assert label_id == "L1"

    apply_label(service, "mid-1", label_id)
    service.users.return_value.messages.return_value.modify.assert_called_once()
