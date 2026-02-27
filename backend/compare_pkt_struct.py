"""
Structural diff between two Packet Tracer XML files focused on devices,
their SAVE_REF_ID/SAVEREFID and the FROM/TO endpoints that reference them.
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Tuple


def _load_devices(root: ET.Element) -> Dict[str, dict]:
    devices: Dict[str, dict] = {}
    for dev in root.findall(".//DEVICE"):
        name = (dev.findtext("ENGINE/NAME") or "").strip()
        if not name:
            continue
        engine = dev.find("ENGINE")
        dtype = (dev.findtext("ENGINE/TYPE") or "").strip()
        model = (dev.findtext("ENGINE/MODEL") or "").strip()
        custom_model = (dev.findtext("ENGINE/CUSTOMMODEL") or "").strip()

        saverefs: List[str] = []
        for tag in ("SAVEREFID", "SAVE_REF_ID"):
            val = dev.findtext(f"ENGINE/{tag}")
            if val:
                saverefs.append(val.strip())

        devices[name] = {
            "type": dtype,
            "model": model,
            "custom_model": custom_model,
            "saverefs": saverefs,
        }
    return devices


def _build_ref_index(devices: Dict[str, dict]) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for name, meta in devices.items():
        for ref in meta.get("saverefs", []):
            idx[ref] = name
    return idx


def _collect_links(root: ET.Element, ref_index: Dict[str, str]) -> Dict[str, List[str]]:
    per_dev: Dict[str, List[str]] = defaultdict(list)
    for cable in root.findall(".//LINK/CABLE"):
        ports = [p.text or "" for p in cable.findall("PORT")]
        from_ref = (cable.findtext("FROM") or "").strip()
        to_ref = (cable.findtext("TO") or "").strip()

        def push(role: str, ref: str, port: str) -> None:
            dev = ref_index.get(ref, f"?ref:{ref}")
            per_dev[dev].append(f"{role}->{ref} on {port or '?port'}")

        push("from", from_ref, ports[0] if ports else "")
        push("to", to_ref, ports[1] if len(ports) > 1 else (ports[0] if ports else ""))
    return per_dev


def _print_device(name: str, left: dict | None, right: dict | None,
                  links_left: Dict[str, List[str]], links_right: Dict[str, List[str]]) -> None:
    print(f"=== {name} ===")

    def fmt(meta: dict | None) -> str:
        if meta is None:
            return "<missing>"
        return (
            f"TYPE={meta['type'] or '-'} "
            f"MODEL={meta['model'] or '-'} "
            f"CUSTOMMODEL={meta['custom_model'] or '-'} "
            f"SAVEREF={', '.join(meta['saverefs']) or '-'}"
        )

    print(f" manual   : {fmt(left)}")
    print(f" generated: {fmt(right)}")

    l_links = links_left.get(name, [])
    r_links = links_right.get(name, [])
    print(f" manual links   ({len(l_links)}): {l_links or '-'}")
    print(f" generated links({len(r_links)}): {r_links or '-'}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Structural diff for PKT XML device/link refs.")
    parser.add_argument("manual_xml", nargs="?", default="manual_1r2s4p.xml",
                        help="Reference XML that opens correctly in Packet Tracer.")
    parser.add_argument("generated_xml", nargs="?", default="testko_from_pkt.xml",
                        help="XML produced by the generator to compare.")
    args = parser.parse_args()

    left_root = ET.parse(args.manual_xml).getroot()
    right_root = ET.parse(args.generated_xml).getroot()

    left_devices = _load_devices(left_root)
    right_devices = _load_devices(right_root)

    left_idx = _build_ref_index(left_devices)
    right_idx = _build_ref_index(right_devices)

    left_links = _collect_links(left_root, left_idx)
    right_links = _collect_links(right_root, right_idx)

    all_names = sorted(set(left_devices) | set(right_devices))
    for name in all_names:
        _print_device(
            name,
            left_devices.get(name),
            right_devices.get(name),
            left_links,
            right_links,
        )


if __name__ == "__main__":
    main()
