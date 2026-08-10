import pytest
from fastapi import Request
from unittest.mock import MagicMock
from app.services.auth import _validate_authorized_party
from app.config import settings
from app.utils.errors import api_error
from fastapi import HTTPException

def test_validate_authorized_party_secure(monkeypatch):
    """
    Verifies that the implementation strictly enforces AZP claim validation
    and rejects spoofed Origin headers.
    """
    # Setup configured authorized parties
    monkeypatch.setattr(settings, "clerk_authorized_parties", "https://trusted-app.com")

    # 1. Case: Valid AZP (Should pass)
    claims_valid_azp = {"azp": "https://trusted-app.com"}
    request_no_origin = MagicMock(spec=Request)
    request_no_origin.headers = {}

    # Should not raise
    _validate_authorized_party(claims_valid_azp, request_no_origin)

    # 2. Case: Missing AZP, but spoofed Origin (Should now FAIL)
    claims_no_azp = {"sub": "user_123"} # No azp claim
    request_spoofed_origin = MagicMock(spec=Request)
    request_spoofed_origin.headers = {"Origin": "https://trusted-app.com"}

    with pytest.raises(HTTPException) as excinfo:
        _validate_authorized_party(claims_no_azp, request_spoofed_origin)
    assert excinfo.value.status_code == 401

    # 3. Case: Invalid both (Should fail)
    claims_invalid_azp = {"azp": "https://attacker.com"}
    request_invalid_origin = MagicMock(spec=Request)
    request_invalid_origin.headers = {"Origin": "https://attacker.com"}

    with pytest.raises(HTTPException) as excinfo:
        _validate_authorized_party(claims_invalid_azp, request_invalid_origin)
    assert excinfo.value.status_code == 401
