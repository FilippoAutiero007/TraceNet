from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator import utils
from app.services.pkt_generator.utils import rand_memaddr, set_text, validate_name, rand_saveref


def _update_device_ip(engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
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


def _assign_unique_macs(new_device: ET.Element, used_macs: set[str], device_type: str) -> None:
    def next_unique_mac() -> str:
        for _ in range(2000):
            mac = utils.rand_realistic_mac(device_type)
            if mac not in used_macs:
                used_macs.add(mac)
                return mac
        raise RuntimeError("Unable to generate unique MAC")

    parent_map: dict[ET.Element, ET.Element] = {}

    def build_parent_map(node: ET.Element) -> None:
        for child in list(node):
            parent_map[child] = node
            build_parent_map(child)

    build_parent_map(new_device)

    for mac_elem in new_device.iter("MACADDRESS"):
        mac = next_unique_mac()
        mac_elem.text = mac
        parent = parent_map.get(mac_elem)
        if parent is None:
            continue
        bia = parent.find("BIA")
        if bia is not None:
            bia.text = mac
        link_local = utils.mac_to_link_local(mac)
        for tag in ("IPV6_LINK_LOCAL", "IPV6_DEFAULT_LINK_LOCAL"):
            ll = parent.find(tag)
            if ll is not None:
                ll.text = link_local.upper() if link_local else ""

    for bia in new_device.iter("BIA"):
        parent = parent_map.get(bia)
        if parent is not None and parent.find("MACADDRESS") is not None:
            continue
        bia.text = next_unique_mac()


def build_device(
    *,
    dev_cfg: dict[str, Any],
    idx: int,
    cols: int,
    templates_base_dir: Path,
    device_templates: dict[str, dict[str, Any]],
    used_macs: set[str],
    used_dev_addrs: set[str],
    used_mem_addrs: set[str],
) -> tuple[ET.Element, str, str, str, Optional[dict[str, Any]]]:
    name = validate_name(dev_cfg["name"])
    requested_type = str(dev_cfg.get("type", "router-1port")).strip()

    resolved_type = requested_type
    device_meta = device_templates.get(resolved_type)
    if device_meta is None:
        resolved_type = "router-1port"
        device_meta = device_templates[resolved_type]

    relative_template = device_meta["template_file"]
    template_path = templates_base_dir / relative_template
    if not template_path.exists():
        # Backward-compatible alias for historical catalog typo.
        candidate = templates_base_dir / relative_template.replace("FinalPoint/", "EndPoint/")
        if candidate != template_path and candidate.exists():
            template_path = candidate
            relative_template = str(Path("EndPoint") / Path(relative_template).name)

    if not template_path.exists() and resolved_type != "router-1port":
        resolved_type = "router-1port"
        device_meta = device_templates[resolved_type]
        relative_template = device_meta["template_file"]
        template_path = templates_base_dir / relative_template

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    xml_str = decrypt_pkt_data(template_path.read_bytes()).decode("utf-8", errors="strict")
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
        raise ValueError(f"Invalid device template {template_path}: missing ENGINE")

    set_text(engine, "NAME", name, create=True)
    set_text(engine, "SYSNAME", name, create=False)
    saveref = rand_saveref()
    set_text(engine, "SAVE_REF_ID", saveref, create=True)
    legacy = engine.find("SAVEREFID")
    if legacy is not None:
        legacy.text = saveref

    _assign_unique_macs(new_device, used_macs, requested_type)

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
            dev_addr = rand_memaddr()
            while dev_addr in used_dev_addrs:
                dev_addr = rand_memaddr()
            used_dev_addrs.add(dev_addr)
            set_text(logical, "DEV_ADDR", dev_addr, create=True)

            mem_addr = rand_memaddr()
            while mem_addr in used_mem_addrs:
                mem_addr = rand_memaddr()
            used_mem_addrs.add(mem_addr)
            set_text(logical, "MEM_ADDR", mem_addr, create=True)

    if dev_cfg.get("ip"):
        _update_device_ip(engine, dev_cfg)

    category = (device_meta.get("category") or resolved_type or "").lower()
    physical_hint: Optional[dict[str, Any]] = None
    phys_text = template_device.findtext("WORKSPACE/PHYSICAL")
    if phys_text:
        path_parts = [part.strip("{} ") for part in phys_text.split(",") if part.strip()]
        if path_parts:
            proto_node: Optional[ET.Element] = None
            pw = template_root.find("PHYSICALWORKSPACE")
            if pw is not None:
                leaf_uuid = path_parts[-1]
                for node in pw.iter("NODE"):
                    uuid_text = (node.findtext("UUID_STR") or "").strip("{} ")
                    if uuid_text == leaf_uuid:
                        proto_node = copy.deepcopy(node)
                        break
            physical_hint = {
                "path_parts": path_parts,
                "proto_node": proto_node,
                "source_template": str(relative_template),
                "source_type": resolved_type,
            }
    return new_device, name, saveref, category, physical_hint
