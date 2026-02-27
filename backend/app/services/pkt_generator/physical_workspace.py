"""
Gestione del PHYSICALWORKSPACE per la generazione di file PKT.

Questo modulo incapsula la logica per la manipolazione del workspace fisico,
inclusa la pulizia, la sincronizzazione e la gestione dei nodi fisici
che rappresentano i device.
"""
from __future__ import annotations

import copy
import logging
import uuid
from typing import Any, Optional
import xml.etree.ElementTree as ET

from .utils import set_text

logger = logging.getLogger(__name__)


class PhysicalWorkspaceManager:
    """
    Gestisce il PHYSICALWORKSPACE di un file PKT.
    """

    def __init__(self, template_root: ET.Element):
        self._template_root = template_root
        self._base_physical_paths = self._extract_base_physical_paths()
        self._base_pw_nodes = self._extract_base_pw_nodes()
        self._pc_parent_node = self._extract_pc_parent_node()
        self._pw_skeleton = self._build_pw_skeleton()

    def _extract_base_physical_paths(self) -> dict[str, list[str]]:
        """
        Estrae i path PHYSICAL dai device del template di base e li usa come
        percorso canonico per i nuovi device.
        """
        paths: dict[str, list[str]] = {}
        devices_node = self._template_root.find("NETWORK/DEVICES")
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
                "power"
                if "power distribution" in raw_type else
                None
            )
            if key is None:
                continue

            path_parts = [p.strip("{} ") for p in phys_elem.text.split(",") if p.strip()]
            paths[key] = path_parts

        return paths

    def _extract_base_pw_nodes(self) -> dict[str, ET.Element]:
        """
        Recupera i nodi prototipo (router/switch/pc) dal PHYSICALWORKSPACE del template.
        """
        nodes: dict[str, ET.Element] = {}
        pw = self._template_root.find("PHYSICALWORKSPACE")
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
                "power"
                if "power distribution device0" in raw else
                None
            )
            if key and key not in nodes:
                nodes[key] = copy.deepcopy(node)

        return nodes

    def _build_pw_skeleton(self) -> Optional[ET.Element]:
        """
        Costruisce un clone del PHYSICALWORKSPACE del template senza nodi device (TYPE=6).
        Serve per ripartire da una struttura coerente ed evitare residui.
        """
        pw = self._template_root.find("PHYSICALWORKSPACE")
        if pw is None:
            return None

        skeleton = copy.deepcopy(pw)

        def strip_devices(node: ET.Element) -> None:
            to_remove = []
            for child in list(node):
                if child.tag == "NODE":
                    ntype = child.findtext("TYPE")
                    if ntype == "6":
                        to_remove.append(child)
                    else:
                        strip_devices(child)
                else:
                    strip_devices(child)
            for c in to_remove:
                node.remove(c)

        strip_devices(skeleton)
        return skeleton

    def _extract_pc_parent_node(self) -> Optional[ET.Element]:
        """
        Trova il NODE padre che contiene PC0 nel PHYSICALWORKSPACE di base.
        """
        pw = self._template_root.find("PHYSICALWORKSPACE")
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

    def sync_physical_workspace(
        self,
        root: ET.Element,
        devices_elem: ET.Element,
    ) -> None:
        """
        Allinea ogni device (WORKSPACE/PHYSICAL) con il PHYSICALWORKSPACE globale.
        """
        if not self._base_physical_paths:
            return

        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return

        # Nodo Rack (per router/switch e fallback)
        rack_node: Optional[ET.Element] = None
        for node in pw.iter("NODE"):
            name = (node.findtext("NAME") or "").strip()
            if name == "Rack":
                rack_node = node
                break

        # Parent dei PC nel PHYSICALWORKSPACE corrente (non quello della base)
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

        pc_parent_node = find_pc_parent(pw) or self._pc_parent_node

        # Index: NAME -> NODE esistente
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
            name_elem = dev.find("ENGINE/NAME")
            type_elem = dev.find("ENGINE/TYPE")
            phys_elem = dev.find("WORKSPACE/PHYSICAL")
            if name_elem is None or type_elem is None or phys_elem is None:
                continue

            dname = name_elem.text or ""
            dtype = (type_elem.text or "").lower()
            if not dname:
                continue

            # pc/server -> "pc", switch -> "switch", router -> "router"
            if "pc" in dtype or "server" in dtype:
                base_key = "pc"
            elif "switch" in dtype:
                base_key = "switch"
            elif "router" in dtype:
                base_key = "router"
            elif "power distribution" in dtype:
                base_key = "power"
            else:
                continue

            base_path = self._base_physical_paths.get(base_key, [])
            if not base_path:
                continue

            parent_node = None
            if len(base_path) >= 2:
                parent_node = uuid_nodes.get(base_path[-2])
            if parent_node is None:
                # fallback: usa Rack come contenitore predefinito
                parent_node = rack_node

            # GUID nuovo e path fisico aggiornato nel device
            new_guid = str(uuid.uuid4())
            new_path = base_path[:-1] + [new_guid]
            phys_elem.text = ",".join(f"{{{p}}}" for p in new_path)

            # Nodo fisico corrispondente (crea se manca)
            pw_node = pw_nodes.get(dname)
            if pw_node is None:
                proto = self._base_pw_nodes.get(base_key)
                if proto is not None:
                    pw_node = copy.deepcopy(proto)
                    name_field = pw_node.find("NAME")
                    if name_field is not None:
                        name_field.text = dname

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
                # Aggiorna sempre l'UUID per farlo combaciare con il path PHYSICAL appena scritto
                uuid_elem.text = f"{{{new_guid}}}"

    def reset_physical_workspace(self, root: ET.Element) -> None:
        """Sostituisce il PHYSICALWORKSPACE con lo scheletro del template, senza device."""
        if self._pw_skeleton is None:
            return
        parent = root
        pw_old = parent.find("PHYSICALWORKSPACE")
        if pw_old is not None:
            parent.remove(pw_old)
        parent.append(copy.deepcopy(self._pw_skeleton))
