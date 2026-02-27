from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Optional
import uuid

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from . import utils
from .physical_workspace import PhysicalWorkspaceManager
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

        # Prototipo del Power Distribution Device (PDU) presente nel template base
        self._power_proto: Optional[ET.Element] = None
        for dev in self.template_root.findall("NETWORK/DEVICES/DEVICE"):
            name = (dev.findtext("ENGINE/NAME") or "").lower()
            dtype = (dev.findtext("ENGINE/TYPE") or "").lower()
            if "power distribution" in name or "power distribution" in dtype:
                self._power_proto = copy.deepcopy(dev)
                break

        # Gestione del Physical Workspace delegata a un manager specializzato
        self._pw_manager = PhysicalWorkspaceManager(self.template_root)

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

        # Reset Physical Workspace to a clean skeleton (no device nodes)
        self._pw_manager.reset_physical_workspace(root)

        # Packet Tracer si aspetta un PDU nel rack: reintroducilo dal template base
        # Solo se abbiamo almeno un device utente; per la generazione "vuota" lasciamo
        # davvero la lista di dispositivi vuota (utile per i test e per file minimi).
        if devices_config:
            self._inject_power_distribution(devices_elem)

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
            set_text(engine, "SAVE_REF_ID", saveref, create=True)
            # Popola <SAVEREFID> solo se il template lo include già, per evitare tag non previsti da PT
            legacy = engine.find("SAVEREFID")
            if legacy is not None:
                legacy.text = saveref
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

            utils.set_coords(engine, x, y)

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
        self._pw_manager.sync_physical_workspace(root, devices_elem)

        # -----------------------
        # Links
        # -----------------------
        if links_config:
            for link_cfg in links_config:
                self._create_link(links_elem, link_cfg, device_saverefs)

        # Rimuovi eventuali tag legacy non previsti dai template base
        utils.remove_all_tags(root, "SAVEREFID")

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

    # ------------------------------------------------------------------
    # Power Distribution Device helper
    # ------------------------------------------------------------------
    def _inject_power_distribution(self, devices_elem: ET.Element) -> None:
        """
        Reintroduce il PDU del template base con ID e indirizzi nuovi.
        Packet Tracer rifiuta spesso file senza il PDU quando è presente un rack.
        """
        if self._power_proto is None:
            return

        # Rimuovi eventuali PDU già presenti per evitare duplicati di nome/UUID
        for existing in list(devices_elem.findall("DEVICE")):
            name = (existing.findtext("ENGINE/NAME") or "").lower()
            if "power distribution device" in name:
                devices_elem.remove(existing)

        pdu = copy.deepcopy(self._power_proto)

        engine = pdu.find("ENGINE")
        if engine is None:
            return

        set_text(engine, "NAME", "Power Distribution Device0", create=True)
        set_text(engine, "SYSNAME", "Power Distribution Device0", create=True)
        pdu_saveref = rand_saveref()
        set_text(engine, "SAVE_REF_ID", pdu_saveref, create=True)
        legacy = engine.find("SAVEREFID")
        if legacy is not None:
            legacy.text = pdu_saveref

        # Rigenera ID numerici lunghi per evitare collisioni col template
        for node in pdu.iter():
            if node.text and node.text.isdigit() and len(node.text) >= 10:
                node.text = rand_memaddr()

        devices_elem.append(pdu)
