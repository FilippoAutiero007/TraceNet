import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_allowed_origin():
    """Verify that a legitimate origin is allowed."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://tracenet.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://tracenet.vercel.app"

def test_cors_preview_origin():
    """Verify that a Vercel preview origin is allowed."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://tracenet-git-main.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://tracenet-git-main.vercel.app"

def test_cors_disallowed_origin_suffix():
    """Verify that an origin with a malicious suffix is disallowed (CORS bypass attempt)."""
    # Starlette CORSMiddleware returns 400 or just doesn't include CORS headers if Origin doesn't match
    # when allow_origin_regex is used.
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://tracenet.vercel.app.attacker.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # If the origin is not allowed, Starlette might return 400 if allow_credentials is True
    # or just return 200 WITHOUT the access-control-allow-origin header.
    assert response.status_code != 200 or "access-control-allow-origin" not in response.headers

def test_cors_disallowed_origin_arbitrary():
    """Verify that an arbitrary origin is disallowed."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code != 200 or "access-control-allow-origin" not in response.headers
