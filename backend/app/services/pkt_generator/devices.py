"""
Device management logic for PKT generator.
Handles cloning, positioning, and configuring devices.
"""
import copy
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

from app.services.pkt_generator import utils, layout

logger = logging.getLogger(__name__)


def clone_device(
    template_device: ET.Element, 
    index: int, 
    dev_config: Dict[str, Any], 
    total_devices: int,
    meta: Dict[str, Any] = None
) -> ET.Element:
    """
    Clone a device from a template and configure it.
    
    Args:
        template_device: The XML element to clone.
        index: The global index of the device (for layout).
        dev_config: Configuration dict (name, type, ip, etc).
        total_devices: Total number of devices (for layout).
        meta: Device catalog metadata (e.g. max_ports, port_prefix).
        
    Returns:
        ET.Element: The configured device XML element.
    """
    if meta is None:
        meta = {}
    new_device = copy.deepcopy(template_device)
    name = utils.validate_name(dev_config["name"])
    
    engine = new_device.find("ENGINE")
    if engine is None:
        raise ValueError(f"Invalid device template for {name}: missing ENGINE")

    # Basic identity
    utils.set_text(engine, "NAME", name, create=True)
    utils.set_text(engine, "SYSNAME", name, create=False)
    
    # Generate unique ID for saving — update the EXISTING <SAVE_REF_ID>
    # tag from the template (with underscores). Do NOT create <SAVEREFID>.
    saveref = utils.rand_saveref()
    utils.set_text(engine, "SAVE_REF_ID", saveref, create=True)
    
    # Store saveref in config for link generation later
    dev_config["_saveref"] = saveref

    # Layout
    # Allow override from config, otherwise calculate
    x = int(dev_config.get("x", -1))
    y = int(dev_config.get("y", -1))
    
    if x == -1 or y == -1:
        x, y = layout.calculate_device_coordinates(index, total_devices)

    # Update the EXISTING <COORD_SETTINGS> in the template (with underscores).
    # Do NOT create <COORDSETTINGS> / <XCOORD> / <YCOORD>.
    coord_settings = engine.find("COORD_SETTINGS")
    if coord_settings is not None:
        utils.set_text(coord_settings, "X_COORD", str(x), create=True)
        utils.set_text(coord_settings, "Y_COORD", str(y), create=True)
        # Leave Z_COORD unchanged (usually 0)
    else:
        # Fallback: create COORD_SETTINGS with correct names if missing
        coord_settings = ET.SubElement(engine, "COORD_SETTINGS")
        utils.set_text(coord_settings, "X_COORD", str(x), create=True)
        utils.set_text(coord_settings, "Y_COORD", str(y), create=True)
        utils.set_text(coord_settings, "Z_COORD", "0", create=True)

    # Set coordinates in WORKSPACE/LOGICAL (sometimes required for accurate placement)
    workspace = new_device.find("WORKSPACE")
    if workspace is not None:
        logical = workspace.find("LOGICAL")
        if logical is not None:
            utils.set_text(logical, "X", str(x), create=True)
            utils.set_text(logical, "Y", str(y), create=True)
            # Each device must carry unique logical addresses; re-roll from template values
            utils.set_text(logical, "DEV_ADDR", utils.rand_memaddr(), create=True)
            utils.set_text(logical, "MEM_ADDR", utils.rand_memaddr(), create=True)

    # IP Configuration
    if "ip" in dev_config:
        _configure_ip(engine, dev_config)

    return new_device


def _configure_ip(engine: ET.Element, dev_config: Dict[str, Any]) -> None:
    """Configure IP address on the first available port."""
    module = engine.find("MODULE")
    if module is None:
        return

    slots = module.findall("SLOT")
    if not slots:
        return

    # Usually Slot 0 has the ports
    slot_module = slots[0].find("MODULE")
    if slot_module is None:
        return

    port = slot_module.find("PORT")
    if port is None:
        return

    ip = str(dev_config.get("ip", ""))
    subnet = str(dev_config.get("subnet", "255.255.255.0"))
    
    if ip:
        utils.set_text(port, "IP", ip, create=True)
        utils.set_text(port, "SUBNET", subnet, create=True)
        utils.set_text(port, "POWER", "true", create=True)
        utils.set_text(port, "UPMETHOD", "3", create=True) # 3 = Static
