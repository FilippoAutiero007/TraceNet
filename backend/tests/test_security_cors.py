import pytest
from fastapi.testclient import TestClient
from app.main import app
import re

client = TestClient(app)

def test_cors_vulnerability_regex_match():
    # This test directly verifies if the regex matches a malicious origin.
    # We are testing the configuration rather than Starlette's CORSMiddleware behavior,
    # which seems to have internal protections.
    from app.main import origin_regex

    pattern = re.compile(origin_regex)
    malicious_origin = "https://tracenet.vercel.app.attacker.com"

    # If vulnerable, this will be True
    assert not pattern.match(malicious_origin), f"VULNERABILITY: Regex {origin_regex} matches malicious origin {malicious_origin}"

def test_cors_legitimate_origin():
    # Legitimate origin
    legitimate_origin = "https://tracenet.vercel.app"

    response = client.options(
        "/api/health",
        headers={
            "Origin": legitimate_origin,
            "Access-Control-Request-Method": "GET",
        }
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == legitimate_origin

def test_cors_legitimate_preview_origin():
    # Legitimate preview origin
    legitimate_origin = "https://tracenet-git-main.vercel.app"

    response = client.options(
        "/api/health",
        headers={
            "Origin": legitimate_origin,
            "Access-Control-Request-Method": "GET",
        }
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == legitimate_origin
