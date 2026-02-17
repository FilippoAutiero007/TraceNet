"""
Topology and entry point for PKT generation.
Exposes the high-level API for generating PKT files.
"""
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.pkt_crypto import encrypt_pkt_data
from app.services.pkt_generator import utils
from app.services.pkt_generator.core import get_pkt_generator, resolve_template_path

logger = logging.getLogger(__name__)


def build_links_config(num_routers: int, num_switches: int, num_pcs: int) -> List[Dict[str, str]]:
    """Generates a standard topology linking Routers -> Switches -> PCs."""
    links_config: List[Dict[str, str]] = []

    # Connect Routers to Switches (1-to-1 or 1-to-Many)
    if num_routers > 0 and num_switches > 0:
        for i in range(min(num_routers, num_switches)):
            links_config.append({
                "from": utils.safe_name("Router", i),
                "from_port": "FastEthernet0/0",
                "to": utils.safe_name("Switch", i),
                "to_port": "FastEthernet0/1",
            })

        # Logic for extra switches connecting to last router
        if num_switches > num_routers:
            for i in range(num_routers, num_switches):
                port_idx = i - num_routers + 1
                links_config.append({
                    "from": utils.safe_name("Router", num_routers - 1),
                    "from_port": f"FastEthernet0/{port_idx}",
                    "to": utils.safe_name("Switch", i),
                    "to_port": "FastEthernet0/1",
                })

    # Connect Switches to PCs
    if num_switches > 0:
        for pc_idx in range(num_pcs):
            switch_idx = pc_idx % num_switches
            # Ports on switch start from 2 onwards (1 is uplink to router)
            port_num = (pc_idx // num_switches) + 2
            links_config.append({
                "from": utils.safe_name("Switch", switch_idx),
                "from_port": f"FastEthernet{port_num}/1",
                "to": utils.safe_name("PC", pc_idx),
                "to_port": "FastEthernet0",
            })

    return links_config


def save_pkt_file(subnets: List[Any], config: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    """
    Main entry point to generate a PKT file.
    
    Args:
        subnets: List of subnet objects (expected to have `usable_range`, `mask`).
        config: Configuration dict with `devices` counts (routers, switches, pcs).
        output_dir: Directory where the output PKT and XML files will be saved.
        
    Returns:
        Dict with generation results (filenames, paths, objects).
    """
    logger.info("Generating PKT file with template-based approach (modular)")

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        pkt_filename = f"network_{timestamp}.pkt"
        xml_filename = f"network_{timestamp}.xml"

        pkt_path = str(Path(output_dir) / pkt_filename)
        xml_path = str(Path(output_dir) / xml_filename)

        # 1. Prepare Configuration
        device_counts = config.get("devices", {})
        num_routers = int(device_counts.get("routers", 1))
        num_switches = int(device_counts.get("switches", 1))
        num_pcs = int(device_counts.get("pcs", 0))

        devices_config: List[Dict[str, Any]] = []

        # Routers
        for i in range(num_routers):
            devices_config.append({"name": utils.safe_name("Router", i), "type": "router"})

        # Switches
        for i in range(num_switches):
            devices_config.append({"name": utils.safe_name("Switch", i), "type": "switch"})

        # PCs (with IP assignment from subnets)
        pc_idx = 0
        for subnet in subnets:
            # Assign up to 3 PCs per subnet for now (logic specific to this topology generator)
            subnet_pcs = min(3, max(0, num_pcs - pc_idx))
            for i in range(subnet_pcs):
                if pc_idx >= num_pcs:
                    break
                
                # Handle subnet object structure (flexible for different implementations)
                usable = getattr(subnet, "usable_range", [])
                
                # Careful: usable could be a list of strings or list of objects
                try: 
                    ip = str(usable[i]) if i < len(usable) else ""
                except (IndexError, TypeError):
                    ip = ""
                    
                mask = getattr(subnet, "mask", "255.255.255.0")
                
                devices_config.append({
                    "name": utils.safe_name("PC", pc_idx),
                    "type": "pc",
                    "ip": ip,
                    "subnet": mask,
                })
                pc_idx += 1

        # Remaining PCs without IP
        while pc_idx < num_pcs:
            devices_config.append({"name": utils.safe_name("PC", pc_idx), "type": "pc"})
            pc_idx += 1

        links_config = build_links_config(num_routers, num_switches, num_pcs)

        # 2. Get Generator Instance
        template_path = str(resolve_template_path())
        generator = get_pkt_generator(template_path)

        # 3. Generate XML
        xml_root = generator.generate(devices_config, links_config)
        
        # 4. Save XML (Debug)
        tree = ET.ElementTree(xml_root)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        logger.info("Generated XML file: %s", xml_path)

        # 5. Save PKT (Encrypted)
        xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(xml_root, encoding="utf-8", method="xml")
        encrypted = encrypt_pkt_data(xml_bytes)
        Path(pkt_path).write_bytes(encrypted)
        logger.info("Generated PKT file: %s", pkt_path)

        return {
            "success": True,
            "pkt_file": pkt_filename,
            "xml_file": xml_filename,
            "pkt_path": pkt_path,
            "xml_path": xml_path,
            "devices": devices_config,
            "links": links_config,
            "encoding_used": "AES",
            "file_size": Path(pkt_path).stat().st_size
        }

    except Exception as e:
        logger.error("Error generating PKT file: %s", e, exc_info=True)
        # Re-raise or return error dict depending on API contract. 
        # Existing contract seems to expect raise or global handler, but user asked for safety.
        # However, looking at the old file, it raised. Let's raise to be safe for now but log it well.
        raise
