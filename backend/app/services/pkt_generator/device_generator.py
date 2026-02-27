"""
Generazione dei device per un file PKT.
"""
from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data
from . import utils
from .utils import (
    validate_name,
    rand_saveref,
    rand_memaddr,
    set_text,
    load_device_templates_config,
)

logger = logging.getLogger(__name__)

DEVICE_TEMPLATES = load_device_templates_config()
_BASE = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_BASE_DIR = _BASE / "templates"


class DeviceGenerator:
    """
    Gestisce la generazione dei device in base alla configurazione.
    """

    def __init__(self, devices_elem: ET.Element):
        self._devices_elem = devices_elem

    def generate_devices(
        self,
        devices_config: list[dict[str, Any]],
    ) -> tuple[dict[str, str], set[str]]:
        """
        Genera i device e li aggiunge all'elemento `DEVICES`.
        Restituisce i saverefs e i MAC usati.
        """
        device_saverefs: dict[str, str] = {}
        used_macs: set[str] = set()

        num_devices = len(devices_config)
        if num_devices <= 4:
            cols = 2
        elif num_devices <= 9:
            cols = 3
        else:
            cols = 4

        for idx, dev_cfg in enumerate(devices_config):
            name = validate_name(dev_cfg["name"])
            dev_type = str(dev_cfg.get("type", "router-1port")).strip()

            device_meta = DEVICE_TEMPLATES.get(dev_type)
            if device_meta is None:
                logger.warning(
                    "Unknown device type %s, falling back to router-1port",
                    dev_type,
                )
                device_meta = DEVICE_TEMPLATES["router-1port"]

            relative_template = device_meta["template_file"]
            template_path = TEMPLATES_BASE_DIR / relative_template

            if not template_path.exists():
                raise FileNotFoundError(f"Template file not found: {template_path}")

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

            set_text(engine, "NAME", name, create=True)
            set_text(engine, "SYSNAME", name, create=False)

            saveref = rand_saveref()
            set_text(engine, "SAVE_REF_ID", saveref, create=True)
            legacy = engine.find("SAVEREFID")
            if legacy is not None:
                legacy.text = saveref
            device_saverefs[name] = saveref

            for node in new_device.iter():
                if node.text and node.text.isdigit() and len(node.text) >= 10:
                    node.text = rand_memaddr()

            def next_unique_mac() -> str:
                for _ in range(2000):
                    mac = utils.rand_realistic_mac(dev_type)
                    if mac not in used_macs:
                        used_macs.add(mac)
                        return mac
                raise RuntimeError("Unable to generate unique MAC")

            parent_map: dict[ET.Element, ET.Element] = {c: p for p in new_device.iter() for c in p}

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

            for bia in new_device.iter("BIA"):
                parent = parent_map.get(bia)
                if parent is not None and parent.find("MACADDRESS") is not None:
                    continue
                bia.text = next_unique_mac()

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

            self._devices_elem.append(new_device)

        return device_saverefs, used_macs

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
