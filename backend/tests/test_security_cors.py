import pytest
import re
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_origin_regex_vulnerability():
    # Valid origin
    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://tracenet.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://tracenet.vercel.app"

    # Malicious origin exploiting lack of anchor
    malicious_origin = "https://tracenet.vercel.app.attacker.com"
    response = client.options(
        "/api/health",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    allow_origin = response.headers.get("access-control-allow-origin")
    print(f"Allow Origin for malicious: {allow_origin}")

    # If vulnerable, allow_origin will be malicious_origin because Starlette's
    # CORSMiddleware uses re.match which matches from the START of the string.
    # If the regex doesn't have $, it will match 'https://tracenet.vercel.app'
    # as a prefix of 'https://tracenet.vercel.app.attacker.com'.

    assert allow_origin != malicious_origin, f"Vulnerability confirmed: {malicious_origin} allowed!"

if __name__ == "__main__":
    pytest.main(["-s", __file__])
