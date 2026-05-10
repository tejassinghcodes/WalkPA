"""
Writing-style memory for WalkPA.

The style profile is intentionally lightweight so it is reliable for a 4-hour build:
- sample sent emails
- ask the LLM to extract tone, structure, and sign-off habits
- save to local JSON
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL, STYLE_PROFILE_FILE
from gmail_tools import get_sent_email_samples
from utils import safe_json_load, safe_json_write, now_iso


DEFAULT_STYLE_PROFILE = {
    "tone": "natural, concise, friendly, and direct",
    "greeting": "short greeting when appropriate",
    "sentence_style": "clear sentences, not overly formal",
    "signoff": "use a simple sign-off if the context needs it",
    "do": ["sound human", "be concise", "be useful"],
    "dont": ["do not sound corporate", "do not over-explain", "do not use filler"],
    "updated_at": None,
}


def load_style_profile() -> dict[str, Any]:
    return safe_json_load(STYLE_PROFILE_FILE, DEFAULT_STYLE_PROFILE)


def refresh_style_profile() -> dict[str, Any]:
    samples = get_sent_email_samples(max_results=8)

    if not OPENAI_API_KEY:
        profile = DEFAULT_STYLE_PROFILE | {
            "updated_at": now_iso(),
            "note": "OPENAI_API_KEY missing, using default profile.",
        }
        safe_json_write(STYLE_PROFILE_FILE, profile)
        return profile

    sample_text = "\n\n---\n\n".join(
        f"Subject: {s['subject']}\nTo: {s['to']}\nBody:\n{s['body']}"
        for s in samples
        if s.get("body")
    )[:9000]

    if not sample_text.strip():
        profile = DEFAULT_STYLE_PROFILE | {
            "updated_at": now_iso(),
            "note": "No sent email samples found, using default profile.",
        }
        safe_json_write(STYLE_PROFILE_FILE, profile)
        return profile

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "You extract a user's email writing style. Return compact JSON only.",
            },
            {
                "role": "user",
                "content": f"""
From these sent emails, infer a reusable writing style profile.

Return JSON with:
tone, greeting, sentence_style, signoff, do, dont.

Sent emails:
{sample_text}
""",
            },
        ],
    )

    content = response.choices[0].message.content or "{}"

    import json
    try:
        profile = json.loads(content)
    except Exception:
        profile = DEFAULT_STYLE_PROFILE | {"raw_model_output": content}

    profile["updated_at"] = now_iso()
    safe_json_write(STYLE_PROFILE_FILE, profile)
    return profile
