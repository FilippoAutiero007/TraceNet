"""
Utility helpers for building Packet Tracer XML payloads.

Only a minimal subset is needed for the current tests: label sanitization
that rejects potentially unsafe or malformed device names.
"""

from __future__ import annotations

import re

# Allow letters, numbers, underscores, hyphens, dots and spaces.
_SAFE_LABEL_RE = re.compile(r"^[A-Za-z0-9 _.-]{1,64}$")


def _sanitize_label(label: str | None, fallback: str) -> str:
    """
    Return a safe label for XML insertion.

    If the provided label is empty or contains characters outside the allowed
    whitelist, fall back to the provided default to avoid injection issues.
    """
    if not label:
        return fallback

    candidate = label.strip()
    if not _SAFE_LABEL_RE.match(candidate):
        return fallback
    return candidate


__all__ = ["_sanitize_label"]
