import pytest
import re
from fastapi.testclient import TestClient
from app.main import app

def test_cors_origin_regex_fixed():
    # The regex is now anchored with $
    from app.main import origin_regex

    # Malicious subdomain suffixing should NOT match
    malicious_origin = "https://tracenet.vercel.app.attacker.com"
    assert re.match(origin_regex, malicious_origin) is None, "Regex should NOT match malicious suffix"

    # Valid origins should still match
    assert re.match(origin_regex, "https://tracenet.vercel.app") is not None
    assert re.match(origin_regex, "https://nettrace-git-main.vercel.app") is not None

def test_cors_middleware_with_malicious_origin():
    client = TestClient(app)
    malicious_origin = "https://tracenet.vercel.app.attacker.com"

    # Preflight request
    response = client.options(
        "/api/health",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "GET",
        }
    )

    # If fixed, the middleware should not return the malicious origin in Access-Control-Allow-Origin
    if "Access-Control-Allow-Origin" in response.headers:
        assert response.headers["Access-Control-Allow-Origin"] != malicious_origin, "CORS vulnerability: Malicious origin allowed!"
