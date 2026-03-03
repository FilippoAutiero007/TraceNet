from __future__ import annotations

import copy
import logging
import xml.etree.ElementTree as ET
from typing import Any, Callable

from app.services.pkt_generator.utils import validate_name

logger = logging.getLogger(__name__)


def _reorder_cable_children(cable: ET.Element) -> None:
    ordered_tags = [
        "LENGTH",
        "FUNCTIONAL",
        "FROM",
        "PORT",
        "TO",
        "PORT",
        "FROM_DEVICE_MEM_ADDR",
        "TO_DEVICE_MEM_ADDR",
        "FROM_PORT_MEM_ADDR",
        "TO_PORT_MEM_ADDR",
        "GEO_VIEW_COLOR",
        "IS_MANAGED_IN_RACK_VIEW",
        "TYPE",
    ]
    nodes_by_tag: dict[str, list[ET.Element]] = {}
    for child in list(cable):
        nodes_by_tag.setdefault(child.tag, []).append(child)
    for child in list(cable):
        cable.remove(child)
    for tag in ordered_tags:
        items = nodes_by_tag.get(tag, [])
        if not items:
            continue
        cable.append(items.pop(0))
    for remaining in nodes_by_tag.values():
        for child in remaining:
            cable.append(child)


def create_link(
    *,
    links_elem: ET.Element,
    link_template: ET.Element | None,
    link_cfg: dict[str, Any],
    device_saverefs: dict[str, str],
    get_device_type: Callable[[str], str],
) -> bool:
    if link_template is None:
        logger.warning("No link template available; skipping link %s", link_cfg)
        return False

    from_name = validate_name(str(link_cfg["from"]))
    to_name = validate_name(str(link_cfg["to"]))
    from_saveref = device_saverefs.get(from_name)
    to_saveref = device_saverefs.get(to_name)
    if not from_saveref or not to_saveref:
        logger.warning("Device not found for link: %s", link_cfg)
        return False

    link = copy.deepcopy(link_template)
    cable = link.find("CABLE")
    if cable is None:
        logger.error("Template link has no CABLE node!")
        return False

    from_elem = cable.find("FROM")
    if from_elem is not None:
        from_elem.text = from_saveref

    to_elem = cable.find("TO")
    if to_elem is not None:
        to_elem.text = to_saveref

    ports = cable.findall("PORT")
    if len(ports) >= 2:
        ports[0].text = str(link_cfg.get("from_port", "FastEthernet0/0"))
        ports[1].text = str(link_cfg.get("to_port", "FastEthernet0/0"))

    type_elem = cable.find("TYPE")
    if type_elem is not None:
        cable_type = link_cfg.get("cable_type")
        if cable_type is None:
            from_type = get_device_type(from_name)
            to_type = get_device_type(to_name)
            cable_type = "eCrossOver" if from_type == to_type else "eStraightThrough"
            logger.info("Auto-selected %s for %s ↔ %s", cable_type, from_name, to_name)
        norm = str(cable_type).strip()
        if norm == "4":
            norm = "eCrossOver"
        elif norm == "0":
            norm = "eStraightThrough"
        type_elem.text = norm

    _reorder_cable_children(cable)
    links_elem.append(link)
    return True
