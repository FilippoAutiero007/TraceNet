from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Optional
import uuid

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from . import utils
from .utils import (
    validate_name,
    rand_saveref,
    rand_memaddr,
    ensure_child,
    set_text,
    load_device_templates_config,
)

logger = logging.getLogger(__name__)

# Carica definizione dei template (id -> metadata, incluso template_file)
DEVICE_TEMPLATES = load_device_templates_config()
_BASE = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_BASE_DIR = _BASE / "templates"


class PKTGenerator:
    def __init__(self, template_path: str | None = None) -> None:
        """
        Usa un template base solo per la struttura NETWORK/DEVICES/LINKS.
        I singoli device vengono clonati da template specifici per tipo.
        """
        if template_path is None:
            template_path = str(_BASE / "templates" / "simple_ref.pkt")
        
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Base template not found at {path.absolute()}")
            
        template_bytes = path.read_bytes()
        xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
        self.template_root = ET.fromstring(xml_str)

        template_network = self.template_root.find("NETWORK")
        if template_network is None:
            raise ValueError("Invalid template: missing NETWORK node")

        links_node = template_network.find("LINKS")
        template_links = links_node.findall("LINK") if links_node is not None else []
        self.link_template: Optional[ET.Element] = template_links[0] if template_links else None

        # Cache di riferimento per il Physical Workspace (path base + nodi prototipo)
        self._base_physical_paths = self._extract_base_physical_paths()
        self._base_pw_nodes = self._extract_base_pw_nodes()
        self._pc_parent_node = self._extract_pc_parent_node()

    def generate(
        self,
        devices_config: list[dict[str, Any]],
        links_config: Optional[list[dict[str, Any]]] = None,
        output_path: str = "output.pkt",
    ) -> str:
        root = copy.deepcopy(self.template_root)
        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Template clone error: missing NETWORK")

        devices_elem = ensure_child(network, "DEVICES")
        links_elem = ensure_child(network, "LINKS")

        devices_elem.clear()
        links_elem.clear()

        # Clean up Physical Workspace (remove orphaned device references)
        self._cleanup_physical_workspace(root)

        # -----------------------
        # GRID layout parameters
        # -----------------------
        num_devices = len(devices_config)
        if num_devices <= 4:
            cols = 2
        elif num_devices <= 9:
            cols = 3
        else:
            cols = 4

        device_saverefs: dict[str, str] = {}
        used_macs: set[str] = set()

        # -----------------------
        # Devices
        # -----------------------
        for idx, dev_cfg in enumerate(devices_config):
            name = validate_name(dev_cfg["name"])
            dev_type = str(dev_cfg.get("type", "router-1port")).strip()

            # 1) Metadati dal JSON
            device_meta = DEVICE_TEMPLATES.get(dev_type)
            if device_meta is None:
                logger.warning(
                    "Unknown device type %s, falling back to router-1port",
                    dev_type,
                )
                device_meta = DEVICE_TEMPLATES["router-1port"]

            relative_template = device_meta["template_file"]  # es. "Router/router_2port.pkt"
            template_path = TEMPLATES_BASE_DIR / relative_template

            if not template_path.exists():
                raise FileNotFoundError(f"Template file not found: {template_path}")

            # 2) Carica il PKT specifico del device
            template_bytes = template_path.read_bytes()
            xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
            template_root = ET.fromstring(xml_str)

            template_network = template_root.find("NETWORK")
            if template_network is None:
                raise ValueError(f"Invalid device template {template_path}: missing NETWORK")

            template_devices_node = template_network.find("DEVICES")
            if template_devices_node is None:
                raise ValueError(f"Invalid device template {template_path}: missing DEVICES")

            template_devices = template_devices_node.findall("DEVICE")
            if not template_devices:
                raise ValueError(f"Invalid device template {template_path}: no DEVICE found")

            template_device = template_devices[0]
            new_device = copy.deepcopy(template_device)

            engine = new_device.find("ENGINE")
            if engine is None:
                logger.warning("Skipping device %s: missing ENGINE in template %s", name, template_path)
                continue

            # Nome e saveref
            set_text(engine, "NAME", name, create=True)
            set_text(engine, "SYSNAME", name, create=False)

            # Genera un SAVE_REF_ID unico per ogni istanza clonata (match con template PT)
            saveref = rand_saveref()
            # Aggiorna l'eventuale SAVE_REF_ID esistente; rimuove SAVEREFID legacy se presente
            set_text(engine, "SAVE_REF_ID", saveref, create=True)
            legacy = engine.find("SAVEREFID")
            if legacy is not None:
                engine.remove(legacy)
            device_saverefs[name] = saveref

            # Rigenera tutti gli ID e indirizzi di memoria nel device clonato per evitare collisioni
            # Cerchiamo tutti gli elementi che contengono numeri lunghi (ID/MemAddr)
            for node in new_device.iter():
                if node.text and node.text.isdigit() and len(node.text) >= 10:
                    node.text = rand_memaddr()

            # MAC univoci e coerenti su TUTTI i nodi che hanno MACADDRESS
            def next_unique_mac() -> str:
                for _ in range(2000):
                    mac = utils.rand_realistic_mac(dev_type)
                    if mac not in used_macs:
                        used_macs.add(mac)
                        return mac
                raise RuntimeError("Unable to generate unique MAC")

            # Mappa parent -> children per gestire BIA/IPv6 nello stesso container
            parent_map: dict[ET.Element, ET.Element] = {}
            def build_parent_map(node: ET.Element):
                for child in list(node):
                    parent_map[child] = node
                    build_parent_map(child)
            build_parent_map(new_device)

            def assign_mac(mac_elem: ET.Element) -> None:
                mac = next_unique_mac()
                mac_elem.text = mac
                parent = parent_map.get(mac_elem)
                if parent is None:
                    return
                bia = parent.find("BIA")
                if bia is not None:
                    bia.text = mac
                link_local = utils.mac_to_link_local(mac)
                for tag in ("IPV6_LINK_LOCAL", "IPV6_DEFAULT_LINK_LOCAL"):
                    ll = parent.find(tag)
                    if ll is not None:
                        ll.text = link_local.upper() if link_local else ""

            for mac_elem in new_device.iter("MACADDRESS"):
                assign_mac(mac_elem)

            # BIA senza MACADDRESS nel parent: assegna mac unico
            for bia in new_device.iter("BIA"):
                parent = parent_map.get(bia)
                if parent is not None and parent.find("MACADDRESS") is not None:
                    continue
                bia.text = next_unique_mac()

            # Coordinate griglia con offset alternato
            default_x = 200 + (idx % cols) * 250
            default_y = 200 + (idx // cols) * 200
            y_offset = (idx % 2) * 50

            x = int(dev_cfg.get("x", default_x))
            y = int(dev_cfg.get("y", default_y + y_offset))

            coords = engine.find("COORDSETTINGS")
            if coords is None:
                coords = ET.SubElement(engine, "COORDSETTINGS")
            set_text(coords, "XCOORD", str(x), create=True)
            set_text(coords, "YCOORD", str(y), create=True)

            workspace = new_device.find("WORKSPACE")
            if workspace is not None:
                logical = workspace.find("LOGICAL")
                if logical is not None:
                    set_text(logical, "X", str(x), create=True)
                    set_text(logical, "Y", str(y), create=True)

            ip = dev_cfg.get("ip")
            if ip:
                self._update_device_ip(engine, dev_cfg)

            devices_elem.append(new_device)

        # Aggiorna il PHYSICALWORKSPACE con i nuovi device/cloni
        self._sync_physical_workspace(root, devices_elem)

        # -----------------------
        # Links
        # -----------------------
        if links_config:
            for link_cfg in links_config:
                self._create_link(links_elem, link_cfg, device_saverefs)

        xml_bytes = (
            b'<?xml version="1.0" encoding="utf-8"?>\n'
            + ET.tostring(root, encoding="utf-8", method="xml")
        )
        encrypted = encrypt_pkt_data(xml_bytes)
        Path(output_path).write_bytes(encrypted)

        return output_path

    def _update_device_ip(self, engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
        module = engine.find("MODULE")
        if module is None:
            return

        slots = module.findall("SLOT")
        if not slots:
            return

        slot_module = slots[0].find("MODULE")
        if slot_module is None:
            return

        port = slot_module.find("PORT")
        if port is None:
            return

        set_text(port, "IP", str(dev_cfg.get("ip", "")), create=True)
        set_text(port, "SUBNET", str(dev_cfg.get("subnet", "255.255.255.0")), create=True)
        set_text(port, "POWER", "true", create=True)
        set_text(port, "UPMETHOD", "3", create=True)

    def _create_link(
        self,
        links_elem: ET.Element,
        link_cfg: dict[str, Any],
        device_saverefs: dict[str, str],
    ) -> None:
        if self.link_template is None:
            logger.warning("No link template available; skipping link %s", link_cfg)
            return

        from_name = validate_name(str(link_cfg["from"]))
        to_name = validate_name(str(link_cfg["to"]))

        from_saveref = device_saverefs.get(from_name)
        to_saveref = device_saverefs.get(to_name)

        if not from_saveref or not to_saveref:
            logger.warning("Device not found for link: %s", link_cfg)
            return

        link = copy.deepcopy(self.link_template)

        # Tutti i campi devono stare dentro <CABLE>, non direttamente sotto <LINK>
        cable = link.find("CABLE")
        if cable is None:
            cable = ET.SubElement(link, "CABLE")
            set_text(cable, "LENGTH", "1", create=True)
            set_text(cable, "FUNCTIONAL", "true", create=True)

        set_text(cable, "FROM", from_saveref, create=True)
        set_text(cable, "TO", to_saveref, create=True)

        ports = cable.findall("PORT")
        while len(ports) < 2:
            ports.append(ET.SubElement(cable, "PORT"))

        ports[0].text = str(link_cfg.get("from_port", "FastEthernet0/0"))
        ports[1].text = str(link_cfg.get("to_port", "FastEthernet0/1"))

        for tag in (
            "FROM_DEVICE_MEM_ADDR",
            "TO_DEVICE_MEM_ADDR",
            "FROM_PORT_MEM_ADDR",
            "TO_PORT_MEM_ADDR",
        ):
            set_text(cable, tag, rand_memaddr(), create=True)

        links_elem.append(link)

    def _cleanup_physical_workspace(self, root: ET.Element) -> None:
        """
        Rimuove i riferimenti fisici ai device originali del template.
        I device nel physical workspace hanno TYPE=6.
        """
        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return

        def remove_device_nodes(parent: ET.Element):
            # Troviamo tutti i NODE children
            # Attenzione: i nodi possono essere in CHILDREN o direttamente sotto PW o altri nodi
            # Nel template analizzato: PW -> NODE (id=0) -> CHILDREN -> NODE (id=1) -> CHILDREN -> NODE (device)
            
            # 1. Rimuovi i nodi di tipo 6 (dispositivi) dal genitore corrente
            to_remove = []
            for node in parent.findall("NODE"):
                ntype = node.find("TYPE")
                if ntype is not None and ntype.text == "6":
                    to_remove.append(node)
            
            for node in to_remove:
                parent.remove(node)
                logger.debug("Removed orphaned physical node: %s", node.findtext("NAME"))

            # 2. Ricorsione sui CHILDREN di ogni rimasuglio (Intercity, City, Building...)
            for node in parent.findall("NODE"):
                children_node = node.find("CHILDREN")
                if children_node is not None:
                    remove_device_nodes(children_node)
                # Anche se non sono in CHILDREN, Packet Tracer a volte mette nodi annidati direttamente? 
                # Ma lo standard sembra essere CHILDREN.
        
        remove_device_nodes(pw)

    # ------------------------------------------------------------------
    # Physical workspace helpers (portati dal nuovo core generator)
    # ------------------------------------------------------------------
    def _extract_base_physical_paths(self) -> dict[str, list[str]]:
        """
        Estrae i path PHYSICAL dai device del template di base e li usa come
        percorso canonico per i nuovi device.
        """
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

    def _extract_base_pw_nodes(self) -> dict[str, ET.Element]:
        """
        Recupera i nodi prototipo (router/switch/pc) dal PHYSICALWORKSPACE del template.
        """
        nodes: dict[str, ET.Element] = {}
        pw = self.template_root.find("PHYSICALWORKSPACE")
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

    def _extract_pc_parent_node(self) -> Optional[ET.Element]:
        """
        Trova il NODE padre che contiene PC0 nel PHYSICALWORKSPACE di base.
        """
        pw = self.template_root.find("PHYSICALWORKSPACE")
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

    def _sync_physical_workspace(
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
                uuid_elem.text = f"{{{new_guid}}}"
