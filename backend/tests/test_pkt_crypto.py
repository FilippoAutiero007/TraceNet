import pytest
from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data

def test_decrypt_pkt_data_rejects_short_payload():
    with pytest.raises(ValueError):
        decrypt_pkt_data(b"abc")

def test_pkt_crypto_roundtrip():
    """Verify that encoding followed by decoding returns original content"""
    original_xml = b'<?xml version="1.0" encoding="utf-8"?>\n<PACKETTRACER5><VERSION>8.2.2</VERSION></PACKETTRACER5>'
    
    # Encode
    encoded = encrypt_pkt_data(original_xml)
    
    # Decode
    decoded = decrypt_pkt_data(encoded)
    
    assert decoded == original_xml
    assert len(encoded) > 0
