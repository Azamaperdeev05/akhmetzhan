from __future__ import annotations

import html
import re

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency fallback
    BeautifulSoup = None


WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    if "<" not in raw_text and ">" not in raw_text:
        return raw_text

    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw_text, "html.parser")
        return soup.get_text(separator=" ")

    return TAG_RE.sub(" ", raw_text)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = html.unescape(text)
    normalized = normalized.replace("\x00", " ")
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def preprocess_email(subject: str, body: str) -> str:
    subject_clean = normalize_text(html_to_text(subject))
    body_clean = normalize_text(html_to_text(body))
    if subject_clean and body_clean:
        return f"{subject_clean}\n\n{body_clean}"
    return subject_clean or body_clean
