"""
Lightweight validator for generated .pkt files.

What it checks (fast, no Packet Tracer needed):
 - Decryption succeeds and XML parses
 - XML_VERSION is present
 - SAVE_REF_ID values are unique and all links reference existing devices
 - MAC addresses are unique across the topology (main cause of past PT incompatibility)
 - DEV_ADDR / MEM_ADDR are unique per device
 - PHYSICALWORKSPACE contains a node for every device name

Usage:
    python tests/validate_pkt.py path/to/file.pkt [more.pkt ...]
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# Ensure repository root is on PYTHONPATH when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.pkt_crypto import decrypt_pkt_data


def load_xml(pkt_path: Path) -> ET.Element:
    raw = pkt_path.read_bytes()
    xml_bytes = decrypt_pkt_data(raw)
    return ET.fromstring(xml_bytes)


def ensure_unique(values, label: str):
    counter = Counter(values)
    dups = [v for v, c in counter.items() if c > 1]
    if dups:
        raise AssertionError(f"Duplicate {label}: {dups[:5]}")


def validate(pkt_path: Path) -> None:
    root = load_xml(pkt_path)

    # Basic version tag
    version = root.findtext("VERSION")
    if not version:
        raise AssertionError("Missing <VERSION> tag")

    devices = list(root.findall("./NETWORK/DEVICES/DEVICE"))
    if not devices:
        raise AssertionError("No devices found")

    # Unique SAVE_REF_ID
    saverefs = [d.findtext("ENGINE/SAVE_REF_ID") for d in devices]
    ensure_unique(saverefs, "SAVE_REF_ID")

    # Unique dev/mem addresses
    dev_addrs = [d.findtext("WORKSPACE/LOGICAL/DEV_ADDR") for d in devices]
    mem_addrs = [d.findtext("WORKSPACE/LOGICAL/MEM_ADDR") for d in devices]
    ensure_unique(dev_addrs, "DEV_ADDR")
    ensure_unique(mem_addrs, "MEM_ADDR")

    # Unique MAC addresses across all ports
    macs = [el.text for el in root.findall(".//MACADDRESS")]
    ensure_unique(macs, "MACADDRESS")

    # Links reference existing devices
    saveref_set = set(saverefs)
    for cable in root.findall("./NETWORK/LINKS/LINK/CABLE"):
        frm = cable.findtext("FROM")
        to = cable.findtext("TO")
        if frm not in saveref_set or to not in saveref_set:
            raise AssertionError(f"Link refs unknown devices: {frm} -> {to}")

    # PHYSICALWORKSPACE contains each device name
    pw_names = {n.findtext("NAME") for n in root.findall(".//PHYSICALWORKSPACE//NODE")}
    missing_pw = []
    for dev in devices:
        name = dev.findtext("ENGINE/NAME")
        if name and name not in pw_names:
            missing_pw.append(name)
    if missing_pw:
        raise AssertionError(f"Missing PW nodes for: {missing_pw}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python tests/validate_pkt.py file1.pkt [file2.pkt ...]", file=sys.stderr)
        return 1

    exit_code = 0
    for path_str in argv[1:]:
        pkt_path = Path(path_str)
        try:
            validate(pkt_path)
            print(f"OK   {pkt_path}")
        except Exception as exc:  # noqa: BLE001
            exit_code = 2
            print(f"FAIL {pkt_path}: {exc}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
