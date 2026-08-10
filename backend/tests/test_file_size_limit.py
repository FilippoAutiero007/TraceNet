import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import AuthContext, require_pro_user

client = TestClient(app)

# Mock AuthContext
mock_auth = AuthContext(
    user_id="user_123",
    session_id="sid_123",
    plan="pro",
    plan_scope="u",
    is_pro=True,
    claims={}
)

def get_mock_pro_user():
    return mock_auth

@pytest.fixture
def override_auth():
    app.dependency_overrides[require_pro_user] = get_mock_pro_user
    yield
    app.dependency_overrides.clear()

def test_analyze_pkt_size_limit_ok(override_auth):
    # 1KB file should pass
    content = b"P" * 1024
    files = {"file": ("test.pkt", content, "application/octet-stream")}
    response = client.post("/api/analyze-pkt", files=files)

    # It might fail with decoding error because it's not a real PKT,
    # but it shouldn't be a 413.
    assert response.status_code != 413

def test_analyze_pkt_size_limit_exceeded(override_auth):
    # 10MB + 1 byte file should fail
    limit = 10 * 1024 * 1024
    content = b"P" * (limit + 1)
    files = {"file": ("large.pkt", content, "application/octet-stream")}
    response = client.post("/api/analyze-pkt", files=files)

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"

def test_analyze_pkt_report_size_limit_exceeded(override_auth):
    # 10MB + 1 byte file should fail
    limit = 10 * 1024 * 1024
    content = b"P" * (limit + 1)
    files = {"file": ("large.pkt", content, "application/octet-stream")}
    response = client.post("/api/analyze-pkt-report", files=files)

    assert response.status_code == 413
    assert response.json()["code"] == "SEC_FILE_TOO_LARGE"
