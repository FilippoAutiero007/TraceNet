# backend/app/services/pkt_generator/topology.py
from __future__ import annotations

from .utils import safe_name


def build_links_config(num_routers: int, num_switches: int, num_pcs: int) -> list[dict[str, str]]:
    links_config: list[dict[str, str]] = []

    if num_routers > 0 and num_switches > 0:
        for i in range(min(num_routers, num_switches)):
            links_config.append({
                "from": safe_name("Router", i),
                "from_port": "FastEthernet0/0",
                "to": safe_name("Switch", i),
                "to_port": "FastEthernet0/1",
            })

        if num_switches > num_routers:
            for i in range(num_routers, num_switches):
                port_idx = i - num_routers + 1
                links_config.append({
                    "from": safe_name("Router", num_routers - 1),
                    "from_port": f"FastEthernet0/{port_idx}",
                    "to": safe_name("Switch", i),
                    "to_port": "FastEthernet0/1",
                })

    if num_switches > 0:
        for pc_idx in range(num_pcs):
            switch_idx = pc_idx % num_switches
            # In Cisco 2960 (switch-24port), le porte sono FastEthernet0/1, 0/2, ...
            # Usiamo la porta 1 per il router, quindi partiamo dalla 2 per i PC
            port_num = (pc_idx // num_switches) + 2
            links_config.append({
                "from": safe_name("Switch", switch_idx),
                "from_port": f"FastEthernet0/{port_num}",
                "to": safe_name("PC", pc_idx),
                "to_port": "FastEthernet0",
            })

    return links_config
