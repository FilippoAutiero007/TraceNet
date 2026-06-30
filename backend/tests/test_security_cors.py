import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_origin_regex_bypass():
    # Valid origin
    response = client.get(
        "/api/health",
        headers={"Origin": "https://tracenet.vercel.app"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://tracenet.vercel.app"

    # Malicious origin bypassing the unanchored regex
    malicious_origin = "https://tracenet.vercel.app.attacker.com"
    response = client.get(
        "/api/health",
        headers={"Origin": malicious_origin}
    )

    # If the regex is insecure, it will allow this origin
    # We WANT it to NOT allow this origin (i.e. not return the CORS header for it)
    assert response.headers.get("access-control-allow-origin") != malicious_origin
