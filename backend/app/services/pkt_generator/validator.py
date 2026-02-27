"""
Lightweight consistency checks for generated Packet Tracer XML.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Iterable, List, Set

logger = logging.getLogger(__name__)


class PktXmlConsistencyError(ValueError):
    """Base error for PKT XML validation failures."""


class MissingSaveRefIdError(PktXmlConsistencyError):
    """Raised when no SAVE_REF_ID / SAVEREFID nodes are present."""


class OrphanLinkEndpointError(PktXmlConsistencyError):
    """Raised when a LINK references an unknown save-ref-id."""


def _collect_save_refs(root: ET.Element) -> Set[str]:
    refs: Set[str] = set()
    for tag in ("SAVEREFID", "SAVE_REF_ID"):
        for node in root.iter(tag):
            if node.text:
                refs.add(node.text.strip())
    return refs


def _collect_link_refs(root: ET.Element) -> List[str]:
    refs: List[str] = []
    for cable in root.findall(".//LINK/CABLE"):
        for tag in ("FROM", "TO"):
            ref = cable.findtext(tag)
            if ref:
                refs.append(ref.strip())
    return refs


def validate_pkt_xml(root: ET.Element) -> None:
    """
    Validate coherence between device save-ref-ids and LINK endpoints.

    Raises:
        MissingSaveRefIdError: if no SAVEREFID/SAVE_REF_ID tags are found.
        OrphanLinkEndpointError: if any LINK FROM/TO points to an undefined id.
    """
    save_refs = _collect_save_refs(root)
    if not save_refs:
        raise MissingSaveRefIdError("No <SAVEREFID> or <SAVE_REF_ID> tags found in devices.")

    link_refs = _collect_link_refs(root)
    missing = sorted({ref for ref in link_refs if ref not in save_refs})
    if missing:
        msg = f"Link endpoints without matching save-ref-id: {', '.join(missing)}"
        logger.error(msg)
        raise OrphanLinkEndpointError(msg)

    # Optionally log when validation passes for debugging runs
    logger.debug("PKT XML validation passed: %d devices refs, %d link refs", len(save_refs), len(link_refs))
