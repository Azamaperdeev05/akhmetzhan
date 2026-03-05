from __future__ import annotations

import re
from email.utils import parseaddr

AUTH_TOKEN_RE = re.compile(r"(spf|dkim|dmarc)\s*=\s*([a-z]+)", re.IGNORECASE)


def _normalize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in (headers or {}).items()}


def _extract_auth_tokens(authentication_results: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for name, status in AUTH_TOKEN_RE.findall(authentication_results or ""):
        tokens[name.lower()] = status.lower()
    return tokens


def _domain_from_sender(sender: str) -> str:
    _, email_addr = parseaddr(sender or "")
    if "@" not in email_addr:
        return ""
    return email_addr.split("@", 1)[1].lower()


def analyze_headers(headers: dict[str, str], sender: str = "") -> dict[str, object]:
    normalized = _normalize_headers(headers)
    auth_result_header = normalized.get("authentication-results", "")
    received_spf = normalized.get("received-spf", "")
    return_path = normalized.get("return-path", "")

    reasons: list[str] = []
    auth_tokens = _extract_auth_tokens(auth_result_header)

    spf_status = auth_tokens.get("spf", "unknown")
    dkim_status = auth_tokens.get("dkim", "unknown")

    if spf_status == "unknown":
        lowered = received_spf.lower()
        if "pass" in lowered:
            spf_status = "pass"
        elif "fail" in lowered or "softfail" in lowered:
            spf_status = "fail"

    if spf_status in {"fail", "softfail"}:
        reasons.append("SPF validation failed")
    if dkim_status == "fail":
        reasons.append("DKIM validation failed")

    sender_domain = _domain_from_sender(sender)
    return_path_domain = _domain_from_sender(return_path)
    if sender_domain and return_path_domain and sender_domain != return_path_domain:
        reasons.append("Sender and Return-Path domains mismatch")

    return {
        "spf_status": spf_status,
        "dkim_status": dkim_status,
        "reasons": reasons,
    }

