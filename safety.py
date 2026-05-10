"""
WalkPA bounded autonomy safety policy.
"""


LOW_RISK_ACTIONS = {
    "create_draft",
    "label",
    "suggest_slot",
}

MEDIUM_RISK_ACTIONS = {
    "create_calendar_hold",
    "archive",
}

HIGH_RISK_ACTIONS = {
    "send_email",
    "delete_email",
    "decline_meeting",
    "forward_email",
}


def can_execute(action_type: str, mode: str) -> bool:
    action_type = (action_type or "").strip()
    mode = (mode or "intervention").strip().lower()

    if mode != "autopilot":
        return False

    if action_type in HIGH_RISK_ACTIONS:
        return False

    return action_type in LOW_RISK_ACTIONS or action_type in MEDIUM_RISK_ACTIONS
