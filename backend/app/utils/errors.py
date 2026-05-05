"""Uniform error helpers for API responses and request-scoped diagnostics."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request


def get_request_id(request: Request | None) -> str | None:
    if request is None:
        return None
    return getattr(getattr(request, "state", None), "request_id", None)


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=message,
        headers={"X-Error-Code": code},
    )


def build_error_payload(
    *,
    request: Request | None,
    code: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": message,
        "code": code,
        "request_id": get_request_id(request),
    }
    if extra:
        payload.update(extra)
    return payload
