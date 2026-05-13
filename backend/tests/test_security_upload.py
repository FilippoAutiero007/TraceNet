import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import AuthContext, require_pro_user

client = TestClient(app)

def mock_require_pro_user():
    return AuthContext(
        user_id="test_user",
        session_id="test_session",
        plan="pro",
        plan_scope="u",
        is_pro=True,
        claims={}
    )

@pytest.fixture
def auth_mock():
    app.dependency_overrides[require_pro_user] = mock_require_pro_user
    yield
    app.dependency_overrides.clear()

def test_analyze_pkt_size_limit(auth_mock):
    # 10MB + 1 byte
    large_data = b"0" * (10 * 1024 * 1024 + 1)
    files = {"file": ("test.pkt", large_data, "application/octet-stream")}

    response = client.post("/api/analyze-pkt", files=files)

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"

def test_analyze_pkt_under_limit(auth_mock):
    # Small data
    small_data = b"0" * 1024
    # Need to be a valid PKT for full analysis, but we just want to see if it passes the size check
    # and fails at decoding (which is after size check)
    files = {"file": ("test.pkt", small_data, "application/octet-stream")}

    response = client.post("/api/analyze-pkt", files=files)

    # It should pass the size check but fail because it's not a valid PKT
    # The decoding error is caught and returns 200 with success=False in PktAnalysisResponse
    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "PKT_DECODE_FAILED" in str(response.json()["issues"])
