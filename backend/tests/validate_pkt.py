"""
Lightweight validator for generated .pkt files.

Obiettivo: bloccare solo gli errori strutturali che possono rendere il file
incompatibile con Packet Tracer, senza essere più rigidi di lui.

Controlli eseguiti (veloci, senza aprire PT):
 - Il .pkt si decifra e l'XML interno è valido
 - Esiste il tag <VERSION> (non controlliamo il valore)
 - SAVE_REF_ID sono univoci
 - Nessun NAME di dispositivo è associato a più SAVE_REF_ID
 - DEV_ADDR / MEM_ADDR sono univoci tra i dispositivi (ignorando i mancanti)
 - Ogni dispositivo con SAVE_REF_ID ha anche DEV_ADDR e MEM_ADDR
 - Le MAC address non sono duplicate (formato lasciato a PT)
 - Esiste almeno un LINK
 - Ogni LINK punta a dispositivi esistenti
 - PHYSICALWORKSPACE ha un nodo per ogni DEVICE (niente device “fantasma”)

Uso:
    python tests/validate_pkt.py path/to/file.pkt [more.pkt ...]
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Iterable

# Ensure repository root is on PYTHONPATH when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.pkt_crypto import decrypt_pkt_data


def load_xml(pkt_path: Path) -> ET.Element:
    """Legge un .pkt, lo decifra e parse l'XML interno."""
    raw = pkt_path.read_bytes()
    xml_bytes = decrypt_pkt_data(raw)
    return ET.fromstring(xml_bytes)


def ensure_unique(values: Iterable[str | None], label: str) -> None:
    """Verifica che non ci siano duplicati, ignorando None/stringhe vuote."""
    valid_values = [v for v in values if v]
    counter = Counter(valid_values)
    dups = [v for v, c in counter.items() if c > 1]
    if dups:
        raise AssertionError(f"Duplicate {label}: {dups[:5]}")


def normalize_mac(mac: str) -> str:
    """Normalizza una MAC: rimuove separatori, porta a maiuscole."""
    cleaned = "".join(c for c in mac if c.isalnum()).upper()
    return cleaned


def validate_macs(macs: list[str | None]) -> None:
    """
    Valida solo l'unicità delle MAC address.

    Il formato esatto viene lasciato a Packet Tracer:
    qui normalizziamo (rimozione separatori, maiuscole) e
    controlliamo che non ci siano duplicati.
    """
    normalized: list[str] = []

    for m in macs:
        if not m:
            continue

        m = m.strip()
        if not m:
            continue

        norm = normalize_mac(m)
        normalized.append(norm)

    ensure_unique(normalized, "MACADDRESS")


def validate(pkt_path: Path) -> None:
    """Esegue tutti i controlli strutturali su un singolo .pkt."""
    try:
        root = load_xml(pkt_path)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"Failed to decrypt/parse XML for {pkt_path}: {exc}") from exc

    # VERSION tag (solo presenza, non il valore)
    version = root.findtext("VERSION")
    if not version:
        raise AssertionError(f"Missing <VERSION> tag in {pkt_path}")

    # Devices
    devices = list(root.findall("./NETWORK/DEVICES/DEVICE"))
    if not devices:
        raise AssertionError(f"No devices found in {pkt_path}")

    # Unique SAVE_REF_ID
    saverefs = [d.findtext("ENGINE/SAVE_REF_ID") for d in devices]
    ensure_unique(saverefs, "SAVE_REF_ID")

    # Extra safety: NAME non deve mappare a ref diversi
    name_to_ref: dict[str, str] = {}
    for dev in devices:
        name = dev.findtext("ENGINE/NAME")
        ref = dev.findtext("ENGINE/SAVE_REF_ID")
        if not name or not ref:
            continue
        prev = name_to_ref.get(name)
        if prev is None:
            name_to_ref[name] = ref
        elif prev != ref:
            raise AssertionError(
                f"Device name {name!r} mapped to multiple SAVE_REF_ID in {pkt_path}: "
                f"{prev!r}, {ref!r}"
            )

    # Unique DEV/MEM addresses
    dev_addrs = [d.findtext("WORKSPACE/LOGICAL/DEV_ADDR") for d in devices]
    mem_addrs = [d.findtext("WORKSPACE/LOGICAL/MEM_ADDR") for d in devices]
    ensure_unique(dev_addrs, "DEV_ADDR")
    ensure_unique(mem_addrs, "MEM_ADDR")

    # Devices con SAVE_REF_ID devono avere DEV_ADDR e MEM_ADDR
    for dev in devices:
        ref = dev.findtext("ENGINE/SAVE_REF_ID")
        dev_addr = dev.findtext("WORKSPACE/LOGICAL/DEV_ADDR")
        mem_addr = dev.findtext("WORKSPACE/LOGICAL/MEM_ADDR")
        if ref and (not dev_addr or not mem_addr):
            raise AssertionError(f"Device {ref} missing DEV_ADDR or MEM_ADDR in {pkt_path}")

    # MAC: solo unicità
    macs = [el.text for el in root.findall(".//MACADDRESS")]
    validate_macs(macs)

    # Links: devono esistere e puntare a device validi
    links = list(root.findall("./NETWORK/LINKS/LINK"))
    if not links:
        raise AssertionError(f"No links found in {pkt_path} (topology has zero cables?)")

    saveref_set = {v for v in saverefs if v}
    for cable in root.findall("./NETWORK/LINKS/LINK/CABLE"):
        frm = cable.findtext("FROM")
        to = cable.findtext("TO")

        # Struttura del cavo
        if not frm or not to:
            raise AssertionError(f"Malformed link found in {pkt_path}: FROM={frm}, TO={to}")

        if frm not in saveref_set or to not in saveref_set:
            raise AssertionError(f"Link refs unknown devices in {pkt_path}: {frm} -> {to}")

    # PHYSICALWORKSPACE: nodi devono coprire tutti i device (ma ignoriamo nodi extra tipo "Home City")
    pw_nodes = list(root.findall(".//PHYSICALWORKSPACE//NODE"))

    pw_names: set[str] = set()
    for n in pw_nodes:
        name = n.findtext("NAME")
        if name:
            pw_names.add(name)

    device_names: set[str] = set()
    for d in devices:
        name = d.findtext("ENGINE/NAME")
        if name:
            device_names.add(name)

    # Ogni DEVICE deve avere un nodo PW
    missing_pw = [name for name in device_names if name not in pw_names]
    if missing_pw:
        raise AssertionError(f"Missing PW nodes in {pkt_path} for: {missing_pw}")

    # PHYSICALWORKSPACE integrity: UUID univoci e catena PHYSICAL -> nodi esistenti e figli
    uuid_nodes = {
        (n.findtext("UUID_STR") or "").strip("{}"): n
        for n in pw_nodes
        if n.findtext("UUID_STR")
    }
    if len(uuid_nodes) != len(
        [n for n in pw_nodes if n.findtext("UUID_STR")]
    ):
        raise AssertionError(f"Duplicate UUID_STR in PHYSICALWORKSPACE of {pkt_path}")

    for dev in devices:
        name = dev.findtext("ENGINE/NAME") or ""
        phys = dev.findtext("WORKSPACE/PHYSICAL") or ""
        chain = [p.strip("{} ") for p in phys.split(",") if p.strip()]
        if not chain:
            raise AssertionError(f"Device {name} has empty PHYSICAL path in {pkt_path}")

        parent_node = None
        for idx, uuid in enumerate(chain):
            node = uuid_nodes.get(uuid)
            if node is None:
                raise AssertionError(
                    f"Device {name} references unknown PW UUID {uuid} (index {idx}) in {pkt_path}"
                )
            if parent_node is not None:
                children = parent_node.find("CHILDREN")
                if children is None or node not in list(children.findall("NODE")):
                    raise AssertionError(
                        f"Device {name} PW chain broken at {uuid} (index {idx}) in {pkt_path}"
                    )
            parent_node = node

        leaf = uuid_nodes[chain[-1]]
        leaf_name = (leaf.findtext("NAME") or "").strip()
        if leaf_name != name:
            raise AssertionError(
                f"Device {name} PW leaf name mismatch: found {leaf_name!r} in {pkt_path}"
            )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python tests/validate_pkt.py file1.pkt [file2.pkt ...]", file=sys.stderr)
        return 1

    exit_code = 0
    for path_str in argv[1:]:
        pkt_path = Path(path_str)
        if not pkt_path.is_file():
            exit_code = 1
            print(f"FAIL {pkt_path}: file not found", file=sys.stderr)
            continue

        try:
            validate(pkt_path)
            print(f"OK   {pkt_path}")
        except Exception as exc:  # noqa: BLE001
            exit_code = 2
            print(f"FAIL {pkt_path}: {exc}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
