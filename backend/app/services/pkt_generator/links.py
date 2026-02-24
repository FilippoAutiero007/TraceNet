"""
Link management logic for PKT generator.
Handles connecting devices with appropriate cables.

# TODO: Future enhancement: Use device_catalog.json to determine cable types and port capability.
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

    # All link-data tags must go inside <CABLE>, NOT directly on <LINK>.
    # The template already has a CABLE child with the correct structure.
    cable = new_link.find("CABLE")
    if cable is None:
        cable = ET.SubElement(new_link, "CABLE")
        # Populate mandatory CABLE defaults if created from scratch
        utils.set_text(cable, "LENGTH", "1", create=True)
        utils.set_text(cable, "FUNCTIONAL", "true", create=True)

    # Set FROM and TO references inside CABLE
    utils.set_text(cable, "FROM", from_saveref, create=True)
    utils.set_text(cable, "TO", to_saveref, create=True)

    # Ensure at least 2 PORT nodes exist inside CABLE
    ports = cable.findall("PORT")
    while len(ports) < 2:
        ports.append(ET.SubElement(cable, "PORT"))

    # Set Port Names
    ports[0].text = str(link_cfg.get("from_port", "FastEthernet0/0"))
    ports[1].text = str(link_cfg.get("to_port", "FastEthernet0/1"))

    # Set memaddr fields inside CABLE with correct underscore-separated names
    for tag in ("FROM_DEVICE_MEM_ADDR", "TO_DEVICE_MEM_ADDR",
                "FROM_PORT_MEM_ADDR", "TO_PORT_MEM_ADDR"):
        utils.set_text(cable, tag, utils.rand_memaddr(), create=True)

    return new_link
