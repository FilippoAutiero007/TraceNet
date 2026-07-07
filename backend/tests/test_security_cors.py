import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_security_subdomain_suffixing():
    """
    Ensure the CORS regex is anchored and does NOT allow subdomain suffixing.
    An origin like https://tracenet.vercel.app.attacker.com must be REJECTED.
    """
    malicious_origin = "https://tracenet.vercel.app.attacker.com"

    response = client.options(
        "/api/health",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "GET",
        }
    )

    # Starlette's CORSMiddleware returns 400 for preflight if allow_credentials=True
    # and Origin is NOT allowed.
    assert response.status_code == 400, f"Malicious origin {malicious_origin} should be rejected with 400"

def test_cors_legitimate_origin():
    """Ensure legitimate origins are still allowed."""
    legit_origins = [
        "https://tracenet.vercel.app",
        "https://tracenet-git-main.vercel.app",
        "https://nettrace.vercel.app",
    ]
    for legit_origin in legit_origins:
        response = client.options(
            "/api/health",
            headers={
                "Origin": legit_origin,
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == legit_origin
