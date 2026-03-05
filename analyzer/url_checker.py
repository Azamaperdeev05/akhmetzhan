from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import requests

from utils.schemas import URLFinding

URL_RE = re.compile(
    r"(?P<url>(?:https?://|www\.)[^\s<>\"]+)",
    re.IGNORECASE,
)

SUSPICIOUS_KEYWORDS = {
    "login",
    "verify",
    "account",
    "update",
    "password",
    "secure",
    "bank",
    "confirm",
    "urgent",
}

SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "cutt.ly",
}


def extract_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = [match.group("url").strip(".,)") for match in URL_RE.finditer(text)]
    normalized = []
    for item in urls:
        if item.lower().startswith("www."):
            normalized.append(f"http://{item}")
        else:
            normalized.append(item)
    return normalized


def _is_ip_host(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def expand_url(url: str, timeout_seconds: int = 4) -> str:
    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            allow_redirects=True,
            headers={"User-Agent": "PhishGuard/1.0"},
        )
        return response.url or url
    except Exception:
        return url


def analyze_url(url: str, expand: bool = True) -> URLFinding:
    final_url = expand_url(url) if expand else url
    parsed = urlparse(final_url)
    original = urlparse(url)
    host = (parsed.hostname or "").lower()
    original_host = (original.hostname or "").lower()
    path_blob = f"{parsed.path} {parsed.query}".lower()

    reasons: list[str] = []

    if parsed.scheme != "https":
        reasons.append("Non-HTTPS URL")

    if "@" in (parsed.netloc or ""):
        reasons.append("Contains @ in host")

    if host in SHORTENER_DOMAINS or original_host in SHORTENER_DOMAINS:
        reasons.append("URL shortener detected")

    if host and _is_ip_host(host):
        reasons.append("Host uses raw IP address")

    if "xn--" in host:
        reasons.append("Punycode domain detected")

    if any(keyword in path_blob for keyword in SUSPICIOUS_KEYWORDS):
        reasons.append("Suspicious keyword in URL path/query")

    if original_host and host and original_host != host:
        reasons.append("Redirected to different domain")

    reason = "; ".join(reasons)
    return URLFinding(
        url=url,
        final_url=final_url,
        suspicious=bool(reasons),
        reason=reason,
        domain=host or original_host,
    )


def analyze_urls(text: str, expand: bool = True) -> list[URLFinding]:
    urls = extract_urls(text)
    return [analyze_url(url, expand=expand) for url in urls]

