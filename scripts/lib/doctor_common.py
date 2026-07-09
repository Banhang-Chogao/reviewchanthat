"""Shared helpers for Deployment Doctor scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = REPO_ROOT / "reports"
DOCTOR_LOGS_DIR = REPORTS_DIR / "deployment-doctor" / "logs"

SECRET_PATTERNS = [
    re.compile(r"(?i)(gh[pousr]_[A-Za-z0-9_]{20,})"),
    re.compile(r"(?i)(github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"(?i)(xox[baprs]-[A-Za-z0-9-]{10,})"),
    re.compile(r"(?i)(AKIA[0-9A-Z]{16})"),
    re.compile(r"(?i)(-----BEGIN[ A-Z]*PRIVATE KEY-----[\s\S]*?-----END[ A-Z]*PRIVATE KEY-----)"),
    re.compile(r"(?i)(Bearer\s+[A-Za-z0-9\-._~+/]+=*)"),
    re.compile(
        r"(?i)((?:PEXELS_API_KEY|PIXABAY_API_KEY|UNSPLASH_ACCESS_KEY|GITHUB_TOKEN|GH_TOKEN|"
        r"GOOGLE_APPLICATION_CREDENTIALS(?:_JSON)?)\s*[=:]\s*)(\S+)"
    ),
    re.compile(r"(?i)([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"),
]

REDACT_REPLACEMENT = "[REDACTED]"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def redact_secrets(text: str) -> str:
    if not text:
        return ""
    out = text
    for pat in SECRET_PATTERNS:
        if pat.groups >= 2:
            out = pat.sub(lambda m: f"{m.group(1)}{REDACT_REPLACEMENT}", out)
        else:
            out = pat.sub(REDACT_REPLACEMENT, out)
    # Hard token names left as keys only
    for key in (
        "PEXELS_API_KEY",
        "PIXABAY_API_KEY",
        "UNSPLASH_ACCESS_KEY",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "BEGIN PRIVATE KEY",
    ):
        out = out.replace(key + "=", key + "=[REDACTED]")
    return out


def truncate_log(text: str, max_chars: int = 80_000) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: max_chars // 2]
    tail = text[-(max_chars // 2) :]
    return head + "\n\n...[truncated]...\n\n" + tail


def attempt_key(sha: str, failure_type: str) -> str:
    short = (sha or "unknown")[:12]
    return f"{short}:{failure_type}"
