import pytest

from app.services.pkt_crypto import decrypt_pkt_data


def test_decrypt_pkt_data_rejects_short_payload():
    with pytest.raises(ValueError):
        decrypt_pkt_data(b"abc")
