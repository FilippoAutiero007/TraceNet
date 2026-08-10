import pytest
from unittest.mock import Mock
from app.services.auth import _validate_authorized_party
from app.config import settings
from fastapi import HTTPException

def test_validate_authorized_party_strictly_uses_azp(monkeypatch):
    # Mock settings
    monkeypatch.setattr(settings, "clerk_authorized_parties", "trusted-party,https://trusted-origin.com")

    # 1. Valid azp should pass
    claims = {"azp": "trusted-party"}
    request = Mock()
    request.headers = {}
    # Should not raise
    _validate_authorized_party(claims, request)

    # 2. Spoofed Origin header should FAIL
    claims = {"azp": "untrusted"}
    request = Mock()
    request.headers = {"Origin": "https://trusted-origin.com"}
    with pytest.raises(HTTPException) as excinfo:
        _validate_authorized_party(claims, request)
    assert excinfo.value.status_code == 401
    assert "AUTH_INVALID_TOKEN" in str(excinfo.value.headers)

    # 3. Missing azp should fail even if Origin is "trusted" (it's not enough anymore)
    claims = {}
    request = Mock()
    request.headers = {"Origin": "trusted-party"}
    with pytest.raises(HTTPException) as excinfo:
        _validate_authorized_party(claims, request)
    assert excinfo.value.status_code == 401
