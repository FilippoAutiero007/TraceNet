import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable


def iter_rack_nodes(root: ET.Element) -> Iterable[ET.Element]:
    """Yield all NODE children under PHYSICALWORKSPACE → Rack → CHILDREN."""
    pw = root.find("PHYSICALWORKSPACE")
    if pw is None:
        raise RuntimeError("No PHYSICALWORKSPACE node found")

    rack = None
    for node in pw.iter("NODE"):
        name = (node.findtext("NAME") or "").strip()
        if name == "Rack":
            rack = node
            break
    if rack is None:
        raise RuntimeError("No Rack node found")

    children = rack.find("CHILDREN")
    if children is None:
        return []
    return children.findall("NODE")


def dump_rack_nodes(path: Path) -> None:
    """Print Rack/CHILDREN/NODE entries from a PKT XML or similar file."""
    tree = ET.parse(path)
    root = tree.getroot()

    nodes = list(iter_rack_nodes(root))
    print(f"=== {path} Rack/CHILDREN/NODE ({len(nodes)} nodes) ===")
    for i, node in enumerate(nodes):
        name = (node.findtext("NAME") or "").strip()
        x = (node.findtext("X") or "").strip()
        y = (node.findtext("Y") or "").strip()
        uuid = (node.findtext("UUID_STR") or "").strip()
        type_ = (node.findtext("TYPE") or "").strip()
        slot = (node.findtext("SLOT") or "").strip()
        subslot = (node.findtext("SUBSLOT") or "").strip()

        print(
            f"{i:02d}: "
            f"name={name!r}, "
            f"X={x}, Y={y}, "
            f"TYPE={type_}, SLOT={slot}, SUBSLOT={subslot}, "
            f"UUID={uuid}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dump Rack/CHILDREN/NODE info from PKT XML files."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="XML/PKT files to inspect",
    )
    args = parser.parse_args(argv)

    for fname in args.files:
        path = Path(fname)
        if not path.exists():
            print(f"[WARN] File not found: {path}", file=sys.stderr)
            continue
        try:
            dump_rack_nodes(path)
        except Exception as e:
            print(f"[ERROR] Failed on {path}: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
