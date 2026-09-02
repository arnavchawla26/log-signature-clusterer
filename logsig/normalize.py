"""Regex-based normalization of volatile tokens in raw log lines.

Each substitution below runs over the *whole line* (not per whitespace
token) so that volatile values embedded inside larger strings -- e.g.
``request_id=550e8400-e29b-41d4-a716-446655440000`` or
``user-12345.json`` -- get normalized too, not just standalone tokens.

Order matters: more specific patterns (UUID, full timestamps) must run
before more general ones (bare numbers), otherwise the general pattern
would eat the specific one's digits first.
"""

from __future__ import annotations

import re

# --- placeholders -----------------------------------------------------

UUID = "<UUID>"
IP = "<IP>"
TIMESTAMP = "<TIMESTAMP>"
DATE = "<DATE>"
TIME = "<TIME>"
HEX = "<HEX>"
NUM = "<NUM>"

_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"

# --- patterns, in the order they must be applied -----------------------

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # UUID: 8-4-4-4-12 hex groups.
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        UUID,
    ),
    # IPv4 dotted-quad (with optional :port).
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b"), IP),
    # Syslog-style "Mon DD HH:MM:SS" (BSD syslog header).
    (
        re.compile(rf"\b{_MONTH}\s+\d{{1,2}}\s+\d{{2}}:\d{{2}}:\d{{2}}\b"),
        TIMESTAMP,
    ),
    # ISO 8601 date + time, e.g. 2024-01-15T10:30:00.123Z or with a space
    # separator and a numeric UTC offset.
    (
        re.compile(
            r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
            r"(?:Z|[+-]\d{2}:?\d{2})?\b"
        ),
        TIMESTAMP,
    ),
    # Bare ISO date, e.g. 2024-01-15.
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), DATE),
    # Bare time, e.g. 10:30:00 or 10:30:00.123.
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b"), TIME),
    # Hex strings of 6+ chars that contain at least one a-f letter (pure
    # decimal runs of digits are left for the NUM pattern below). No
    # trailing \b for the same reason as NUM below -- the char class
    # already stops at the first non-hex character, so the boundary
    # isn't needed and would only misfire when a hex run is glued to a
    # non-hex word character (e.g. a trailing unit or suffix).
    (re.compile(r"\b(?=[0-9a-fA-F]*[a-fA-F])[0-9a-fA-F]{6,}"), HEX),
    # Any remaining integer or float. Deliberately no trailing \b: a
    # digit run immediately followed by a unit or suffix letter (e.g.
    # "250ms", "3rd") is still a word character on both sides, so a
    # trailing \b would never fire and the number would be missed
    # entirely. Leaving it off means "250ms" normalizes to "<NUM>ms".
    (re.compile(r"\b\d+(?:\.\d+)?"), NUM),
]


def normalize_line(line: str) -> str:
    """Replace volatile substrings in ``line`` with stable placeholders."""
    for pattern, placeholder in _PATTERNS:
        line = pattern.sub(placeholder, line)
    return line
