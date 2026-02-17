"""PKT Generator package - public API."""
from .topology import save_pkt_file
from .core import get_pkt_generator, PKTGenerator

def generate_cisco_config(*args, **kwargs):
    """Stub for backward compatibility - deprecated."""
    raise NotImplementedError("Use save_pkt_file directly")

__all__ = ["save_pkt_file", "get_pkt_generator", "PKTGenerator", "generate_cisco_config"]
