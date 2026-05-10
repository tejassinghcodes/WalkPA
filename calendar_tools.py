"""
Google Calendar tool layer for WalkPA final.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from config import ALLOW_CALENDAR_CREATE
from google_auth import calendar_service


DEFAULT_TZ = "Australia/Melbourne"


def get_events(days_ahead: int = 4, timezone: str = DEFAULT_TZ) -> list[dict[str, Any]]:
    svc = calendar_service()
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    end = now + timedelta(days=days_ahead)

    response = svc.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=30,
    ).execute()

    events = []
    for e in response.get("items", []) or []:
        events.append({
            "id": e.get("id"),
            "summary": e.get("summary", "(no title)"),
            "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
            "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
            "location": e.get("location", ""),
            "htmlLink": e.get("htmlLink", ""),
        })
    return events


def _parse_dt(value: str, timezone: str = DEFAULT_TZ) -> datetime | None:
    if not value:
        return None
    tz = ZoneInfo(timezone)
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(tz)
        return datetime.fromisoformat(value).replace(tzinfo=tz)
    except Exception:
        return None


def _overlaps(start: datetime, end: datetime, events: list[dict[str, Any]], timezone: str = DEFAULT_TZ) -> bool:
    for event in events:
        event_start = _parse_dt(event.get("start", ""), timezone)
        event_end = _parse_dt(event.get("end", ""), timezone)
        if not event_start or not event_end:
            continue
        if "T" not in str(event.get("start", "")):
            if start.date() == event_start.date():
                return True
            continue
        if start < event_end and end > event_start:
            return True
    return False


def suggest_free_slot_options(
    events: list[dict[str, Any]],
    timezone: str = DEFAULT_TZ,
    days_ahead: int = 5,
    duration_minutes: int = 30,
    max_slots: int = 4,
) -> list[dict[str, str]]:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    candidate_hours = [9, 10, 11, 14, 15, 16]
    slots = []

    day = now
    checked = 0
    while len(slots) < max_slots and checked < days_ahead + 5:
        day = day + timedelta(days=1)
        checked += 1

        if day.weekday() >= 5:
            continue

        for hour in candidate_hours:
            start = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            end = start + timedelta(minutes=duration_minutes)

            if start <= now:
                continue
            if _overlaps(start, end, events, timezone):
                continue

            slots.append({
                "label": f"{start.strftime('%A %d %b, %I:%M %p')} - {end.strftime('%I:%M %p')}",
                "start_iso": start.isoformat(),
                "end_iso": end.isoformat(),
            })

            if len(slots) >= max_slots:
                break

    return slots


def suggest_free_slots(events: list[dict[str, Any]], timezone: str = DEFAULT_TZ) -> list[str]:
    return [slot["label"] for slot in suggest_free_slot_options(events, timezone=timezone)]


def create_calendar_hold(
    title: str,
    start_iso: str,
    end_iso: str,
    timezone: str = DEFAULT_TZ,
    description: str = "Created by WalkPA.",
    add_meet: bool = True,
) -> dict[str, Any]:
    if not ALLOW_CALENDAR_CREATE:
        return {"created": False, "reason": "Calendar creation disabled by ALLOW_CALENDAR_CREATE=false"}

    svc = calendar_service()
    event = {
        "summary": title,
        "start": {"dateTime": start_iso, "timeZone": timezone},
        "end": {"dateTime": end_iso, "timeZone": timezone},
        "description": description,
    }

    if add_meet:
        event["conferenceData"] = {
            "createRequest": {
                "requestId": f"walkpa-{uuid4().hex[:16]}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    created = svc.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1 if add_meet else 0,
    ).execute()

    meet_link = created.get("hangoutLink", "")
    if not meet_link:
        for entry in created.get("conferenceData", {}).get("entryPoints", []) or []:
            if entry.get("entryPointType") == "video":
                meet_link = entry.get("uri", "")
                break

    return {
        "created": True,
        "event_id": created.get("id"),
        "html_link": created.get("htmlLink"),
        "meet_link": meet_link,
        "summary": created.get("summary"),
        "start": created.get("start", {}),
        "end": created.get("end", {}),
    }
