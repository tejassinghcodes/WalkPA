"""
Verify WalkPA final real-world actions.

Run:
python verify_walkpa_actions.py
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from gmail_tools import find_walkpa_drafts, find_walkpa_sent
from google_auth import calendar_service, gmail_service


def labels():
    all_labels = gmail_service().users().labels().list(userId="me").execute().get("labels", [])
    return [label for label in all_labels if label.get("name", "").startswith("WalkPA")]


def calendar_events():
    tz = ZoneInfo("Australia/Melbourne")
    now = datetime.now(tz) - timedelta(days=1)
    future = now + timedelta(days=7)

    events = calendar_service().events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=future.isoformat(),
        q="WalkPA",
        singleEvents=True,
        orderBy="startTime",
        maxResults=20,
    ).execute().get("items", [])

    return [
        {
            "summary": e.get("summary"),
            "start": e.get("start"),
            "end": e.get("end"),
            "htmlLink": e.get("htmlLink"),
            "hangoutLink": e.get("hangoutLink"),
        }
        for e in events
    ]


if __name__ == "__main__":
    print(json.dumps({
        "drafts": find_walkpa_drafts(),
        "sent": find_walkpa_sent(),
        "labels": labels(),
        "calendar_events": calendar_events(),
    }, indent=2, ensure_ascii=False))
