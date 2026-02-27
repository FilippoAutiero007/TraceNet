"""
Ripara la sezione PHYSICALWORKSPACE di un file .pkt:
- decifra il .pkt
- sostituisce il PHYSICALWORKSPACE con lo scheletro del template base
- rigenera i nodi fisici per ogni DEVICE con UUID unici e catene coerenti
- ricifra e salva in output (di default <input>.fixed.pkt)

Uso:
    python tests/repair_pw.py path/to/file.pkt [output.pkt]
"""

from __future__ import annotations

import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Ensure repo root on path (same trick as validate_pkt)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator


def repair(input_path: Path, output_path: Path) -> None:
    pkt_bytes = input_path.read_bytes()
    xml_bytes = decrypt_pkt_data(pkt_bytes)
    root = ET.fromstring(xml_bytes)

    pg = PKTGenerator()

    # Azzeriamo il PW e re-sincronizziamo con i device esistenti
    pg._reset_physical_workspace(root)  # type: ignore[attr-defined]

    devices_elem = root.find("./NETWORK/DEVICES")
    if devices_elem is None:
        raise ValueError("Missing NETWORK/DEVICES in input XML")

    # Elimina PDU esistenti e inserisce quello del template
    pg._inject_power_distribution(devices_elem)  # type: ignore[attr-defined]

    # Rigenera i nodi PW e i path PHYSICAL
    pg._sync_physical_workspace(root, devices_elem)  # type: ignore[attr-defined]

    # Ricomponi l'XML e cifra
    xml_bytes_out = (
        b'<?xml version="1.0" encoding="utf-8"?>\n'
        + ET.tostring(root, encoding="utf-8", method="xml")
    )
    output_path.write_bytes(encrypt_pkt_data(xml_bytes_out))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    in_path = Path(argv[1])
    out_path = Path(argv[2]) if len(argv) >= 3 else in_path.with_suffix(".fixed.pkt")
    repair(in_path, out_path)
    print(f"Repaired: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
