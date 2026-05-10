"""
Google OAuth helpers.

This uses Google's installed desktop OAuth flow. Put credentials.json in the project root,
then run the app. The browser will open for consent and token.json will be saved locally.
"""

from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import CREDENTIALS_FILE, GOOGLE_SCOPES, TOKEN_FILE


def get_credentials() -> Credentials:
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GOOGLE_SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                "Missing credentials.json. Download OAuth Desktop credentials from Google Cloud "
                "and place the file in the project root."
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), GOOGLE_SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def gmail_service():
    return build("gmail", "v1", credentials=get_credentials())


def calendar_service():
    return build("calendar", "v3", credentials=get_credentials())
