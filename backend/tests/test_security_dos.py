import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import AuthContext, require_pro_user

client = TestClient(app)

def test_analyze_pkt_enforces_10mb_limit():
    # Mock Pro user authentication
    app.dependency_overrides[require_pro_user] = lambda: AuthContext(
        user_id="user_pro",
        session_id="sess_pro",
        plan="professional",
        plan_scope="u",
        is_pro=True,
        claims={"sub": "user_pro", "pla": "u:professional"},
    )

    # Create a dummy payload slightly larger than 10MB
    limit = 10 * 1024 * 1024
    large_data = b"0" * (limit + 1)

    response = client.post(
        "/api/analyze-pkt",
        files={"file": ("large.pkt", large_data, "application/octet-stream")},
    )

    assert response.status_code == 413
    payload = response.json()
    assert payload["code"] == "SEC_FILE_TOO_LARGE"
    assert "exceeds 10MB limit" in payload["error"]

    app.dependency_overrides.clear()
