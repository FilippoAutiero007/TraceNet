import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_analyze_pkt_file_size_limit():
    client = TestClient(app)

    # 11MB file (exceeds 10MB limit)
    large_content = b"a" * (11 * 1024 * 1024)
    files = {"file": ("test.pkt", large_content, "application/octet-stream")}

    response = client.post("/api/analyze-pkt", files=files)

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"

def test_analyze_pkt_report_file_size_limit():
    client = TestClient(app)

    # 11MB file
    large_content = b"a" * (11 * 1024 * 1024)
    files = {"file": ("test.pkt", large_content, "application/octet-stream")}

    response = client.post("/api/analyze-pkt-report", files=files)

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"

def test_analyze_pkt_within_limit():
    client = TestClient(app)

    # 1KB file (within limit)
    content = b"a" * 1024
    files = {"file": ("test.pkt", content, "application/octet-stream")}

    response = client.post("/api/analyze-pkt", files=files)

    # It shouldn't be 413.
    assert response.status_code != 413
