import pytest
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_origin_bypass_fix():
    # This should be allowed
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

    # This SHOULD NOT be allowed (subdomain suffixing bypass)
    malicious_origin = "https://tracenet.vercel.app.attacker.com"
    response = client.options(
        "/api/health",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    # Starlette CORSMiddleware returns 400 if origin is rejected and allow_credentials=True
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None

def test_analyze_pkt_file_size_limit():
    # Create a small "pkt" file
    small_file = ("test.pkt", b"dummy data")

    # This should NOT trigger the 5MB limit but might fail for other reasons (like being invalid pkt)
    # However, we want to test that it DOES NOT return 413.
    response = client.post(
        "/api/analyze-pkt",
        files={"file": small_file}
    )
    assert response.status_code != 413

    # Create a "large" file (> 5MB)
    large_content = b"0" * (5 * 1024 * 1024 + 1)
    large_file = ("large.pkt", large_content)

    response = client.post(
        "/api/analyze-pkt",
        files={"file": large_file}
    )

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"

def test_analyze_pkt_report_file_size_limit():
    # Create a "large" file (> 5MB)
    large_content = b"0" * (5 * 1024 * 1024 + 1)
    large_file = ("large.pkt", large_content)

    response = client.post(
        "/api/analyze-pkt-report",
        files={"file": large_file}
    )

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"
