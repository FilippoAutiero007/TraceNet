import os
import pytest
import xml.etree.ElementTree as ET
from app.services.pkt_file_generator import (
    _legacy_xor_encode,
    _legacy_xor_decode,
    build_pkt_xml,
    validate_pkt_xml,
    save_pkt_file
)

# Mock classes for testing logic
class MockSubnet:
    def __init__(self, gateway, mask, hosts):
        self.gateway = gateway
        self.mask = mask
        self.hosts_count = len(hosts)
        self.hosts = hosts

def test_legacy_xor_roundtrip():
    """Verify that legacy encoding followed by decoding returns original content"""
    original_xml = '<PACKETTRACER5><VERSION>8.2.0</VERSION></PACKETTRACER5>'
    
    # Encode
    encoded = _legacy_xor_encode(original_xml)
    
    # Decode
    decoded = _legacy_xor_decode(encoded)
    
    assert decoded == original_xml
    assert len(encoded) > 0

def test_xml_structure_builder():
    """Verify that build_pkt_xml produces expected tags"""
    subnets = [MockSubnet("192.168.1.1", "255.255.255.0", ["192.168.1.2"])]
    config = {}
    
    xml_out = build_pkt_xml(subnets, config)
    
    assert "<PACKETTRACER5>" in xml_out
    assert "<VERSION>" in xml_out
    assert "<DEVICES>" in xml_out
    assert "<LINKS>" in xml_out
    # Check if devices are created
    assert 'name="R1"' in xml_out
    assert 'name="S1"' in xml_out
    assert 'name="PC1_1"' in xml_out

def test_validate_pkt_xml_valid():
    """Verify validation passes for good XML"""
    valid_xml = '''
    <PACKETTRACER5>
        <NETWORK>
            <DEVICES>
                <DEVICE name="R1" id="R1">
                    <INTERFACE name="Fa0/0" />
                </DEVICE>
                <DEVICE name="S1" id="S1">
                    <INTERFACE name="Fa0/1" />
                </DEVICE>
            </DEVICES>
            <LINKS>
                <LINK from="R1" to="S1" from_port="Fa0/0" to_port="Fa0/1" />
            </LINKS>
        </NETWORK>
    </PACKETTRACER5>
    '''
    # Should not raise exception
    validate_pkt_xml(valid_xml)

def test_validate_pkt_xml_invalid_link():
    """Verify validation fails for missing device in link"""
    invalid_xml = '''
    <PACKETTRACER5>
        <NETWORK>
            <DEVICES>
                <DEVICE name="R1" />
            </DEVICES>
            <LINKS>
                <LINK from="R1" to="GHOST_DEVICE" />
            </LINKS>
        </NETWORK>
    </PACKETTRACER5>
    '''
    with pytest.raises(ValueError) as excinfo:
        validate_pkt_xml(invalid_xml)
    assert "Link destination device 'GHOST_DEVICE' does not exist" in str(excinfo.value)
