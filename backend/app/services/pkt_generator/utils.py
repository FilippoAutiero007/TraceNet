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
    return f"save-ref-id{n}"


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


# Legacy aliases per compatibilità durante la migrazione
_validate_name = validate_name
_safe_name = safe_name
_rand_saveref = rand_saveref
_rand_memaddr = rand_memaddr
_ensure_child = ensure_child
_set_text = set_text
