"""Turn a raw log line into the token sequence used for clustering."""

from __future__ import annotations

from .normalize import normalize_line


def tokenize(raw_line: str) -> list[str]:
    """Normalize volatile substrings, then split on whitespace.

    Whitespace splitting happens *after* normalization so that a
    placeholder like ``<TIMESTAMP>`` (which contains no whitespace) is
    always a single token, and so a multi-word volatile value collapses
    to one token instead of several.
    """
    return normalize_line(raw_line.rstrip("\n")).split()
