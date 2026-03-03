from __future__ import annotations

import copy
import uuid
import xml.etree.ElementTree as ET
from typing import Any, Optional


class PhysicalWorkspaceOps:
    def __init__(self, template_root: ET.Element):
        self.template_root = template_root
        self._base_physical_paths: dict[str, list[str]] | None = None
        self._base_pw_nodes: dict[str, ET.Element] | None = None
        self._pc_parent_node: Optional[ET.Element] = None

    def cleanup(self, root: ET.Element) -> None:
        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return

        def remove_device_nodes(parent: ET.Element) -> None:
            to_remove = []
            for node in parent.findall("NODE"):
                ntype = node.find("TYPE")
                if ntype is not None and ntype.text == "6":
                    to_remove.append(node)
            for node in to_remove:
                parent.remove(node)
            for node in parent.findall("NODE"):
                children_node = node.find("CHILDREN")
                if children_node is not None:
                    remove_device_nodes(children_node)

        remove_device_nodes(pw)

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

    def sync(
        self,
        root: ET.Element,
        devices_elem: ET.Element,
        device_physical_hints: Optional[dict[str, dict[str, Any]]] = None,
    ) -> None:
        self._ensure_cache()
        if not self._base_physical_paths:
            return
        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return

        rack_node: Optional[ET.Element] = None
        for node in pw.iter("NODE"):
            if (node.findtext("NAME") or "").strip() == "Rack":
                rack_node = node
                break

        def find_pc_parent(node: ET.Element) -> Optional[ET.Element]:
            for child in list(node):
                if child.tag == "NODE" and (child.findtext("NAME") or "").strip() == "PC0":
                    return node
                found = find_pc_parent(child)
                if found is not None:
                    return found
            return None

        pc_parent_node = find_pc_parent(pw) or self._pc_parent_node

        pw_nodes: dict[str, ET.Element] = {}
        uuid_nodes: dict[str, ET.Element] = {}
        for node in pw.iter("NODE"):
            name = (node.findtext("NAME") or "").strip()
            if name:
                pw_nodes[name] = node
            uuid_text = node.findtext("UUID_STR")
            if uuid_text:
                uuid_nodes[uuid_text.strip("{}")] = node

        for dev in devices_elem:
            dname = dev.findtext("ENGINE/NAME") or ""
            dtype = (dev.findtext("ENGINE/TYPE") or "").lower()
            phys_elem = dev.find("WORKSPACE/PHYSICAL")
            if not dname or phys_elem is None:
                continue
            hint = (device_physical_hints or {}).get(dname, {})

            if "pc" in dtype or "server" in dtype:
                base_key = "pc"
            elif "switch" in dtype:
                base_key = "switch"
            elif "router" in dtype:
                base_key = "router"
            else:
                continue

            hinted_path = hint.get("path_parts") or []
            use_hinted_path = bool(hinted_path) and all(part in uuid_nodes for part in hinted_path[:-1])
            base_path = hinted_path if use_hinted_path else self._base_physical_paths.get(base_key, [])
            if not base_path:
                continue

            parent_node = uuid_nodes.get(base_path[-2]) if len(base_path) >= 2 else None
            if parent_node is None:
                parent_node = pc_parent_node if base_key == "pc" else rack_node

            new_guid = str(uuid.uuid4())
            phys_elem.text = ",".join(f"{{{part}}}" for part in (base_path[:-1] + [new_guid]))

            pw_node = pw_nodes.get(dname)
            if pw_node is None:
                proto = hint.get("proto_node")
                if proto is None and self._base_pw_nodes:
                    proto = self._base_pw_nodes.get(base_key)
                if proto is not None:
                    pw_node = copy.deepcopy(proto)
                    name_field = pw_node.find("NAME")
                    if name_field is not None:
                        name_field.text = dname
                    if parent_node is not None:
                        siblings = parent_node if parent_node.tag == "CHILDREN" else parent_node.find("CHILDREN")
                        if siblings is None:
                            siblings = ET.SubElement(parent_node, "CHILDREN")
                        existing_named = [
                            node
                            for node in siblings.findall("NODE")
                            if (node.findtext("NAME") or "").strip()
                            and (node.findtext("NAME") or "").lower().startswith(base_key)
                        ]
                        base_x = float(pw_node.findtext("X", default="0"))
                        step_x = 86.0 if base_key == "pc" else 120.0
                        x_elem = pw_node.find("X")
                        if x_elem is not None:
                            x_elem.text = str(base_x + step_x * len(existing_named))
                        siblings.append(pw_node)
                        pw_nodes[dname] = pw_node

            if pw_node is not None:
                uuid_elem = pw_node.find("UUID_STR")
                if uuid_elem is None:
                    uuid_elem = ET.SubElement(pw_node, "UUID_STR")
                uuid_elem.text = f"{{{new_guid}}}"
