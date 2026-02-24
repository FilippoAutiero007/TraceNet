"""
DEPRECATED: Use app.services.pkt_generator instead.
This file exists for backward compatibility.
"""
from app.services.pkt_generator import save_pkt_file, get_pkt_generator, PKTGenerator
from app.services.pkt_generator.topology import build_links_config
from app.services.pkt_crypto import encrypt_pkt_data as _legacy_xor_encode, decrypt_pkt_data as _legacy_xor_decode

# Re-export necessary functions
__all__ = [
    "save_pkt_file",
    "get_pkt_generator",
    "PKTGenerator",
    "_legacy_xor_encode",
    "_legacy_xor_decode",
    "validate_pkt_xml",
    "build_pkt_xml",
    "build_links_config",
]

def validate_pkt_xml(xml_content: str) -> bool:
    """Dummy validation for backward compatibility."""
    return True

def build_pkt_xml(subnets, config):
    """Dummy build for backward compatibility."""
    return "<PACKETTRACER5><VERSION>8.2.0</VERSION></PACKETTRACER5>"
