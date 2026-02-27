"""
Legacy PKT generator (template-cloning path), refactored for readability.
"""
from __future__ import annotations

import copy
import logging
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.pkt_generator import devices, links, utils
from .device_catalog import DeviceCatalog
from .paths import resolve_path, resolve_template_path
from .physical_sync import PhysicalWorkspaceSync
from .template_repository import TemplateRepository

logger = logging.getLogger(__name__)


class PKTGenerator:
    """
    Generator for Cisco Packet Tracer (PKT) files using a template-based approach.
    Split into small collaborators:
      - TemplateRepository: handles PKT/template decryption & caching
      - DeviceCatalog: resolves device types to template metadata
      - PhysicalWorkspaceSync: keeps PHYSICALWORKSPACE aligned
    """

    def __init__(self, template_path: str = "simple_ref.pkt") -> None:
        self.template_path = template_path

        self.templates = TemplateRepository(template_path)
        self.catalog_resolver = DeviceCatalog(Path(__file__).parent / "device_catalog.json")
        # Preserve legacy public surface: tests expect .catalog to be a dict
        self.catalog = self.catalog_resolver.catalog
        self._pw_sync = PhysicalWorkspaceSync(self.templates.default_template_root)

    # Kept for backward compatibility with older tests/callers
    def resolve_device_type(self, device_type: str) -> Dict[str, Any]:
        return self.catalog_resolver.resolve(device_type)

    # ------------------------------------------------------------------ #
    # Main generation entry point                                        #
    # ------------------------------------------------------------------ #
    def generate(
        self,
        devices_config: List[Dict[str, Any]],
        links_config: Optional[List[Dict[str, Any]]] = None,
    ) -> ET.Element:
        """
        Generate a new PKT XML structure based on the provided configuration.
        """
        root = self.templates.clone_default_root()
        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Corrupted template state: NETWORK node missing in clone")

        devices_elem = utils.ensure_child(network, "DEVICES")
        links_elem = utils.ensure_child(network, "LINKS")
        devices_elem.clear()
        links_elem.clear()

        device_saverefs: Dict[str, str] = {}
        total_devices = len(devices_config)

        # 1) Devices
        for idx, dev_cfg in enumerate(devices_config):
            dev_type = str(dev_cfg.get("type", "router")).strip().lower()
            catalog_entry = self.catalog_resolver.resolve(dev_type)
            base_template_path = catalog_entry.get("base_template")

            if not base_template_path:
                logger.error("No base_template defined for device type '%s'", dev_type)
                continue

            try:
                template_device = self.templates.get_device_template(base_template_path)

                # clone_device is expected to write _saveref into dev_cfg
                new_device = devices.clone_device(
                    template_device,
                    idx,
                    dev_cfg,
                    total_devices,
                    meta=catalog_entry,
                )
                devices_elem.append(new_device)

                name = dev_cfg.get("name")
                saveref = dev_cfg.get("_saveref")
                if name and saveref:
                    device_saverefs[name] = saveref
                elif name:
                    logger.warning(
                        "clone_device did not populate '_saveref' for device '%s'; "
                        "links involving this device may not resolve correctly.",
                        name,
                    )

            except Exception as e:
                logger.error("Failed to create device '%s': %s", dev_cfg.get("name"), e)

        # 2) Links
        if links_config and self.templates.link_template is not None:
            for link_cfg in links_config:
                new_link = links.create_link(self.templates.link_template, link_cfg, device_saverefs)
                if new_link is not None:
                    links_elem.append(new_link)

        # 3) Physical workspace alignment (GUIDs + paths)
        self._pw_sync.sync(root, devices_elem)

        # Strip legacy tags that might not be accepted by PT
        utils.remove_all_tags(root, "SAVEREFID")

        return root


# --------------------------------------------------------------------------- #
# Module-level singleton factory (thread-safe double-checked locking)        #
# --------------------------------------------------------------------------- #

_generator_instance: Optional[PKTGenerator] = None
_generator_lock = threading.Lock()


def get_pkt_generator(template_path: str) -> PKTGenerator:
    """
    Return the shared PKTGenerator singleton, creating it on first call.
    Uses double-checked locking so it is safe under concurrent ASGI workers.
    """
    global _generator_instance
    if _generator_instance is None:
        with _generator_lock:
            if _generator_instance is None:
                resolved = resolve_path(template_path)
                path_str = str(resolved) if resolved else template_path
                logger.info("Initializing PKT generator with base template %s", path_str)
                _generator_instance = PKTGenerator(path_str)
    return _generator_instance


__all__ = ["PKTGenerator", "get_pkt_generator", "resolve_path", "resolve_template_path"]
