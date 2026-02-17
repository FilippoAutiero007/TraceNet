"""
Core PKT generator logic.
Orchestrates the loading of templates and generation of the network XML.
"""
import copy
import logging
import os
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from app.services.pkt_generator import devices, links, utils

logger = logging.getLogger(__name__)


class PKTGenerator:
    """
    Generator for Cisco Packet Tracer (PKT) files using a template-based approach.
    """

    def __init__(self, template_path: str = "simple_ref.pkt") -> None:
        """
        Initialize the generator by loading and parsing the template.
        """
        self.template_path = template_path
        try:
            template_bytes = Path(template_path).read_bytes()
            # Decrypt the template (PKT files are encrypted XML)
            xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
            self.template_root = ET.fromstring(xml_str)
        except Exception as e:
            raise ValueError(f"Failed to load PKT template from {template_path}: {e}")

        # Validate template structure
        self.network = self.template_root.find("NETWORK")
        if self.network is None:
            raise ValueError("Invalid template: missing NETWORK node")

        devices_node = self.network.find("DEVICES")
        if devices_node is None:
            raise ValueError("Invalid template: missing NETWORK/DEVICES node")

        # Index available devices by type
        self.device_templates: Dict[str, ET.Element] = {}
        for device in devices_node.findall("DEVICE"):
            engine = device.find("ENGINE")
            if engine is not None:
                dev_type = (engine.findtext("TYPE") or "").strip().lower()
                if dev_type:
                    self.device_templates[dev_type] = device

        if "router" not in self.device_templates:
            raise ValueError("Invalid template: no router device template found")

        # Find link template
        links_node = self.network.find("LINKS")
        link_list = links_node.findall("LINK") if links_node is not None else []
        self.link_template: Optional[ET.Element] = link_list[0] if link_list else None
        
        if self.link_template is None:
             logger.warning("Template contains no links; link generation will be disabled.")

    def generate(
        self, 
        devices_config: List[Dict[str, Any]], 
        links_config: Optional[List[Dict[str, Any]]] = None
    ) -> ET.Element:
        """
        Generate a new PKT XML structure based on the configuration.
        
        Args:
            devices_config: List of device configurations.
            links_config: List of link configurations.
            
        Returns:
            ET.Element: The root element of the generated XML.
        """
        # Deep copy the template structure to modify it
        root = copy.deepcopy(self.template_root)
        network = root.find("NETWORK")
        if network is None:
             raise ValueError("Corrupted template state: NETWORK node missing in clone")

        # Clear existing devices and links
        devices_elem = utils.ensure_child(network, "DEVICES")
        links_elem = utils.ensure_child(network, "LINKS")
        devices_elem.clear()
        links_elem.clear()

        # Map to store saverefs for link creation
        device_saverefs: Dict[str, str] = {}
        total_devices = len(devices_config)

        # 1. Create Devices
        for idx, dev_cfg in enumerate(devices_config):
            dev_type = str(dev_cfg.get("type", "router")).strip().lower() or "router"
            
            # Fallback to router if type not found
            template = self.device_templates.get(dev_type) or self.device_templates.get("router")
            if not template:
                 logger.warning(f"No template for device type {dev_type} and no router fallback")
                 continue

            try:
                new_device = devices.clone_device(template, idx, dev_cfg, total_devices)
                devices_elem.append(new_device)
                
                # Store the saveref we generated/assigned
                name = dev_cfg["name"] # validated inside clone_device
                saveref = dev_cfg.get("_saveref")
                if saveref:
                    device_saverefs[name] = saveref
            except Exception as e:
                logger.error(f"Failed to create device {dev_cfg.get('name')}: {e}")

        # 2. Create Links
        if links_config and self.link_template is not None:
            for link_cfg in links_config:
                new_link = links.create_link(self.link_template, link_cfg, device_saverefs)
                if new_link is not None:
                    links_elem.append(new_link)

        return root


@lru_cache(maxsize=1)
def get_pkt_generator(template_path: str) -> PKTGenerator:
    """Cached factory for PKTGenerator."""
    logger.info("Loading PKT generator template from %s", template_path)
    return PKTGenerator(template_path)


def resolve_template_path() -> Path:
    """Resolve the path to the PKT template file."""
    env_template = os.environ.get("PKT_TEMPLATE_PATH")
    if env_template and Path(env_template).exists():
        return Path(env_template)

    # Common locations
    candidates = [
        Path("/app/templates/simple_ref.pkt"),
        Path(__file__).resolve().parent.parent.parent.parent / "templates" / "simple_ref.pkt",
        Path.cwd() / "backend" / "templates" / "simple_ref.pkt",
         Path.cwd() / "templates" / "simple_ref.pkt",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("simple_ref.pkt template not found. Set PKT_TEMPLATE_PATH env variable.")
