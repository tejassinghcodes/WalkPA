"""
Central configuration for WalkPA.

Keep all scopes and environment variables here so the rest of the code stays clean.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "WalkPA"

ROOT_DIR = Path(__file__).resolve().parent
MEMORY_DIR = ROOT_DIR / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

CREDENTIALS_FILE = ROOT_DIR / "credentials.json"
TOKEN_FILE = ROOT_DIR / "token.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1").strip()

ALLOW_EMAIL_SEND = os.getenv("ALLOW_EMAIL_SEND", "false").lower() == "true"
ALLOW_CALENDAR_CREATE = os.getenv("ALLOW_CALENDAR_CREATE", "true").lower() == "true"

STYLE_PROFILE_FILE = MEMORY_DIR / "style_profile.json"
ACTION_LOG_FILE = MEMORY_DIR / "action_log.json"

# These scopes let the local demo read/modify Gmail, create drafts, and read/write Calendar.
# If you change these later, delete token.json and authenticate again.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
]
