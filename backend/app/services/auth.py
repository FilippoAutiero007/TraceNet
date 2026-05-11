from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import jwt
from fastapi import HTTPException, Request

from app.config import settings
from app.utils.errors import api_error


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
        try:
            response = await client.get(settings.clerk_jwks_url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise api_error(503, "AUTH_PROVIDER_UNAVAILABLE", "Authentication service unavailable.") from exc

    keys = data.get("keys")
    if not isinstance(keys, list) or not keys:
        raise api_error(503, "AUTH_PROVIDER_UNAVAILABLE", "Authentication service unavailable.")

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
    if azp and azp in configured:
        return

    # We no longer check the Origin header here as it can be easily spoofed.
    # We rely on the azp claim which is verified as part of the JWT signature.
    raise api_error(401, "AUTH_INVALID_TOKEN", "Invalid authentication token.")


async def verify_clerk_session_token(request: Request) -> AuthContext:
    token = _parse_bearer_token(request)
    if not token:
        raise api_error(401, "AUTH_REQUIRED", "Authentication required.")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise api_error(401, "AUTH_INVALID_TOKEN", "Invalid authentication token.") from exc

    if header.get("alg") != "RS256":
        raise api_error(401, "AUTH_INVALID_TOKEN", "Invalid authentication token.")

    kid = header.get("kid")
    if not kid:
        raise api_error(401, "AUTH_INVALID_TOKEN", "Invalid authentication token.")

    keys = await _get_jwks_keys()
    matching_key = next((key for key in keys if key.get("kid") == kid), None)
    if not matching_key:
        raise api_error(401, "AUTH_INVALID_TOKEN", "Invalid authentication token.")

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
        raise api_error(401, "AUTH_INVALID_TOKEN", "Invalid authentication token.") from exc

    _validate_authorized_party(claims, request)

    scope, plan_slug = _extract_plan(claims)
    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise api_error(401, "AUTH_INVALID_TOKEN", "Invalid authentication token.")

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
    try:
        return await verify_clerk_session_token(request)
    except HTTPException as exc:
        # Optional auth should not block anonymous-safe endpoints if the auth
        # provider is temporarily unavailable. Invalid tokens must still fail.
        if exc.status_code == 503:
            return None
        raise


async def require_pro_user(request: Request) -> AuthContext:
    auth = await verify_clerk_session_token(request)
    if not auth.is_pro:
        raise api_error(403, "AUTH_PLAN_REQUIRED", "Pro plan required.")
    return auth
