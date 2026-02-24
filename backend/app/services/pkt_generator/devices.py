"""
Device management logic for PKT generator.
Handles cloning, positioning, and configuring devices.
"""
import copy
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict

from app.services.pkt_generator import utils, layout


logger = logging.getLogger(__name__)


def clone_device(
    template_device: ET.Element,
    index: int,
    dev_config: Dict[str, Any],
    total_devices: int,
    meta: Dict[str, Any] = None,
) -> ET.Element:
    """
    Clone a device from a template and configure it.

    Args:
        template_device: The XML element to clone.
        index:           Global index of the device (used for layout).
        dev_config:      Configuration dict (name, type, ip, subnet, x, y, ...).
        total_devices:   Total number of devices in the topology (for layout).
        meta:            Device catalog metadata (e.g. max_ports, port_prefix).

    Returns:
        ET.Element: The fully configured device XML element.
    """
    if meta is None:
        meta = {}

    new_device = copy.deepcopy(template_device)
    name = utils.validate_name(dev_config["name"])

    engine = new_device.find("ENGINE")
    if engine is None:
        raise ValueError(f"Invalid device template for '{name}': missing <ENGINE>")

    # ── Basic identity ────────────────────────────────────────────────────────
    utils.set_text(engine, "NAME",    name, create=True)
    utils.set_text(engine, "SYSNAME", name, create=False)

    # Update the EXISTING <SAVE_REF_ID> tag from the template.
    # Do NOT create a new <SAVEREFID> (no underscores variant).
    saveref = utils.rand_saveref()
    utils.set_text(engine, "SAVE_REF_ID", saveref, create=True)
    dev_config["_saveref"] = saveref

    # ── Normalize device type ─────────────────────────────────────────────────
    # Handles compound names like "router-8port", "switch-24port", "pc-desktop".
    raw_type = str(dev_config.get("type", "generic")).strip().lower()
    if "router" in raw_type:
        dev_type = "router"
    elif "switch" in raw_type:
        dev_type = "switch"
    elif "server" in raw_type:
        dev_type = "server"
    else:
        dev_type = "pc"

    # ── Realistic hardware serial (required by PT 8.2.2) ─────────────────────
    # PT marks the file as "Incompatible version" without a realistic serial.
    serial = utils.rand_realistic_serial(dev_type)
    for serial_elem in new_device.iterfind(".//SERIAL"):
        serial_elem.text = serial

    # ── Unique realistic MAC addresses (hex12, as per PT 8.2.2 manual) ───────
    # Each interface gets a dynamically generated MAC — no hardcoded pool,
    # so the topology scales to any number of devices without collisions.
    mac_count = 0
    for container in new_device.iter():
        mac_elem = container.find("MACADDRESS")
        if mac_elem is None:
            mac_elem = container.find("MAC")
        if mac_elem is None:
            continue

        mac = utils.rand_realistic_mac(dev_type)
        mac_elem.text = mac
        mac_count += 1

        bia_elem = container.find("BIA")
        if bia_elem is not None:
            bia_elem.text = mac

        link_local = utils.mac_to_link_local(mac)
        for tag in ("IPV6_LINK_LOCAL", "IPV6_DEFAULT_LINK_LOCAL"):
            ll_elem = container.find(tag)
            if ll_elem is not None and link_local:
                ll_elem.text = link_local.upper()

    logger.debug("'%s': serial=%s, %d MAC(s) assigned", name, serial, mac_count)

    # ── Layout ────────────────────────────────────────────────────────────────
    x = int(dev_config.get("x", -1))
    y = int(dev_config.get("y", -1))

    if x == -1 or y == -1:
        x, y = layout.calculate_device_coordinates(index, total_devices)

    # Update the EXISTING <COORD_SETTINGS> in the template (underscore names).
    # Do NOT create <COORDSETTINGS> / <XCOORD> / <YCOORD>.
    coord_settings = engine.find("COORD_SETTINGS")
    if coord_settings is not None:
        utils.set_text(coord_settings, "X_COORD", str(x), create=True)
        utils.set_text(coord_settings, "Y_COORD", str(y), create=True)
        # Leave Z_COORD unchanged (already 0 in the template).
    else:
        # Fallback: template had no COORD_SETTINGS, create it from scratch.
        coord_settings = ET.SubElement(engine, "COORD_SETTINGS")
        utils.set_text(coord_settings, "X_COORD", str(x), create=True)
        utils.set_text(coord_settings, "Y_COORD", str(y), create=True)
        utils.set_text(coord_settings, "Z_COORD", "0",    create=True)

    # Mirror coordinates in WORKSPACE/LOGICAL and assign unique memory addresses.
    workspace = new_device.find("WORKSPACE")
    if workspace is not None:
        logical = workspace.find("LOGICAL")
        if logical is not None:
            utils.set_text(logical, "X",        str(x),                create=True)
            utils.set_text(logical, "Y",        str(y),                create=True)
            utils.set_text(logical, "DEV_ADDR", utils.rand_memaddr(),  create=True)
            utils.set_text(logical, "MEM_ADDR", utils.rand_memaddr(),  create=True)

    # ── IP Configuration ──────────────────────────────────────────────────────
    if "ip" in dev_config:
        _configure_ip(engine, dev_config)

    return new_device


def _configure_ip(engine: ET.Element, dev_config: Dict[str, Any]) -> None:
    """Configure a static IP address on the first available port (Slot 0)."""
    module = engine.find("MODULE")
    if module is None:
        return

    slots = module.findall("SLOT")
    if not slots:
        return

    # Slot 0 holds the built-in ports (Fa0/0, Fa0/1, etc.).
    slot_module = slots[0].find("MODULE")
    if slot_module is None:
        return

    port = slot_module.find("PORT")
    if port is None:
        return

    ip     = str(dev_config.get("ip",     ""))
    subnet = str(dev_config.get("subnet", "255.255.255.0"))

    if ip:
        utils.set_text(port, "IP",       ip,      create=True)
        utils.set_text(port, "SUBNET",   subnet,  create=True)
        utils.set_text(port, "POWER",    "true",  create=True)
        utils.set_text(port, "UPMETHOD", "3",     create=True)  # 3 = Static
