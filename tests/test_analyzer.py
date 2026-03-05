from __future__ import annotations

from datetime import datetime, timezone

from analyzer.header_analyzer import analyze_headers
from analyzer.pipeline import PhishGuardPipeline
from analyzer.preprocessor import preprocess_email
from analyzer.url_checker import analyze_urls
from utils.schemas import EmailMessage


class DummyPredictor:
    def __init__(self, score: float) -> None:
        self.score = score

    def predict_proba(self, text: str) -> float:
        return self.score


def test_preprocess_email_removes_html() -> None:
    cleaned = preprocess_email("<b>Alert</b>", "<p>Hello <a href='x'>world</a></p>")
    assert "Alert" in cleaned
    assert "<b>" not in cleaned


def test_url_checker_detects_suspicious_url() -> None:
    text = "Click here: http://192.168.1.10/login to verify account."
    findings = analyze_urls(text, expand=False)
    assert len(findings) == 1
    assert findings[0].suspicious is True
    assert "Host uses raw IP address" in findings[0].reason


def test_header_analyzer_detects_spf_dkim_fail() -> None:
    headers = {
        "Authentication-Results": "mx.google.com; spf=fail smtp.mailfrom=x; dkim=fail",
        "Return-Path": "<spoof@evil.example>",
    }
    result = analyze_headers(headers, sender="Admin <admin@corp.example>")
    assert result["spf_status"] == "fail"
    assert result["dkim_status"] == "fail"
    assert result["reasons"]


def test_pipeline_scan_email_returns_scan_result() -> None:
    pipeline = PhishGuardPipeline(predictor=DummyPredictor(0.92), threshold=0.75, expand_short_urls=False)
    email = EmailMessage(
        message_id="m-1",
        subject="Security update required",
        body="Please verify now at http://bit.ly/update-account",
        sender="Security <security@example.com>",
        sender_domain="example.com",
        received_at=datetime.now(timezone.utc),
        headers={"Authentication-Results": "mx.google.com; spf=fail; dkim=pass"},
    )

    result = pipeline.scan_email(email)
    assert result.label == "PHISHING"
    assert result.risk_level in {"MEDIUM", "HIGH"}
    assert result.phishing_probability > 0.75
    assert result.urls

