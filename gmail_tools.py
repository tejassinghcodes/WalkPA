"""
Gmail tool layer for WalkPA final.

Visible, verifiable Gmail actions:
- recent inbox reads
- sent email samples for existing style_memory compatibility
- visible WalkPA drafts
- visible approved sent replies
- labels
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Any

from google_auth import gmail_service


WALKPA_DRAFT_MARKER = "WALKPA_CREATED_DRAFT"
WALKPA_SENT_MARKER = "WALKPA_SENT_APPROVED_REPLY"


@dataclass
class EmailMessage:
    id: str
    thread_id: str
    sender: str
    sender_email: str
    subject: str
    snippet: str
    body: str

    def compact(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "from": self.sender,
            "sender_email": self.sender_email,
            "subject": self.subject,
            "snippet": self.snippet,
            "body_preview": self.body[:1200],
        }


def _header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body(data: str | None) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_text(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if body_data and mime_type in {"text/plain", "text/html"}:
        text = _decode_body(body_data)
        if mime_type == "text/html":
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
        return text.strip()

    parts = payload.get("parts", []) or []
    out = []
    for part in parts:
        text = _extract_text(part)
        if text:
            out.append(text)
    return "\n".join(out).strip()


def get_recent_emails(max_results: int = 15) -> list[EmailMessage]:
    svc = gmail_service()
    response = svc.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=max_results,
        q="-in:drafts -from:me",
    ).execute()

    emails = []
    for item in response.get("messages", []) or []:
        msg = svc.users().messages().get(userId="me", id=item["id"], format="full").execute()
        payload = msg.get("payload", {})
        headers = payload.get("headers", []) or []

        from_header = _header(headers, "From")
        subject = _header(headers, "Subject") or "(no subject)"
        _, sender_email = parseaddr(from_header)

        emails.append(
            EmailMessage(
                id=msg["id"],
                thread_id=msg.get("threadId", ""),
                sender=from_header or sender_email or "(unknown)",
                sender_email=sender_email or from_header,
                subject=subject,
                snippet=msg.get("snippet", ""),
                body=_extract_text(payload),
            )
        )

    return emails


def get_sent_email_samples(max_results: int = 8) -> list[dict[str, str]]:
    svc = gmail_service()
    response = svc.users().messages().list(
        userId="me",
        labelIds=["SENT"],
        maxResults=max_results,
        q=f'-"{WALKPA_SENT_MARKER}" -"{WALKPA_DRAFT_MARKER}"',
    ).execute()

    samples = []
    for item in response.get("messages", []) or []:
        msg = svc.users().messages().get(userId="me", id=item["id"], format="full").execute()
        payload = msg.get("payload", {})
        headers = payload.get("headers", []) or []
        samples.append({
            "id": msg.get("id", ""),
            "to": _header(headers, "To"),
            "subject": _header(headers, "Subject") or "(no subject)",
            "body": _extract_text(payload)[:1500],
        })
    return samples


def _mime_message(to: str, subject: str, body: str) -> dict[str, str]:
    message = MIMEText(body, "plain", "utf-8")
    message["To"] = to
    message["Subject"] = subject
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")}


def create_draft(to: str, subject: str, body: str, thread_id: str | None = None) -> dict[str, Any]:
    svc = gmail_service()

    visible_subject = subject if subject.lower().startswith("[walkpa draft]") else f"[WalkPA Draft] {subject}"
    visible_body = (
        f"{body.strip()}\n\n"
        "---\n"
        f"{WALKPA_DRAFT_MARKER}\n"
        "Created by WalkPA. This is a draft only. It was not sent automatically.\n"
    )

    created = svc.users().drafts().create(
        userId="me",
        body={"message": _mime_message(to, visible_subject, visible_body)},
    ).execute()

    return {
        "created": True,
        "draft_id": created.get("id"),
        "message_id": created.get("message", {}).get("id"),
        "to": to,
        "subject": visible_subject,
        "marker": WALKPA_DRAFT_MARKER,
        "gmail_search": f'in:drafts "{WALKPA_DRAFT_MARKER}"',
    }


def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    svc = gmail_service()

    visible_subject = subject if subject.lower().startswith("[walkpa sent]") else f"[WalkPA Sent] {subject}"
    visible_body = (
        f"{body.strip()}\n\n"
        "---\n"
        f"{WALKPA_SENT_MARKER}\n"
        "Sent by WalkPA after explicit user follow-up approval.\n"
    )

    sent = svc.users().messages().send(
        userId="me",
        body=_mime_message(to, visible_subject, visible_body),
    ).execute()

    return {
        "sent": True,
        "message_id": sent.get("id"),
        "thread_id": sent.get("threadId"),
        "to": to,
        "subject": visible_subject,
        "marker": WALKPA_SENT_MARKER,
        "gmail_search": f'in:sent "{WALKPA_SENT_MARKER}"',
    }


def _list_labels() -> list[dict[str, Any]]:
    return gmail_service().users().labels().list(userId="me").execute().get("labels", []) or []


def ensure_label(label_name: str) -> str:
    svc = gmail_service()

    for label in _list_labels():
        if label.get("name") == label_name:
            return label["id"]

    created = svc.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()

    return created["id"]


def apply_label(message_id: str, label_name: str) -> dict[str, Any]:
    svc = gmail_service()
    label_id = ensure_label(label_name)

    result = svc.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]},
    ).execute()

    return {
        "label_applied": True,
        "message_id": message_id,
        "label_name": label_name,
        "label_id": label_id,
        "result_label_ids": result.get("labelIds", []),
    }


def archive_email(message_id: str) -> dict[str, Any]:
    result = gmail_service().users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["INBOX"]},
    ).execute()

    return {"archived": True, "message_id": message_id, "result_label_ids": result.get("labelIds", [])}


def find_walkpa_drafts(max_results: int = 10) -> list[dict[str, Any]]:
    svc = gmail_service()
    response = svc.users().messages().list(
        userId="me",
        q=f'in:drafts "{WALKPA_DRAFT_MARKER}"',
        maxResults=max_results,
    ).execute()

    out = []
    for item in response.get("messages", []) or []:
        msg = svc.users().messages().get(userId="me", id=item["id"], format="metadata").execute()
        headers = msg.get("payload", {}).get("headers", []) or []
        out.append({
            "id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "subject": _header(headers, "Subject"),
            "to": _header(headers, "To"),
            "snippet": msg.get("snippet", ""),
        })
    return out


def find_walkpa_sent(max_results: int = 10) -> list[dict[str, Any]]:
    svc = gmail_service()
    response = svc.users().messages().list(
        userId="me",
        q=f'in:sent "{WALKPA_SENT_MARKER}"',
        maxResults=max_results,
    ).execute()

    out = []
    for item in response.get("messages", []) or []:
        msg = svc.users().messages().get(userId="me", id=item["id"], format="metadata").execute()
        headers = msg.get("payload", {}).get("headers", []) or []
        out.append({
            "id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "subject": _header(headers, "Subject"),
            "to": _header(headers, "To"),
            "snippet": msg.get("snippet", ""),
        })
    return out
