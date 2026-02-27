"""Physical workspace synchronisation helpers (legacy generator path)."""
from __future__ import annotations

import copy
import logging
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PhysicalWorkspaceSync:
    """
    Extracts prototype data from the base template and aligns PHYSICALWORKSPACE
    with generated devices.
    """

    def __init__(self, default_template_root: Optional[ET.Element]) -> None:
        self._base_physical_paths = self._extract_base_physical_paths(default_template_root)
        self._base_pw_nodes = self._extract_base_pw_nodes(default_template_root)
        self._pc_parent_proto = self._extract_pc_parent_node(default_template_root)

    # ------------------------ public API ------------------------

    def sync(self, root: ET.Element, devices_elem: ET.Element) -> None:
        """
        Allinea ogni device (WORKSPACE/PHYSICAL) con il PHYSICALWORKSPACE globale.
        Replica il comportamento precedente, ma in modo isolato.
        """
        if not self._base_physical_paths:
            return

        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return

        def find_pc_parent(node: ET.Element) -> Optional[ET.Element]:
            for child in list(node):
                if child.tag == "NODE":
                    name = child.findtext("NAME")
                    if name and name.strip() == "PC0":
                        return node
                found = find_pc_parent(child)
                if found is not None:
                    return found
            return None

        rack_node: Optional[ET.Element] = None
        for node in pw.iter("NODE"):
            name = (node.findtext("NAME") or "").strip()
            if name == "Rack":
                rack_node = node
                break

        pc_parent_node = find_pc_parent(pw)

        pw_nodes: Dict[str, ET.Element] = {}
        for node in pw.iter("NODE"):
            name = (node.findtext("NAME") or "").strip()
            if name:
                pw_nodes[name] = node

        for dev in devices_elem:
            name_elem = dev.find("ENGINE/NAME")
            type_elem = dev.find("ENGINE/TYPE")
            phys_elem = dev.find("WORKSPACE/PHYSICAL")
            if name_elem is None or type_elem is None or phys_elem is None:
                continue

            dname = name_elem.text or ""
            dtype = (type_elem.text or "").lower()
            if not dname:
                continue

            if "pc" in dtype or "server" in dtype:
                base_key = "pc"
            elif "switch" in dtype:
                base_key = "switch"
            elif "router" in dtype:
                base_key = "router"
            else:
                continue
            logger.info("SYNC_PW device %s type %s base_key %s", dname, dtype, base_key)

            base_path = self._base_physical_paths.get(base_key, [])
            if not base_path:
                continue

            new_guid = str(uuid.uuid4())
            new_path = base_path[:-1] + [new_guid]
            phys_elem.text = ",".join(f"{{{p}}}" for p in new_path)

            pw_node = pw_nodes.get(dname)
            if pw_node is None:
                proto = self._base_pw_nodes.get(base_key)
                if proto is not None:
                    pw_node = copy.deepcopy(proto)

                    name_field = pw_node.find("NAME")
                    if name_field is not None:
                        name_field.text = dname

                    if base_key == "pc" and pc_parent_node is not None:
                        parent_node = pc_parent_node
                    else:
                        parent_node = rack_node

                    if parent_node is not None:
                        if parent_node.tag == "CHILDREN":
                            siblings = parent_node
                        else:
                            siblings = parent_node.find("CHILDREN")
                            if siblings is None:
                                siblings = ET.SubElement(parent_node, "CHILDREN")

                        existing_named = [
                            n for n in siblings.findall("NODE")
                            if (n.findtext("NAME") or "").strip()
                            and (n.findtext("NAME") or "").lower().startswith(base_key)
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

    # ----------------------- extraction helpers -----------------

    def _extract_base_physical_paths(self, root: Optional[ET.Element]) -> Dict[str, List[str]]:
        paths: Dict[str, List[str]] = {}
        if root is None:
            return paths

        devices_node = root.find("NETWORK/DEVICES")
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
                if "pc" in raw_type or "server" in raw_type else
                "switch"
                if "switch" in raw_type else
                "router"
                if "router" in raw_type else
                None
            )
            if key is None:
                continue

            path_parts = [p.strip("{} ") for p in phys_elem.text.split(",") if p.strip()]
            paths[key] = path_parts

        return paths

    def _extract_base_pw_nodes(self, root: Optional[ET.Element]) -> Dict[str, ET.Element]:
        nodes: Dict[str, ET.Element] = {}
        if root is None:
            return nodes

        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return nodes

        for node in pw.iter("NODE"):
            name_elem = node.find("NAME")
            if name_elem is None or name_elem.text is None:
                continue
            raw = name_elem.text.lower()
            key = (
                "router"
                if "router0" in raw else
                "switch"
                if "switch0" in raw else
                "pc"
                if "pc0" in raw else
                None
            )
            if key and key not in nodes:
                nodes[key] = copy.deepcopy(node)

        return nodes

    def _extract_pc_parent_node(self, root: Optional[ET.Element]) -> Optional[ET.Element]:
        if root is None:
            return None

        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return None

        def find_parent_of_pc0(parent: ET.Element) -> Optional[ET.Element]:
            for child in list(parent):
                if child.tag == "NODE":
                    name = child.findtext("NAME")
                    if name and name.strip() == "PC0":
                        return parent
                found = find_parent_of_pc0(child)
                if found is not None:
                    return found
            return None

        return find_parent_of_pc0(pw)
