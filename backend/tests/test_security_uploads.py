import pytest
from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)

def test_analyze_pkt_size_limit():
    # Valid small file
    small_file = io.BytesIO(b"dummy data")
    response = client.post(
        "/api/analyze-pkt",
        files={"file": ("test.pkt", small_file, "application/octet-stream")}
    )
    # It might fail with 400 because of invalid PKT format, but it should NOT be 413
    assert response.status_code != 413

    # Oversized file (> 5MB)
    large_content = b"0" * (5 * 1024 * 1024 + 1)
    large_file = io.BytesIO(large_content)
    response = client.post(
        "/api/analyze-pkt",
        files={"file": ("large.pkt", large_file, "application/octet-stream")}
    )

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"

def test_analyze_pkt_report_size_limit():
    # Oversized file (> 5MB)
    large_content = b"0" * (5 * 1024 * 1024 + 1)
    large_file = io.BytesIO(large_content)
    response = client.post(
        "/api/analyze-pkt-report",
        files={"file": ("large.pkt", large_file, "application/octet-stream")}
    )

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"
