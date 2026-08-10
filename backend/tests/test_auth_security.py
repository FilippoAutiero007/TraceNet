import pytest
from fastapi import Request
from app.services.auth import _validate_authorized_party
from app.config import settings
from app.utils.errors import HTTPException

def test_validate_authorized_party_success(monkeypatch):
    monkeypatch.setattr(settings, "clerk_authorized_parties", "http://localhost:5173,https://tracenet.vercel.app")
    claims = {"azp": "http://localhost:5173"}
    request = Request({"type": "http", "headers": []})

    # Should not raise
    _validate_authorized_party(claims, request)

def test_validate_authorized_party_rejects_spoofed_origin(monkeypatch):
    monkeypatch.setattr(settings, "clerk_authorized_parties", "http://localhost:5173")

    # azp is wrong, but Origin is "correct" (spoofed)
    claims = {"azp": "http://attacker.com"}
    request = Request({
        "type": "http",
        "headers": [(b"origin", b"http://localhost:5173")]
    })

    with pytest.raises(HTTPException) as excinfo:
        _validate_authorized_party(claims, request)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid authentication token."

def test_validate_authorized_party_no_configured_parties(monkeypatch):
    monkeypatch.setattr(settings, "clerk_authorized_parties", "")
    claims = {"azp": "http://anything.com"}
    request = Request({"type": "http", "headers": []})

    # Should not raise when no parties are configured (open for dev/testing)
    _validate_authorized_party(claims, request)

def test_validate_authorized_party_missing_azp(monkeypatch):
    monkeypatch.setattr(settings, "clerk_authorized_parties", "http://localhost:5173")
    claims = {}
    request = Request({"type": "http", "headers": []})

    with pytest.raises(HTTPException) as excinfo:
        _validate_authorized_party(claims, request)

    assert excinfo.value.status_code == 401
