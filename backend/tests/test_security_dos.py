import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_analyze_pkt_large_file_rejected():
    """
    Test that a large file (11MB) is rejected with 413 Payload Too Large.
    """
    large_data = b"0" * (11 * 1024 * 1024)
    response = client.post(
        "/api/analyze-pkt",
        files={"file": ("large.pkt", large_data, "application/octet-stream")},
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["code"] == "SEC_FILE_TOO_LARGE"
    assert "10MB" in payload["error"]

def test_analyze_pkt_report_large_file_rejected():
    """
    Test that a large file (11MB) is rejected with 413 in the report endpoint.
    """
    large_data = b"0" * (11 * 1024 * 1024)
    response = client.post(
        "/api/analyze-pkt-report",
        files={"file": ("large.pkt", large_data, "application/octet-stream")},
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["code"] == "SEC_FILE_TOO_LARGE"

def test_analyze_pkt_normal_file_read_attempted():
    """
    Test that a small file is still read (and then fails decryption as expected).
    """
    small_data = b"not-a-real-pkt"
    response = client.post(
        "/api/analyze-pkt",
        files={"file": ("small.pkt", small_data, "application/octet-stream")},
    )

    # 200 because analysis completes (with success=False)
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert any(i["code"] == "PKT_DECODE_FAILED" for i in payload["issues"])
