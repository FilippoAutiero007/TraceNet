from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Optional

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
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
TEMPLATES_BASE_DIR = Path("backend/templates/FinalPoint")


class PKTGenerator:
    def __init__(self, template_path: str = "backend/templates/simple_ref.pkt") -> None:
        """
        Usa un template base solo per la struttura NETWORK/DEVICES/LINKS.
        I singoli device vengono clonati da template specifici per tipo.
        """
        template_bytes = Path(template_path).read_bytes()
        xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
        self.template_root = ET.fromstring(xml_str)

        template_network = self.template_root.find("NETWORK")
        if template_network is None:
            raise ValueError("Invalid template: missing NETWORK node")

        links_node = template_network.find("LINKS")
        template_links = links_node.findall("LINK") if links_node is not None else []
        self.link_template: Optional[ET.Element] = template_links[0] if template_links else None

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

            saveref = rand_saveref()
            set_text(engine, "SAVEREFID", saveref, create=True)
            device_saverefs[name] = saveref

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

        # Ensure FROM/TO exist
        set_text(link, "FROM", from_saveref, create=True)
        set_text(link, "TO", to_saveref, create=True)

        # Ensure at least 2 PORT nodes
        ports = link.findall("PORT")
        while len(ports) < 2:
            ports.append(ET.SubElement(link, "PORT"))

        ports[0].text = str(link_cfg.get("from_port", "FastEthernet0/0"))
        ports[1].text = str(link_cfg.get("to_port", "FastEthernet0/1"))

        # Set memaddr fields (create if missing)
        for tag in ("FROMDEVICEMEMADDR", "TODEVICEMEMADDR", "FROMPORTMEMADDR", "TOPORTMEMADDR"):
            set_text(link, tag, rand_memaddr(), create=True)

        links_elem.append(link)
