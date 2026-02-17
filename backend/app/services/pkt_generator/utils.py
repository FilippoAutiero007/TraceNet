"""
Utility helpers for PKT generation.
Pure module with no internal dependencies.
"""
import re
import secrets
import xml.etree.ElementTree as ET

_SAFE_DEVICE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_name(name: str) -> str:
    """Ensure device name is safe and valid."""
    if not isinstance(name, str) or not _SAFE_DEVICE_NAME.fullmatch(name):
        raise ValueError(f"Unsafe device name: {name!r}")
    return name


def safe_name(prefix: str, index: int) -> str:
    """Generate a safe name from prefix and index."""
    return validate_name(f"{prefix}{index}")


def rand_saveref() -> str:
    """Generate a random save reference ID."""
    n = 10**18 + secrets.randbelow(9 * 10**18)
    return f"save-ref-id{n}"


def rand_memaddr() -> str:
    """Generate a random memory address string."""
    return str(10**12 + secrets.randbelow(9 * 10**12))


def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    """Find or create a child element."""
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def set_text(parent: ET.Element, tag: str, value: str, *, create: bool = True) -> None:
    """Set text content of a child element, optionally creating it."""
    elem = parent.find(tag)
    if elem is None:
        if not create:
            return
        elem = ET.SubElement(parent, tag)
    elem.text = value
