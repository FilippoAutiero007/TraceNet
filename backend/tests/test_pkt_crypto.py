"""
Crypto unit tests for pkt_crypto.py.

Covers:
  - Reject short/invalid payload
  - Roundtrip on synthetic XML
  - Roundtrip on the real simple_ref.pkt template (746 KB)
  - obf_stage2 is self-inverse
  - Decrypted XML starts with the expected PT root tag
"""
from __future__ import annotations

from pathlib import Path

import pytest
from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data, obf_stage2

TEMPLATE = Path(__file__).parent.parent / "templates" / "simple_ref.pkt"


# ---------------------------------------------------------------------------
# Basic error handling
# ---------------------------------------------------------------------------

def test_decrypt_pkt_data_rejects_short_payload():
    with pytest.raises((ValueError, Exception)):
        decrypt_pkt_data(b"abc")


# ---------------------------------------------------------------------------
# Roundtrip on synthetic XML
# ---------------------------------------------------------------------------

def test_pkt_crypto_roundtrip_synthetic():
    """Encoding followed by decoding returns the original content (small payload)."""
    original_xml = (
        b'<?xml version="1.0" encoding="utf-8"?>\n'
        b'<PACKETTRACER5><VERSION>8.2.2</VERSION></PACKETTRACER5>'
    )
    encoded = encrypt_pkt_data(original_xml)
    decoded = decrypt_pkt_data(encoded)

    assert decoded == original_xml
    assert len(encoded) > 0


# ---------------------------------------------------------------------------
# Roundtrip on the real template
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not TEMPLATE.exists(), reason="simple_ref.pkt template not found")
def test_pkt_crypto_roundtrip_template():
    """
    Decrypt simple_ref.pkt → re-encrypt → re-decrypt must produce identical XML.
    This proves the crypto pipeline is byte-stable on a real PT file.
    """
    raw_pkt = TEMPLATE.read_bytes()
    xml_bytes = decrypt_pkt_data(raw_pkt)

    assert len(xml_bytes) > 100_000, "Decrypted XML suspiciously small"
    assert xml_bytes.lstrip().startswith(b"<PACKETTRACER5"), (
        "Decrypted XML does not start with <PACKETTRACER5>"
    )

    re_enc = encrypt_pkt_data(xml_bytes)
    xml_check = decrypt_pkt_data(re_enc)

    assert xml_check == xml_bytes, (
        "decrypt(encrypt(xml)) != xml – crypto pipeline is NOT self-inverse"
    )


# ---------------------------------------------------------------------------
# obf_stage2 self-inverse
# ---------------------------------------------------------------------------

def test_obf_stage2_self_inverse_short():
    """obf_stage2(obf_stage2(data)) == data for a short payload."""
    data = b"Hello, Packet Tracer!"
    assert obf_stage2(obf_stage2(data)) == data


def test_obf_stage2_self_inverse_large():
    """obf_stage2 is self-inverse for payloads longer than 256 bytes (> 0xFF)."""
    data = bytes(range(256)) * 4  # 1024 bytes, exercises the > 0xFF path
    assert obf_stage2(obf_stage2(data)) == data
