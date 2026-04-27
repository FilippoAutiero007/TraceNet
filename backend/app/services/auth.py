from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import jwt
from fastapi import HTTPException, Request

from app.config import settings


@dataclass
class AuthContext:
    user_id: str
    session_id: Optional[str]
    plan: Optional[str]
    plan_scope: Optional[str]
    is_pro: bool
    claims: dict[str, Any]


_JWKS_CACHE: dict[str, Any] = {"keys": None, "expires_at": 0.0}


def _parse_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer ") :].strip()
    return token or None


async def _get_jwks_keys() -> list[dict[str, Any]]:
    now = time.time()
    if _JWKS_CACHE["keys"] and now < float(_JWKS_CACHE["expires_at"]):
        return _JWKS_CACHE["keys"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.clerk_jwks_url)
        response.raise_for_status()
        data = response.json()

    keys = data.get("keys")
    if not isinstance(keys, list) or not keys:
        raise HTTPException(status_code=503, detail="Clerk JWKS unavailable")

    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["expires_at"] = now + 300
    return keys


def _extract_plan(claims: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    raw_plan = str(claims.get("pla") or "").strip()
    if not raw_plan or ":" not in raw_plan:
        return None, None
    scope, slug = raw_plan.split(":", 1)
    scope = scope.strip().lower()
    slug = slug.strip().lower()
    if scope not in {"u", "o"} or not slug:
        return None, None
    return scope, slug


def _is_pro_plan(plan_slug: Optional[str]) -> bool:
    if not plan_slug:
        return False
    allowed = {
        item.strip().lower()
        for item in settings.clerk_pro_plan_slugs.split(",")
        if item.strip()
    }
    return plan_slug.lower() in allowed


def _validate_authorized_party(claims: dict[str, Any], request: Request) -> None:
    configured = [
        item.strip()
        for item in settings.clerk_authorized_parties.split(",")
        if item.strip()
    ]
    if not configured:
        return

    azp = str(claims.get("azp") or "").strip()
    origin = request.headers.get("Origin", "").strip()
    if azp and azp in configured:
        return
    if origin and origin in configured:
        return
    raise HTTPException(status_code=401, detail="Unauthorized Clerk token audience")


async def verify_clerk_session_token(request: Request) -> AuthContext:
    token = _parse_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Clerk token header: {exc}") from exc

    if header.get("alg") != "RS256":
        raise HTTPException(status_code=401, detail="Unsupported Clerk token algorithm")

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Missing Clerk token key id")

    keys = await _get_jwks_keys()
    matching_key = next((key for key in keys if key.get("kid") == kid), None)
    if not matching_key:
        raise HTTPException(status_code=401, detail="Unknown Clerk signing key")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(matching_key))
    try:
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            options={"require": ["exp", "nbf", "sub"]},
            leeway=5,
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Clerk session token: {exc}") from exc

    _validate_authorized_party(claims, request)

    scope, plan_slug = _extract_plan(claims)
    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Clerk token missing user id")

    return AuthContext(
        user_id=user_id,
        session_id=str(claims.get("sid") or "").strip() or None,
        plan=plan_slug,
        plan_scope=scope,
        is_pro=_is_pro_plan(plan_slug),
        claims=claims,
    )


async def get_optional_auth_context(request: Request) -> Optional[AuthContext]:
    token = _parse_bearer_token(request)
    if not token:
        return None
    return await verify_clerk_session_token(request)


async def require_pro_user(request: Request) -> AuthContext:
    auth = await verify_clerk_session_token(request)
    if not auth.is_pro:
        raise HTTPException(status_code=403, detail="Pro plan required")
    return auth
