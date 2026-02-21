import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional


def node_path(root: ET.Element, target: ET.Element) -> str:
    """
    Restituisce il path gerarchico fino al NODE target, includendo NODE(NAME).
    """
    path: List[ET.Element] = []

    def dfs(node: ET.Element, cur_path: List[ET.Element]) -> bool:
        if node is target:
            path.extend(cur_path + [node])
            return True
        for child in list(node):
            if dfs(child, cur_path + [node]):
                return True
        return False

    dfs(root, [])

    parts: List[str] = []
    for n in path:
        if n.tag == "NODE":
            name = (n.findtext("NAME") or "").strip()
            parts.append(f"NODE({name})" if name else "NODE")
        else:
            parts.append(n.tag)
    return "/".join(parts)


def dump_pc_paths(path_str: str) -> None:
    """
    Stampa info e path gerarchico per tutti i NODE che rappresentano PC.
    """
    tree = ET.parse(path_str)
    root = tree.getroot()

    pw = root.find("PHYSICALWORKSPACE")
    if pw is None:
        print(f"[WARN] No PHYSICALWORKSPACE in {path_str}")
        return

    print(f"=== {Path(path_str).name} PC nodes ===")
    for node in pw.iter("NODE"):
        name = (node.findtext("NAME") or "").strip()
        if not name.startswith("PC"):
            continue

        x = (node.findtext("X") or "").strip()
        y = (node.findtext("Y") or "").strip()
        uuid = (node.findtext("UUID_STR") or "").strip()
        path_repr = node_path(root, node)

        print(
            f"name={name}, X={x}, Y={y}, UUID={uuid}, PATH={path_repr}"
        )


def main(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print(f"Usage: {Path(sys.argv[0]).name} file1.xml [file2.xml ...]")
        return 1

    for f in argv:
        dump_pc_paths(f)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
