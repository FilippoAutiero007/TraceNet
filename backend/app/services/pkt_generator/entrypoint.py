# backend/app/services/pkt_generator/entrypoint.py

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.pkt_crypto import decrypt_pkt_data
from .template import get_pkt_generator, get_template_path
from .topology import build_links_config
from .utils import safe_name

logger = logging.getLogger(__name__)


def save_pkt_file(subnets: list, config: dict[str, Any], output_dir: str) -> dict[str, Any]:
    logger.info("Generating PKT file with template-based approach")

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        pkt_filename = f"network_{timestamp}.pkt"
        xml_filename = f"network_{timestamp}.xml"

        pkt_path = str(Path(output_dir) / pkt_filename)
        xml_path = str(Path(output_dir) / xml_filename)

        template_path = str(get_template_path())
        generator = get_pkt_generator(template_path)

        device_counts = config.get("devices", {})
        num_routers = int(device_counts.get("routers", 1))
        num_switches = int(device_counts.get("switches", 1))
        num_pcs = int(device_counts.get("pcs", 0))

        devices_config: list[dict[str, Any]] = []

        # Router: usa di default il modello a 2 porte (id dal JSON)
        for i in range(num_routers):
            devices_config.append({
                "name": safe_name("Router", i),
                "type": "router-2port",
            })

        # Switch: ad esempio Cisco 2960 a 24 porte (id dal JSON)
        for i in range(num_switches):
            devices_config.append({
                "name": safe_name("Switch", i),
                "type": "switch-24port",
            })

        # PC: usa l'id che hai definito nel JSON per gli end device, qui assumo "pc"
        pc_idx = 0
        for subnet in subnets:
            subnet_pcs = min(3, max(0, num_pcs - pc_idx))
            for i in range(subnet_pcs):
                if pc_idx >= num_pcs:
                    break
                usable = getattr(subnet, "usable_range", [])
                ip = usable[i] if i < len(usable) else ""
                devices_config.append({
                    "name": safe_name("PC", pc_idx),
                    "type": "pc",
                    "ip": ip,
                    "subnet": getattr(subnet, "mask", "255.255.255.0"),
                })
                pc_idx += 1

        while pc_idx < num_pcs:
            devices_config.append({
                "name": safe_name("PC", pc_idx),
                "type": "pc",
            })
            pc_idx += 1

        links_config = build_links_config(num_routers, num_switches, num_pcs)
        logger.info("Generating %s devices and %s links", len(devices_config), len(links_config))

        generator.generate(devices_config, links_config=links_config, output_path=pkt_path)

        # Export XML of the GENERATED PKT (not the template)
        pkt_bytes = Path(pkt_path).read_bytes()
        generated_xml = decrypt_pkt_data(pkt_bytes).decode("utf-8", errors="strict")
        Path(xml_path).write_text(generated_xml, encoding="utf-8")

        file_size = Path(pkt_path).stat().st_size
        return {
            "success": True,
            "pkt_path": pkt_path,
            "xml_path": xml_path,
            "pkt_file": pkt_filename,
            "xml_file": xml_filename,
            "devices": devices_config,
            "links": links_config,
            "encoding_used": "template_based",
            "file_size": file_size,
            "pka2xml_available": False,
            "method": "template_cloning",
        }

    except Exception as exc:
        logger.error("PKT generation failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}
