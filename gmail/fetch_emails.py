from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

from analyzer.preprocessor import html_to_text
from analyzer.url_checker import extract_urls
from utils.schemas import EmailMessage


def _decode_base64url(data: str) -> str:
    if not data:
        return ""
    pad = "=" * ((4 - len(data) % 4) % 4)
    decoded = base64.urlsafe_b64decode(data + pad)
    return decoded.decode("utf-8", errors="replace")


def _extract_body(payload: dict) -> str:
    if not payload:
        return ""

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")
    parts = payload.get("parts", [])

    if mime_type in {"text/plain", "text/html"} and body_data:
        text = _decode_base64url(body_data)
        return html_to_text(text) if mime_type == "text/html" else text

    plain_parts: list[str] = []
    html_parts: list[str] = []
    for part in parts:
        sub_body = _extract_body(part)
        if not sub_body:
            continue
        if part.get("mimeType", "").startswith("text/plain"):
            plain_parts.append(sub_body)
        else:
            html_parts.append(sub_body)

    if plain_parts:
        return "\n".join(plain_parts)
    if html_parts:
        return "\n".join(html_parts)
    return ""


def _headers_to_map(headers: list[dict[str, str]]) -> dict[str, str]:
    output: dict[str, str] = {}
    for item in headers or []:
        name = item.get("name")
        value = item.get("value", "")
        if name:
            output[name] = value
    return output


def _parse_received_at(message: dict, headers: dict[str, str]) -> datetime:
    internal_date = message.get("internalDate")
    if internal_date:
        try:
            millis = int(internal_date)
            return datetime.fromtimestamp(millis / 1000, tz=timezone.utc)
        except ValueError:
            pass

    date_header = headers.get("Date", "")
    if date_header:
        try:
            parsed = parsedate_to_datetime(date_header)
            return parsed.astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def parse_gmail_message(message: dict) -> EmailMessage:
    payload = message.get("payload", {})
    header_map = _headers_to_map(payload.get("headers", []))
    sender = header_map.get("From", "")
    _, sender_email = parseaddr(sender)
    sender_domain = sender_email.split("@", 1)[1].lower() if "@" in sender_email else ""
    body = _extract_body(payload)

    email_obj = EmailMessage(
        message_id=message.get("id", ""),
        thread_id=message.get("threadId"),
        subject=header_map.get("Subject", ""),
        body=body,
        sender=sender,
        sender_domain=sender_domain,
        received_at=_parse_received_at(message, header_map),
        headers=header_map,
        urls=extract_urls(body),
    )
    return email_obj


def fetch_recent_emails(
    service,
    query: str = "in:inbox",
    max_results: int = 20,
    seen_ids: set[str] | None = None,
) -> list[EmailMessage]:
    if seen_ids is None:
        seen_ids = set()
    if max_results <= 0:
        return []

    message_refs: list[dict] = []
    page_token: str | None = None
    while len(message_refs) < max_results:
        request = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=min(max_results, 100),
            pageToken=page_token,
        )
        response = request.execute()
        page_refs = response.get("messages", [])
        if page_refs:
            message_refs.extend(page_refs)

        page_token = response.get("nextPageToken")
        if not page_token or not page_refs:
            break

    unique_refs: list[dict] = []
    seen_in_batch: set[str] = set()
    for ref in message_refs:
        message_id = ref.get("id", "")
        if not message_id or message_id in seen_in_batch:
            continue
        seen_in_batch.add(message_id)
        unique_refs.append(ref)
        if len(unique_refs) >= max_results:
            break

    parsed: list[EmailMessage] = []
    for reference in unique_refs:
        message_id = reference.get("id", "")
        if not message_id or message_id in seen_ids:
            continue

        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        parsed_message = parse_gmail_message(message)
        parsed.append(parsed_message)
        seen_ids.add(message_id)
    return parsed


def load_sample_emails(path: Path) -> list[EmailMessage]:
    if not path.exists():
        return []
    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    emails: list[EmailMessage] = []
    for item in raw_payload:
        headers = item.get("headers", {})
        sender = item.get("sender", "")
        _, sender_email = parseaddr(sender)
        sender_domain = sender_email.split("@", 1)[1].lower() if "@" in sender_email else ""
        emails.append(
            EmailMessage(
                message_id=item.get("message_id", ""),
                thread_id=item.get("thread_id"),
                subject=item.get("subject", ""),
                body=item.get("body", ""),
                sender=sender,
                sender_domain=sender_domain,
                headers=headers,
                urls=extract_urls(item.get("body", "")),
            )
        )
    return emails
