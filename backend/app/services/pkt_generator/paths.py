"""Path resolution helpers for Packet Tracer templates."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def resolve_path(path_str: str) -> Optional[Path]:
    """
    Resolve a file path by checking absolute path, CWD, and standard project layouts.
    The 'templates/' candidates are only appended when the path_str does not already
    contain 'templates' to avoid duplicated entries.
    """
    if not path_str:
        return None

    path = Path(path_str)
    if path.is_absolute() and path.exists():
        return path

    candidates = [
        Path.cwd() / path_str,
        Path.cwd() / "backend" / path_str,
        Path(__file__).parent.parent.parent.parent / path_str,
    ]

    if "templates" not in path_str:
        candidates.append(Path.cwd() / "templates" / path_str)
        candidates.append(Path.cwd() / "backend" / "templates" / path_str)

    for cand in candidates:
        if cand.exists():
            return cand

    logger.debug("resolve_path: no candidate matched for %s", path_str)
    return None


def resolve_template_path() -> Path:
    """Legacy resolver for simple_ref.pkt, kept for compatibility."""
    for candidate in ("simple_ref.pkt", "templates/simple_ref.pkt"):
        resolved = resolve_path(candidate)
        if resolved:
            return resolved

    raise FileNotFoundError("simple_ref.pkt template not found.")
