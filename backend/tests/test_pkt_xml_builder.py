from app.services.pkt_xml_builder import _sanitize_label


def test_sanitize_label_replaces_unsafe_device_name():
    sanitized = _sanitize_label('<script>alert(1)</script>', 'Router_1')
    assert sanitized == 'Router_1'
