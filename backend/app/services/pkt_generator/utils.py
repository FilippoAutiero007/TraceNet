from __future__ import annotations

import json
import re
import secrets
from pathlib import Path
from typing import Any, Dict

import xml.etree.ElementTree as ET

# Regex per nomi device sicuri
_SAFE_DEVICE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_name(name: str) -> str:
    """
    Valida il nome del device per evitare caratteri strani.
    """
    if not isinstance(name, str) or not _SAFE_DEVICE_NAME.fullmatch(name):
        raise ValueError(f"Unsafe device name: {name!r}")
    return name


def safe_name(prefix: str, index: int) -> str:
    """
    Costruisce un nome sicuro del tipo 'Router0', 'PC1', ecc.
    """
    return validate_name(f"{prefix}{index}")


def rand_saveref() -> str:
    """
    Genera un ID pseudo-random per il campo SAVEREFID.
    """
    n = 10**18 + secrets.randbelow(9 * 10**18)
    return f"save-ref-id:{n}"


def rand_memaddr() -> str:
    """
    Genera un indirizzo di memoria pseudo-random usato nei link (memaddr).
    """
    return str(10**12 + secrets.randbelow(9 * 10**12))


def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    """
    Ritorna il child con il tag dato, creandolo se non esiste.
    """
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def set_text(parent: ET.Element, tag: str, value: str, *, create: bool = True) -> None:
    """
    Imposta il testo di un sotto-elemento; se non esiste lo crea (se create=True).
    """
    elem = parent.find(tag)
    if elem is None:
        if not create:
            return
        elem = ET.SubElement(parent, tag)
    elem.text = value


def load_device_templates_config(
    config_path: str | None = None,
) -> Dict[str, Any]:
    """
    Carica il JSON con le definizioni dei template dei device.
    """
    if config_path is None:
        # Default: device_catalog.json nella root del backend
        config_path = str(Path(__file__).resolve().parent.parent.parent.parent / "device_catalog.json")
    
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Device templates config not found at {path.absolute()}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
    offset = secrets.randbelow(99999) + 1000 # Ensure 5 digits
    return f"{base}-{offset:05d}"


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
    oui_prefix = secrets.choice(oui_pool)
    # Generate a pseudo-unique NIC portion while keeping values realistic.
    nic = f"{secrets.randbelow(0xFFFFFE - 0x170000) + 0x170000:06X}"  # 6 hex digits
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
