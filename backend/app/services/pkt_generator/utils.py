"""
Utility helpers for PKT generation.
Pure module with no internal dependencies.
"""
import re
import random
import secrets
import xml.etree.ElementTree as ET


# ── Validation helpers ────────────────────────────────────────────────────────

_SAFE_DEVICE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_name(name: str) -> str:
    """Validate that a device name is safe (ASCII, 1–64 chars, no spaces)."""
    if not isinstance(name, str) or not _SAFE_DEVICE_NAME.fullmatch(name):
        raise ValueError(f"Unsafe device name: {name!r}")
    return name


def safe_name(prefix: str, index: int) -> str:
    """Build and validate a device name from a prefix and an index."""
    return validate_name(f"{prefix}{index}")


# ── Random identifiers (save refs, memory addresses) ─────────────────────────

def rand_saveref() -> str:
    """Generate a random SAVE_REF_ID compatible identifier."""
    n = 10**18 + secrets.randbelow(9 * 10**18)
    return f"save-ref-id:{n}"


def rand_memaddr() -> str:
    """Generate a random decimal memory address string."""
    return str(10**12 + secrets.randbelow(9 * 10**12))


# ── XML helpers ──────────────────────────────────────────────────────────────

def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    """Return an existing child element or create it if missing."""
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def set_text(parent: ET.Element, tag: str, value: str, *, create: bool = True) -> None:
    """
    Set the text of a child element.

    If the child does not exist:
      - create=True  → create the child and set the text
      - create=False → do nothing
    """
    elem = parent.find(tag)
    if elem is None:
        if not create:
            return
        elem = ET.SubElement(parent, tag)
    elem.text = value


# ── Realistic serials for Packet Tracer devices ──────────────────────────────

def rand_realistic_serial(device_type: str) -> str:
    """
    Generate a dynamic, realistic serial number for Packet Tracer devices.

    Uses stable base prefixes per device family and a random numeric suffix.
    """
    serial_bases = {
        "router": "PTT0810K17M-730940400000",
        "switch": "PT-SWITCH-NM-1FE-730940400000",
        "pc":     "PT-PC-NM-1FE-730940400000",
        "server": "PT-SERVER-NM-1GE-730940400000",
    }
    base = serial_bases.get(device_type.lower(), "PT-GENERIC-730940400000")
    offset = random.randint(1000, 99999)
    return f"{base}-{offset:05d}"


# ── Realistic MAC addresses for Packet Tracer 8.2.2 ──────────────────────────

def rand_realistic_mac(device_type: str = "generic") -> str:
    """
    Generate a realistic MAC address (dotted Cisco format) for PT 8.2.2.

    OUI prefixes are chosen to resemble real Cisco/PT hardware families:
      - Router: 0001 / 0002
      - Switch: 0050
      - PC:     0060
      - Server: 00D0
    """
    oui_map = {
        "router": ["0001", "0002"],
        "switch": ["0050"],
        "pc":     ["0060"],
        "server": ["00D0"],
    }

    oui_pool = oui_map.get(device_type.lower(), ["0060"])  # default: PC-like
    oui_prefix = random.choice(oui_pool)

    # Generate a pseudo-unique NIC portion while keeping values realistic.
    nic = f"{random.randint(0x170000, 0xFFFFFE):06X}"  # 6 hex digits
    mac_hex = (oui_prefix + nic).upper()  # 12 hex characters
    return f"{mac_hex[0:4]}.{mac_hex[4:8]}.{mac_hex[8:12]}"


def mac_to_link_local(mac_addr: str) -> str:
    """
    Convert a MAC address (with or without separators) into an IPv6
    link-local address using the EUI-64 expansion.
    Returns empty string on parsing errors.
    """
    hex_str = "".join(ch for ch in mac_addr if ch.isalnum()).lower()
    if len(hex_str) != 12:
        return ""

    try:
        mac_bytes = bytearray.fromhex(hex_str)
    except ValueError:
        return ""

    # Flip the U/L bit
    mac_bytes[0] ^= 0x02

    # Insert FF:FE in the middle to form EUI-64
    eui = mac_bytes[:3] + b"\xff\xfe" + mac_bytes[3:]

    groups = [f"{(eui[i] << 8) | eui[i+1]:04x}" for i in range(0, 8, 2)]
    return "fe80::" + ":".join(groups)
