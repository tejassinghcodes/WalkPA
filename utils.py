"""
Small utilities shared across the project.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from email.utils import parseaddr
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_json_write(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clean_text(text: str, limit: int = 4000) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def email_address(value: str) -> str:
    return parseaddr(value or "")[1] or value


def person_name(value: str) -> str:
    name, addr = parseaddr(value or "")
    return name or addr or value
