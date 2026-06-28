import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_allowed_origin():
    # Test a legitimate origin from the static list
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_cors_allowed_regex_origin():
    # Test a legitimate origin matching the regex
    origin = "https://tracenet-git-main.vercel.app"
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin

def test_cors_disallowed_regex_bypass_attempt():
    # Test a malicious origin that attempts to bypass the regex by suffixing it
    malicious_origin = "https://tracenet.vercel.app.attacker.com"
    response = client.get("/api/health", headers={"Origin": malicious_origin})

    # When CORS rejects an origin, Starlette's CORSMiddleware does NOT return the Origin header
    # and might return a 400 or just ignore the CORS headers depending on the request type.
    # For a simple GET, it just won't include the CORS headers.
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None

def test_cors_preflight_disallowed_regex_bypass_attempt():
    # Test a malicious preflight request
    malicious_origin = "https://tracenet.vercel.app.attacker.com"
    response = client.options(
        "/api/health",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )

    # For preflight (OPTIONS), Starlette returns a 400 if the origin is not allowed
    # OR it might return a 200 but without the CORS headers.
    # Actually, Starlette CORSMiddleware returns 200 "OK" for disallowed origins
    # but WITHOUT the Access-Control-Allow-Origin header.
    assert response.status_code == 200 or response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None
