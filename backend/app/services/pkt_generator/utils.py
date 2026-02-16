# backend/app/services/pkt_generator/utils.py
from __future__ import annotations

import re
import secrets
from typing import Any
import xml.etree.ElementTree as ET

_SAFE_DEVICE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not _SAFE_DEVICE_NAME.fullmatch(name):
        raise ValueError(f"Unsafe device name: {name!r}")
    return name


def safe_name(prefix: str, index: int) -> str:
    return validate_name(f"{prefix}{index}")


def rand_saveref() -> str:
    n = 10**18 + secrets.randbelow(9 * 10**18)
    return f"save-ref-id{n}"


def rand_memaddr() -> str:
    return str(10**12 + secrets.randbelow(9 * 10**12))


def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def set_text(parent: ET.Element, tag: str, value: str, *, create: bool = True) -> None:
    elem = parent.find(tag)
    if elem is None:
        if not create:
            return
        elem = ET.SubElement(parent, tag)
    elem.text = value


# Legacy aliases for compatibility during migration
_validate_name = validate_name
_safe_name = safe_name
_rand_saveref = rand_saveref
_rand_memaddr = rand_memaddr
_ensure_child = ensure_child
_set_text = set_text
