from __future__ import annotations


def _get_label_map(service) -> dict[str, str]:
    response = service.users().labels().list(userId="me").execute()
    labels = response.get("labels", [])
    return {label["name"]: label["id"] for label in labels}


def ensure_label(service, label_name: str = "PHISHING") -> str:
    label_map = _get_label_map(service)
    if label_name in label_map:
        return label_map[label_name]

    payload = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    response = service.users().labels().create(userId="me", body=payload).execute()
    return response["id"]


def apply_label(service, message_id: str, label_id: str) -> None:
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id], "removeLabelIds": []},
    ).execute()


def mark_as_phishing(service, message_id: str, label_name: str = "PHISHING") -> str:
    label_id = ensure_label(service, label_name=label_name)
    apply_label(service, message_id, label_id)
    return label_id

