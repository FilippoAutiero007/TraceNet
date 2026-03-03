"""Small XML/label sanitization helpers.

This module exists primarily as a stable import path for older code/tests.
"""

from __future__ import annotations

import re


_SAFE_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _sanitize_label(label: str, fallback: str) -> str:
    """Return `label` if it's safe, otherwise fall back to `fallback`."""
    if label is None:
        return fallback
    candidate = str(label).strip()
    return candidate if _SAFE_LABEL_RE.match(candidate) else fallback


__all__ = ["_sanitize_label"]

