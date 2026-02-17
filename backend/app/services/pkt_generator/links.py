"""
Link management logic for PKT generator.
Handles creating connections between devices.
"""
import copy
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

from app.services.pkt_generator import utils

logger = logging.getLogger(__name__)


def create_link(
    link_template: ET.Element, 
    link_cfg: Dict[str, Any], 
    device_saverefs: Dict[str, str]
) -> Optional[ET.Element]:
    """
    Create a link element between two devices.
    
    Args:
        link_template: Template XML element for a link.
        link_cfg: Configuration dict (from, to, ports).
        device_saverefs: Map of device names to their SAVEREFID.
        
    Returns:
        Optional[ET.Element]: The new link XML element, or None if invalid.
    """
    try:
        from_name = utils.validate_name(str(link_cfg["from"]))
        to_name = utils.validate_name(str(link_cfg["to"]))
    except ValueError as e:
        logger.warning("Invalid link config: %s", e)
        return None

    from_saveref = device_saverefs.get(from_name)
    to_saveref = device_saverefs.get(to_name)

    if not from_saveref or not to_saveref:
        logger.warning(
            "Device not found for link: %s -> %s (Refs: %s -> %s)", 
            from_name, to_name, from_saveref, to_saveref
        )
        return None

    new_link = copy.deepcopy(link_template)

    # Set FROM and TO references
    utils.set_text(new_link, "FROM", from_saveref, create=True)
    utils.set_text(new_link, "TO", to_saveref, create=True)

    # Ensure at least 2 PORT nodes exist
    ports = new_link.findall("PORT")
    while len(ports) < 2:
        ports.append(ET.SubElement(new_link, "PORT"))

    # Set Port Names
    ports[0].text = str(link_cfg.get("from_port", "FastEthernet0/0"))
    ports[1].text = str(link_cfg.get("to_port", "FastEthernet0/1"))

    # Set random memaddr fields for internal consistency
    for tag in ("FROMDEVICEMEMADDR", "TODEVICEMEMADDR", "FROMPORTMEMADDR", "TOPORTMEMADDR"):
        utils.set_text(new_link, tag, utils.rand_memaddr(), create=True)

    return new_link
