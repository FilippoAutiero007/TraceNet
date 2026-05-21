import pytest
from pydantic import ValidationError
from app.models.schemas import ParseNetworkRequest, NormalizedNetworkRequest, SubnetRequest, DeviceConfig
from fastapi.testclient import TestClient
from app.main import app
import io

def test_parse_network_request_input_length():
    # max_length=2000
    valid_input = "a" * 2000
    invalid_input = "a" * 2001

    # Should not raise
    ParseNetworkRequest(user_input=valid_input)

    with pytest.raises(ValidationError):
        ParseNetworkRequest(user_input=invalid_input)

def test_normalized_network_request_limits():
    # routers le=50, switches le=50, pcs le=200, servers le=20
    valid_req = {
        "base_network": "192.168.1.0/24",
        "routers": 50,
        "switches": 50,
        "pcs": 200,
        "servers": 20,
        "routing_protocol": "STATIC"
    }
    NormalizedNetworkRequest(**valid_req)

    with pytest.raises(ValidationError):
        NormalizedNetworkRequest(**{**valid_req, "routers": 51})

    with pytest.raises(ValidationError):
        NormalizedNetworkRequest(**{**valid_req, "switches": 51})

    with pytest.raises(ValidationError):
        NormalizedNetworkRequest(**{**valid_req, "pcs": 201})

    with pytest.raises(ValidationError):
        NormalizedNetworkRequest(**{**valid_req, "servers": 21})

def test_subnet_request_name_length():
    # max_length=64
    valid_name = "a" * 64
    invalid_name = "a" * 65

    SubnetRequest(name=valid_name, required_hosts=10)

    with pytest.raises(ValidationError):
        SubnetRequest(name=invalid_name, required_hosts=10)

def test_analyze_pkt_size_limit():
    client = TestClient(app)

    # Mocking require_pro_user is needed if we want to hit the actual endpoint logic
    # But we can also just test the endpoint if it doesn't strictly check auth for this first part
    # Actually it's a Depends(require_pro_user), so we might need to mock it.

    # For a unit-like test of the router function, we can just call it or mock auth.
    # Since we are Sentinel and want to verify the FIX in the router:

    from app.services.auth import require_pro_user, AuthContext

    app.dependency_overrides[require_pro_user] = lambda: AuthContext(
        user_id="test_user", session_id="test_sid", plan="pro", plan_scope="u", is_pro=True, claims={}
    )

    try:
        # 10MB limit
        limit = 10 * 1024 * 1024

        # Small file - should pass size check (might fail later because it's not a real PKT, but that's fine)
        small_file = io.BytesIO(b"dummy content")
        response = client.post(
            "/api/analyze-pkt",
            files={"file": ("test.pkt", small_file, "application/octet-stream")},
            data={"exercise_text": "test"}
        )
        # It should NOT be 413
        assert response.status_code != 413

        # Large file - should fail size check
        large_file = io.BytesIO(b"a" * (limit + 1))
        response = client.post(
            "/api/analyze-pkt",
            files={"file": ("test.pkt", large_file, "application/octet-stream")},
            data={"exercise_text": "test"}
        )
        assert response.status_code == 413
        assert response.json()["code"] == "SEC_FILE_TOO_LARGE"

    finally:
        app.dependency_overrides = {}

if __name__ == "__main__":
    # This allows running the test script directly if needed
    pytest.main([__file__])
