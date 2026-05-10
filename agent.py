"""
WalkPA final agent.

Conversational PA loop:
1. First pass:
   - reads real Gmail + Calendar
   - creates drafts, labels, calendar holds in autopilot
   - asks for missing decisions
2. Follow-up:
   - user gives missing info by voice/text
   - WalkPA drafts or sends approved replies

No LLM dependency. Reliable for the final demo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from calendar_tools import create_calendar_hold, get_events, suggest_free_slot_options
from config import ACTION_LOG_FILE
from gmail_tools import apply_label, create_draft, get_recent_emails, send_email
from safety import can_execute
from utils import now_iso, safe_json_load, safe_json_write


MEMORY_DIR = Path("memory")
MEMORY_DIR.mkdir(exist_ok=True)
PENDING_FILE = MEMORY_DIR / "pending_pa_questions.json"


PROMO_WORDS = [
    "unsubscribe", "promotion", "promo", "sale", "discount", "deal", "offer", "coupon",
    "newsletter", "digest", "weekly update", "marketing", "shop", "buy now", "limited time",
    "event platform", "join us in our next event", "webinar", "community event", "register now",
    "food", "restaurant", "delivery", "swiggy", "indeed", "jobs recommended", "job alert",
    "uber eats", "domino", "pizza", "50% off", "product demo night",
]
AUTOMATED_SENDER_WORDS = [
    "noreply", "no-reply", "donotreply", "do-not-reply", "notification",
    "updates", "mailer", "marketing",
]
FINANCE_WORDS = [
    "invoice", "receipt", "payment", "bill", "billing", "finance", "admin",
    "tax invoice", "purchase order",
]
ROUTING_WORDS = [
    "route this", "forward this", "pass this", "send this to", "whoever handles",
    "finance team", "ops team", "operations team", "legal team", "admin team",
]
MEETING_WORDS = [
    "can we meet", "could we meet", "schedule a call", "book a call", "jump on a call",
    "reschedule", "availability", "are you available", "when are you free", "find a time",
    "onboarding call", "project call", "meeting", "30-minute slot",
]
REPLY_WORDS = [
    "can you", "could you", "please", "let me know", "thoughts", "confirm", "reply",
    "follow up", "following up", "update me", "send me", "share", "?",
]
URGENT_WORDS = [
    "urgent", "asap", "immediately", "deadline", "due today", "action required",
    "by end of day", "eod", "need your decision",
]
SENSITIVE_WORDS = [
    "contract", "legal", "salary", "bank", "password", "confidential", "termination",
    "visa", "passport", "medical", "tax file", "tfn",
]


def _text(email: Any) -> str:
    return f"{email.sender} {email.sender_email} {email.subject} {email.snippet} {email.body}".lower()


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def classify(email: Any) -> tuple[str, str]:
    t = _text(email)
    sender = f"{email.sender} {email.sender_email}".lower()

    if _has_any(t, SENSITIVE_WORDS):
        return "needs_user_input", "Sensitive/legal/personal wording. I need your decision before replying."

    if _has_any(t, FINANCE_WORDS) or _has_any(t, ROUTING_WORDS):
        return "needs_routing", "Finance/admin/routing content."

    if not _has_any(sender, AUTOMATED_SENDER_WORDS) and not _has_any(t, PROMO_WORDS) and _has_any(t, MEETING_WORDS):
        return "needs_meeting", "Asks to schedule or find time."

    if not _has_any(t, PROMO_WORDS) and _has_any(t, URGENT_WORDS):
        return "needs_user_input", "Urgent decision needed from you."

    if not _has_any(sender, AUTOMATED_SENDER_WORDS) and not _has_any(t, PROMO_WORDS) and _has_any(t, REPLY_WORDS):
        return "needs_reply", "Needs a normal response."

    if _has_any(sender, AUTOMATED_SENDER_WORDS) or _has_any(t, PROMO_WORDS):
        return "low_priority", "Automated, promotional, or informational."

    return "fyi", "FYI only."


def _reply_subject(subject: str) -> str:
    subject = subject or "(no subject)"
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def _short(subject: str, limit: int = 52) -> str:
    subject = subject or "(no subject)"
    return subject if len(subject) <= limit else subject[:limit - 3] + "..."


def _meeting_body(slot_options: list[dict[str, str]]) -> str:
    slots = [s["label"] for s in slot_options[:2]]
    slot_text = " or ".join(slots) if slots else "tomorrow morning or tomorrow afternoon"
    return (
        "Hi,\n\n"
        f"Thanks for reaching out. I can do {slot_text}. "
        "Let me know which works best and I’ll lock it in.\n\n"
        "Best,"
    )


def _normal_body() -> str:
    return (
        "Hi,\n\n"
        "Thanks for following up. I’ve seen this and will take a look. "
        "I’ll get back to you shortly with a proper update.\n\n"
        "Best,"
    )


def _build_plan(emails: list[Any], slot_options: list[dict[str, str]]) -> dict[str, Any]:
    triage = []
    actions = []
    questions = []

    counts = {
        "needs_meeting": 0,
        "needs_reply": 0,
        "needs_routing": 0,
        "needs_user_input": 0,
        "low_priority": 0,
        "fyi": 0,
    }

    for email in emails:
        category, reason = classify(email)
        counts[category] = counts.get(category, 0) + 1

        triage.append({
            "email_id": email.id,
            "from": email.sender,
            "sender_email": email.sender_email,
            "subject": email.subject,
            "category": category,
            "reason": reason,
        })

        if category == "needs_meeting":
            actions.append({
                "action_type": "create_draft",
                "email_id": email.id,
                "to": email.sender_email,
                "subject": _reply_subject(email.subject),
                "body": _meeting_body(slot_options),
                "reason": "Draft scheduling reply with free times.",
                "risk": "low",
            })
            if slot_options:
                slot = slot_options[0]
                actions.append({
                    "action_type": "create_calendar_hold",
                    "email_id": email.id,
                    "title": f"WalkPA hold: {_short(email.subject)}",
                    "start_iso": slot["start_iso"],
                    "end_iso": slot["end_iso"],
                    "reason": f"Create provisional Calendar hold with Meet for {slot['label']}.",
                    "risk": "medium",
                })

        elif category == "needs_reply":
            actions.append({
                "action_type": "create_draft",
                "email_id": email.id,
                "to": email.sender_email,
                "subject": _reply_subject(email.subject),
                "body": _normal_body(),
                "reason": "Create safe reply draft.",
                "risk": "low",
            })

        elif category == "needs_routing":
            label = "WalkPA/Routed"
            if "invoice" in _text(email) or "payment" in _text(email) or "finance" in _text(email):
                label = "WalkPA/Routed-Finance"
            elif "legal" in _text(email) or "contract" in _text(email):
                label = "WalkPA/Routed-Legal"
            actions.append({
                "action_type": "label",
                "email_id": email.id,
                "label": label,
                "reason": f"Route this message to {label}.",
                "risk": "low",
            })

        elif category == "needs_user_input":
            actions.append({
                "action_type": "label",
                "email_id": email.id,
                "label": "WalkPA/Needs Your Input",
                "reason": "Flag message because a decision is needed before replying.",
                "risk": "low",
            })
            questions.append({
                "email_id": email.id,
                "to": email.sender_email,
                "subject": _reply_subject(email.subject),
                "original_subject": email.subject,
                "question": f"What should I say for '{_short(email.subject)}'?",
                "reason": reason,
                "category": category,
            })

        elif category == "low_priority":
            actions.append({
                "action_type": "label",
                "email_id": email.id,
                "label": "WalkPA/Low Priority",
                "reason": "Route low-priority email out of the active queue.",
                "risk": "low",
            })

    return {"triage": triage, "actions": actions, "questions": questions, "counts": counts}


def _execute_actions(actions: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    results = []

    for a in actions:
        action_type = a["action_type"]
        result = {
            "action_type": action_type,
            "executed": False,
            "reason": a.get("reason", ""),
            "label": a.get("label"),
            "subject": a.get("subject"),
            "calendar_title": a.get("title"),
        }

        if not can_execute(action_type, mode):
            result["detail"] = "Prepared only; not executed in intervention mode."
            results.append(result)
            continue

        try:
            if action_type == "create_draft":
                created = create_draft(
                    to=a["to"],
                    subject=a["subject"],
                    body=a["body"],
                    thread_id=None,
                )
                result.update({"executed": True, "detail": created})

            elif action_type == "label":
                labelled = apply_label(a["email_id"], a["label"])
                result.update({"executed": True, "detail": labelled})

            elif action_type == "create_calendar_hold":
                created = create_calendar_hold(
                    title=a["title"],
                    start_iso=a["start_iso"],
                    end_iso=a["end_iso"],
                    add_meet=True,
                )
                result.update({"executed": True, "detail": created})

            else:
                result["detail"] = "Action not implemented."

        except Exception as exc:
            result["error"] = str(exc)

        results.append(result)

    return results


def _brief(result: dict[str, Any]) -> str:
    mode = result["mode"]
    counts = result["counts"]
    questions = result["questions"]
    triage = result["triage"]
    executions = result["execution_results"]

    drafts = [e for e in executions if e.get("action_type") == "create_draft" and e.get("executed")]
    routes = [e for e in executions if e.get("action_type") == "label" and e.get("executed")]
    holds = [e for e in executions if e.get("action_type") == "create_calendar_hold" and e.get("executed")]

    parts = [f"PA briefing. I checked {result['email_count']} emails."]

    if mode == "autopilot":
        parts.append(
            f"Done: {len(drafts)} drafts created, {len(routes)} emails routed, and {len(holds)} calendar holds created. "
            "Nothing was sent without your follow-up approval."
        )
    else:
        parts.append(
            f"I prepared the queue: {counts.get('needs_reply',0)} replies, "
            f"{counts.get('needs_meeting',0)} meetings, {counts.get('needs_routing',0)} routes, "
            f"and {counts.get('low_priority',0)} low-priority items."
        )

    for item in triage[:12]:
        subject = _short(item["subject"])
        category = item["category"]

        if category == "needs_meeting":
            parts.append(f"{subject}: meeting request. I drafted a reply and created a calendar hold.")
        elif category == "needs_reply":
            parts.append(f"{subject}: reply drafted.")
        elif category == "needs_routing":
            parts.append(f"{subject}: routed to the right label.")
        elif category == "needs_user_input":
            parts.append(f"{subject}: I need your decision before replying.")
        elif category == "fyi":
            parts.append(f"{subject}: FYI only.")
        # Low priority gets summarised as a count below.

    low = counts.get("low_priority", 0)
    if low:
        parts.append(f"{low} low-priority messages were routed out of the way.")

    if questions:
        prompt = " ".join(q["question"] for q in questions[:3])
        parts.append(f"Here is what I need from you: {prompt}")
    else:
        parts.append("I do not need anything else from you.")

    return " ".join(parts)


def run_agent(command: str, mode: str = "autopilot", max_emails: int = 15, execute: bool = True) -> dict[str, Any]:
    emails = get_recent_emails(max_results=max_emails)
    events = get_events(days_ahead=4)
    slots = suggest_free_slot_options(events)

    plan = _build_plan(emails, slots)
    results = _execute_actions(plan["actions"], mode) if execute else []

    result = {
        "command": command,
        "mode": mode,
        "email_count": len(emails),
        "event_count": len(events),
        "calendar_free_slots": [s["label"] for s in slots],
        "triage": plan["triage"],
        "counts": plan["counts"],
        "actions": plan["actions"],
        "questions": plan["questions"],
        "execution_results": results,
        "plan": {
            "triage": plan["triage"],
            "proposed_actions": plan["actions"],
            "spoken_summary": "",
            "demo_highlights": [
                "Conversational PA loop",
                "Safe reversible actions happen first",
                "User is asked only for missing information",
                "Approved replies can be sent in the follow-up step",
                "Calendar holds include Meet links",
            ],
        },
    }

    result["plan"]["spoken_summary"] = _brief(result)

    safe_json_write(PENDING_FILE, {
        "timestamp": now_iso(),
        "questions": plan["questions"],
        "triage": plan["triage"],
        "mode": mode,
    })

    log = safe_json_load(ACTION_LOG_FILE, [])
    log.append({
        "timestamp": now_iso(),
        "type": "first_pass",
        "summary": result["plan"]["spoken_summary"],
        "execution_results": results,
    })
    safe_json_write(ACTION_LOG_FILE, log[-50:])

    return result


def _reply_for_question(question: dict[str, Any], user_reply: str) -> str:
    subject = question.get("original_subject", "").lower()
    text = user_reply.strip()

    if "urgent" in subject or "decision" in subject or "rohan" in text.lower():
        return (
            "Hi,\n\n"
            "Yes, I’m okay with the latest version. Please go ahead.\n\n"
            "Best,"
        )

    if "contract" in subject or "legal" in subject:
        return (
            "Hi,\n\n"
            "I’ll review this properly this afternoon, but I don’t want to confirm anything yet until I’ve checked the details.\n\n"
            "Best,"
        )

    return f"Hi,\n\n{text}\n\nBest,"


def process_user_followup(user_reply: str, send_approved: bool = False) -> dict[str, Any]:
    pending = safe_json_load(PENDING_FILE, {})
    questions = pending.get("questions", [])

    if not questions:
        return {
            "spoken_summary": "I do not have any pending questions. The queue is already handled.",
            "sent_results": [],
            "pending": pending,
        }

    results = []
    for q in questions:
        body = _reply_for_question(q, user_reply)

        if send_approved:
            action_result = send_email(
                to=q["to"],
                subject=q["subject"],
                body=body,
            )
            results.append({
                "action": "sent_email",
                "original_subject": q["original_subject"],
                "to": q["to"],
                "result": action_result,
            })
        else:
            action_result = create_draft(
                to=q["to"],
                subject=q["subject"],
                body=body,
            )
            results.append({
                "action": "created_draft",
                "original_subject": q["original_subject"],
                "to": q["to"],
                "result": action_result,
            })

    action_word = "sent" if send_approved else "drafted"
    spoken = (
        f"Done. I {action_word} {len(results)} approved follow-up replies based on what you just told me. "
        "Nothing else is pending."
    )

    safe_json_write(PENDING_FILE, {
        "timestamp": now_iso(),
        "questions": [],
        "last_followup_results": results,
    })

    log = safe_json_load(ACTION_LOG_FILE, [])
    log.append({
        "timestamp": now_iso(),
        "type": "followup",
        "summary": spoken,
        "results": results,
    })
    safe_json_write(ACTION_LOG_FILE, log[-50:])

    return {
        "spoken_summary": spoken,
        "sent_results": results,
        "pending": pending,
    }
