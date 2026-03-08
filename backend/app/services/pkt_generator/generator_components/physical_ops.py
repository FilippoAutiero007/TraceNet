from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from typing import Any, Optional


class PhysicalWorkspaceOps:
    def __init__(self, template_root: ET.Element):
        self.template_root = template_root
        self._base_physical_paths: dict[str, list[str]] | None = None
        self._base_pw_nodes: dict[str, ET.Element] | None = None
        self._pc_parent_node: Optional[ET.Element] = None

    def cleanup(self, root: ET.Element) -> None:
        # Keep the template Physical Workspace intact. Device-level reconciliation
        # is handled by sync() to avoid destructive resets that can corrupt PT files.
        _ = root

    def _extract_base_physical_paths(self) -> dict[str, list[str]]:
        paths: dict[str, list[str]] = {}
        devices_node = self.template_root.find("NETWORK/DEVICES")
        if devices_node is None:
            return paths
        for dev in devices_node:
            type_elem = dev.find("ENGINE/TYPE")
            phys_elem = dev.find("WORKSPACE/PHYSICAL")
            if phys_elem is None or phys_elem.text is None:
                continue
            raw_type = (type_elem.text if type_elem is not None else "").lower()
            key = (
                "pc"
                if "pc" in raw_type or "server" in raw_type
                else "switch"
                if "switch" in raw_type
                else "router"
                if "router" in raw_type
                else None
            )
            if key is None:
                continue
            paths[key] = [part.strip("{} ") for part in phys_elem.text.split(",") if part.strip()]
        if "_fallback" not in paths and paths:
            first_path = next(iter(paths.values()))
            paths["_fallback"] = first_path
        return paths

    def _extract_base_pw_nodes(self) -> dict[str, ET.Element]:
        nodes: dict[str, ET.Element] = {}
        pw = self.template_root.find("PHYSICALWORKSPACE")
        if pw is None:
            return nodes
        for node in pw.iter("NODE"):
            name = (node.findtext("NAME") or "").lower()
            key = (
                "router"
                if "router0" in name
                else "switch"
                if "switch0" in name
                else "pc"
                if "pc0" in name
                else None
            )
            if key and key not in nodes:
                nodes[key] = copy.deepcopy(node)
        return nodes

    def _extract_pc_parent_node(self) -> Optional[ET.Element]:
        pw = self.template_root.find("PHYSICALWORKSPACE")
        if pw is None:
            return None

        def find_parent_of_pc0(parent: ET.Element) -> Optional[ET.Element]:
            for child in list(parent):
                if child.tag == "NODE" and (child.findtext("NAME") or "").strip() == "PC0":
                    return parent
                found = find_parent_of_pc0(child)
                if found is not None:
                    return found
            return None

        return find_parent_of_pc0(pw)

    def _ensure_cache(self) -> None:
        if self._base_physical_paths is None:
            self._base_physical_paths = self._extract_base_physical_paths()
        if self._base_pw_nodes is None:
            self._base_pw_nodes = self._extract_base_pw_nodes()
        if self._pc_parent_node is None:
            self._pc_parent_node = self._extract_pc_parent_node()

    @staticmethod
    def _extract_uuid_path_from_node(pw_root: ET.Element, leaf_node: ET.Element) -> list[str]:
        parent_map = {child: parent for parent in pw_root.iter() for child in parent}
        path: list[str] = []
        current: Optional[ET.Element] = leaf_node
        while current is not None:
            if current.tag == "NODE":
                uuid_text = (current.findtext("UUID_STR") or "").strip().strip("{}")
                if uuid_text:
                    path.append(uuid_text)
            current = parent_map.get(current)
        path.reverse()
        return path

    def sync(
        self,
        root: ET.Element,
        devices_elem: ET.Element,
        device_physical_hints: Optional[dict[str, dict[str, Any]]] = None,
    ) -> None:
        hints = device_physical_hints or {}

        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return

        # Build an index of existing PW nodes by UUID to avoid duplicates.
        uuid_index: dict[str, ET.Element] = {}
        for node in pw.iter("NODE"):
            uuid_text = (node.findtext("UUID_STR") or "").strip().strip("{}")
            if uuid_text:
                uuid_index[uuid_text] = node

        def parse_path(text: str | None) -> list[str]:
            if not text:
                return []
            return [part.strip("{} ") for part in text.split(",") if part.strip()]

        for dev in devices_elem:
            dname = dev.findtext("ENGINE/NAME") or ""
            if not dname:
                continue

            phys_elem = dev.findtext("WORKSPACE/PHYSICAL") or ""
            hint = hints.get(dname, {})
            path_parts = hint.get("path_parts") or parse_path(phys_elem)
            if not path_parts:
                continue

            proto_node = hint.get("proto_node")

            parent_node: Optional[ET.Element] = None
            for idx, part in enumerate(path_parts):
                node = uuid_index.get(part)
                if node is None:
                    if idx == len(path_parts) - 1 and proto_node is not None:
                        node = copy.deepcopy(proto_node)
                        name_elem = node.find("NAME") or ET.SubElement(node, "NAME")
                        name_elem.text = dname
                        uuid_elem = node.find("UUID_STR") or ET.SubElement(node, "UUID_STR")
                        uuid_elem.text = f"{{{part}}}"
                    else:
                        node = ET.Element("NODE")
                        uuid_elem = ET.SubElement(node, "UUID_STR")
                        uuid_elem.text = f"{{{part}}}"
                    if parent_node is None:
                        pw.append(node)
                    else:
                        children = parent_node.find("CHILDREN")
                        if children is None:
                            children = ET.SubElement(parent_node, "CHILDREN")
                        children.append(node)
                    uuid_index[part] = node
                parent_node = node
