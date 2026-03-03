# backend/app/services/pkt_generator/entrypoint.py

from __future__ import annotations

import ipaddress
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
        subnet_allocators: list[dict[str, Any]] = []
        for subnet in subnets:
            usable_range = getattr(subnet, "usable_range", None)
            if not isinstance(usable_range, list) or len(usable_range) != 2:
                logger.warning("Invalid usable_range for subnet %s: %r", getattr(subnet, "name", "?"), usable_range)
                continue

            try:
                start_ip = ipaddress.ip_address(str(usable_range[0]))
                end_ip = ipaddress.ip_address(str(usable_range[1]))
            except ValueError:
                logger.warning("Unparseable usable_range for subnet %s: %r", getattr(subnet, "name", "?"), usable_range)
                continue

            if int(start_ip) > int(end_ip):
                logger.warning("Empty usable_range for subnet %s: %r", getattr(subnet, "name", "?"), usable_range)
                continue

            subnet_allocators.append(
                {
                    "name": getattr(subnet, "name", ""),
                    "mask": getattr(subnet, "mask", "255.255.255.0"),
                    "next_ip": start_ip,
                    "end_ip": end_ip,
                }
            )

        while pc_idx < num_pcs and subnet_allocators:
            made_progress = False
            for alloc in subnet_allocators:
                if pc_idx >= num_pcs:
                    break
                if int(alloc["next_ip"]) > int(alloc["end_ip"]):
                    continue

                ip = str(alloc["next_ip"])
                alloc["next_ip"] = ipaddress.ip_address(int(alloc["next_ip"]) + 1)
                devices_config.append(
                    {
                        "name": safe_name("PC", pc_idx),
                        "type": "pc",
                        "ip": ip,
                        "subnet": alloc["mask"],
                    }
                )
                pc_idx += 1
                made_progress = True

            if not made_progress:
                break

        if pc_idx < num_pcs:
            logger.warning(
                "Not enough usable IPs to assign all PCs: assigned=%s requested=%s",
                pc_idx,
                num_pcs,
            )
            while pc_idx < num_pcs:
                devices_config.append(
                    {
                        "name": safe_name("PC", pc_idx),
                        "type": "pc",
                    }
                )
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
