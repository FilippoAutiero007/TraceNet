import pytest
import re
from fastapi.testclient import TestClient
from app.main import app

def test_cors_origin_regex_secure():
    """
    Test that the CORS origin regex is NOT vulnerable to subdomain suffixing bypass.
    The regex should NOT match the malicious origin because of the $ anchor.
    """
    # Get the regex from the app middleware
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "CORSMiddleware":
            cors_middleware = middleware
            break

    assert cors_middleware is not None

    origin_regex_str = cors_middleware.kwargs.get("allow_origin_regex")
    assert origin_regex_str is not None

    origin_regex = re.compile(origin_regex_str)
    malicious_origin = "https://tracenet.vercel.app.attacker.com"

    match = origin_regex.match(malicious_origin)
    # The match should be None because of the $ anchor
    assert match is None, f"Regex {origin_regex_str} should NOT match {malicious_origin} (fixed)"

def test_cors_origin_regex_valid():
    """
    Test that legitimate origins are still allowed.
    """
    client = TestClient(app)
    valid_origin = "https://tracenet.vercel.app"

    response = client.options(
        "/api/health",
        headers={
            "Origin": valid_origin,
            "Access-Control-Request-Method": "GET",
        }
    )

    assert response.headers.get("Access-Control-Allow-Origin") == valid_origin

def test_cors_origin_regex_valid_preview():
    """
    Test that Vercel preview/git branch origins are still allowed.
    """
    client = TestClient(app)
    valid_preview = "https://tracenet-git-feature-branch.vercel.app"

    response = client.options(
        "/api/health",
        headers={
            "Origin": valid_preview,
            "Access-Control-Request-Method": "GET",
        }
    )

    assert response.headers.get("Access-Control-Allow-Origin") == valid_preview
