from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class URLFinding:
    url: str
    final_url: str
    suspicious: bool
    reason: str = ""
    domain: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EmailMessage:
    message_id: str
    thread_id: str | None = None
    subject: str = ""
    body: str = ""
    sender: str = ""
    sender_domain: str = ""
    received_at: datetime = field(default_factory=utcnow)
    headers: dict[str, str] = field(default_factory=dict)
    urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScanResult:
    message_id: str
    received_at: datetime
    phishing_probability: float
    label: str
    risk_level: str
    reasons: list[str] = field(default_factory=list)
    urls: list[URLFinding] = field(default_factory=list)
    spf_status: str = "unknown"
    dkim_status: str = "unknown"
    scanned_at: datetime = field(default_factory=utcnow)

    @property
    def is_phishing(self) -> bool:
        return self.label.upper() == "PHISHING"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["urls"] = [item.to_dict() for item in self.urls]
        return payload

