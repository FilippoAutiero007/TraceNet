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
    saveref = utils.rand_saveref()
    utils.set_text(engine, "SAVE_REF_ID", saveref, create=True)
    legacy = engine.find("SAVEREFID")
    if legacy is not None:
        legacy.text = saveref
    dev_config["_saveref"] = saveref

    # ── Normalize device type ─────────────────────────────────────────────────
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
    serial = utils.rand_realistic_serial(dev_type)
    for serial_elem in new_device.iterfind(".//SERIAL"):
        serial_elem.text = serial

    # ── Unique realistic MAC addresses ────────────────────────────────────────
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

    utils.set_coords(engine, x, y)

    workspace = new_device.find("WORKSPACE")
    if workspace is not None:
        logical = workspace.find("LOGICAL")
        if logical is not None:
            utils.set_text(logical, "X",        str(x),              create=True)
            utils.set_text(logical, "Y",        str(y),              create=True)
            utils.set_text(logical, "DEV_ADDR", utils.rand_memaddr(), create=True)
            utils.set_text(logical, "MEM_ADDR", utils.rand_memaddr(), create=True)

    # ── IP Configuration ──────────────────────────────────────────────────────
    is_pc = dev_type == "pc"
    dhcp_mode = str(dev_config.get("dhcp_mode", "")).lower() if is_pc else ""

    if "ip" in dev_config:
        if not is_pc:
            _configure_ip(engine, dev_config)
        else:
            if dhcp_mode == "static":
                _configure_ip(engine, dev_config)
            else:
                # DHCP: nessun IP statico sulla porta
                pass

    if is_pc and dhcp_mode == "dhcp":
        _set_pc_dhcp_mode(engine, dev_config)

    return new_device


def _configure_ip(engine: ET.Element, dev_config: Dict[str, Any]) -> None:
    """Configure a static IP address on the first available port (Slot 0)."""
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

    ip = str(dev_config.get("ip", ""))
    subnet = str(dev_config.get("subnet", "255.255.255.0"))

    if ip:
        utils.set_text(port, "IP",      ip,     create=True)
        utils.set_text(port, "SUBNET",  subnet, create=True)
        utils.set_text(port, "POWER",   "true", create=True)
        utils.set_text(port, "UPMETHOD","3",    create=True)  # 3 = Static


def _set_pc_dhcp_mode(engine: ET.Element, dev_config: Dict[str, Any]) -> None:
    """
    Imposta la porta principale del PC in modalità DHCP,
    replicando i tag visti nel dump XML di Packet Tracer.
    """
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

    # UP_METHOD = 1 (DHCP client in PT)
    upm = port.find("UP_METHOD")
    if upm is None:
        upm = ET.SubElement(port, "UP_METHOD")
    upm.text = "1"

    # Abilita DHCP sulla porta
    dhcp_en = port.find("PORT_DHCP_ENABLE")
    if dhcp_en is None:
        dhcp_en = ET.SubElement(port, "PORT_DHCP_ENABLE")
    dhcp_en.text = "true"

    # DHCP server IP (se fornito)
    dhcp_server_ip = str(dev_config.get("dhcp_server_ip", "")).strip()
    if dhcp_server_ip:
        ds = port.find("DHCP_SERVER_IP")
        if ds is None:
            ds = ET.SubElement(port, "DHCP_SERVER_IP")
        ds.text = dhcp_server_ip

        pdns = port.find("PORT_DNS")
        if pdns is None:
            pdns = ET.SubElement(port, "PORT_DNS")
        pdns.text = dhcp_server_ip

    # GATEWAY globale del PC (gateway della LAN)
    gateway_ip = str(dev_config.get("gateway_ip", "")).strip()
    if gateway_ip:
        gw = engine.find("GATEWAY")
        if gw is None:
            gw = ET.SubElement(engine, "GATEWAY")
        gw.text = gateway_ip
