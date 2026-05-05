"""Weekly generation quota tracking for authenticated and anonymous users."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from fastapi import Request

from app.config import settings
from app.services.auth import AuthContext
from app.utils.errors import api_error


@dataclass
class GenerationQuotaStatus:
    limit: int | None
    used: int
    remaining: int | None
    applies: bool


_GENERATION_COUNTS: dict[tuple[str, str], int] = {}
_GENERATION_COUNTS_LOCK = Lock()


def _current_week_key() -> str:
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def _quota_subject(auth: AuthContext | None, request: Request) -> str:
    if auth is not None:
        return auth.user_id
    client_host = request.client.host if request.client and request.client.host else "unknown"
    return f"anon:{client_host}"


def get_generation_quota_status(auth: AuthContext | None, request: Request) -> GenerationQuotaStatus:
    if auth is not None and auth.is_pro:
        return GenerationQuotaStatus(limit=None, used=0, remaining=None, applies=False)

    limit = settings.free_weekly_generation_limit
    week_key = _current_week_key()
    subject = _quota_subject(auth, request)
    with _GENERATION_COUNTS_LOCK:
        used = _GENERATION_COUNTS.get((subject, week_key), 0)
    remaining = max(0, limit - used)
    return GenerationQuotaStatus(limit=limit, used=used, remaining=remaining, applies=True)


def consume_generation_quota(auth: AuthContext | None, request: Request) -> GenerationQuotaStatus:
    status = get_generation_quota_status(auth, request)
    if not status.applies:
        return status

    if status.remaining is not None and status.remaining <= 0:
        raise api_error(
            429,
            "SEC_RATE_LIMIT",
            "Weekly network generation quota exceeded for your current plan.",
        )

    week_key = _current_week_key()
    subject = _quota_subject(auth, request)
    with _GENERATION_COUNTS_LOCK:
        new_used = _GENERATION_COUNTS.get((subject, week_key), 0) + 1
        _GENERATION_COUNTS[(subject, week_key)] = new_used

    remaining = max(0, settings.free_weekly_generation_limit - new_used)
    return GenerationQuotaStatus(
        limit=settings.free_weekly_generation_limit,
        used=new_used,
        remaining=remaining,
        applies=True,
    )


def reset_generation_quota_state() -> None:
    with _GENERATION_COUNTS_LOCK:
        _GENERATION_COUNTS.clear()
