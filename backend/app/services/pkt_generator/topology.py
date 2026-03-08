# backend/app/services/pkt_generator/topology.py
from __future__ import annotations

from .utils import safe_name


def build_links_config(
    num_routers: int,
    num_switches: int,
    num_pcs: int,
    *,
    edge_routers: int | None = None,
    backbone_mode: str = "chain",
) -> list[dict[str, str]]:
    links_config: list[dict[str, str]] = []
    router_ports = [
        "FastEthernet0/0", "FastEthernet1/0", "FastEthernet2/0",
        "FastEthernet3/0", "FastEthernet4/0", "FastEthernet5/0",
        "FastEthernet6/0", "FastEthernet7/0", "FastEthernet8/0",
        "FastEthernet9/0",
    ]
    router_port_usage: dict[int, int] = {}

    def next_router_port(router_idx: int) -> str | None:
        used = router_port_usage.get(router_idx, 0)
        if used >= len(router_ports):
            return None
        router_port_usage[router_idx] = used + 1
        return router_ports[used]

    edge_count = edge_routers if edge_routers is not None else min(num_routers, num_switches)
    edge_count = max(0, min(edge_count, num_routers))
    if num_routers > 0 and num_switches > 0 and edge_count == 0:
        edge_count = min(1, num_routers)

    if num_routers > 0 and num_switches > 0:
        for i in range(num_switches):
            router_idx = i % edge_count if edge_count > 0 else max(0, num_routers - 1)
            from_port = next_router_port(router_idx)
            if from_port is None:
                continue
            links_config.append({
                "from": safe_name("Router", router_idx),
                "from_port": from_port,
                "to": safe_name("Switch", i),
                "to_port": "FastEthernet0/1",
            })

    if num_routers > 1:
        mode = (backbone_mode or "chain").strip().lower()
        backbone_router_indices = list(range(edge_count, num_routers))
        if not backbone_router_indices:
            backbone_router_indices = list(range(num_routers))

        if len(backbone_router_indices) > 1:
            if mode == "full-mesh":
                for i, from_idx in enumerate(backbone_router_indices):
                    for to_idx in backbone_router_indices[i + 1:]:
                        from_port = next_router_port(from_idx)
                        to_port = next_router_port(to_idx)
                        if from_port is None or to_port is None:
                            continue
                        links_config.append({
                            "from": safe_name("Router", from_idx),
                            "from_port": from_port,
                            "to": safe_name("Router", to_idx),
                            "to_port": to_port,
                        })
            else:
                for i in range(len(backbone_router_indices) - 1):
                    from_idx = backbone_router_indices[i]
                    to_idx = backbone_router_indices[i + 1]
                    from_port = next_router_port(from_idx)
                    to_port = next_router_port(to_idx)
                    if from_port is None or to_port is None:
                        continue
                    links_config.append({
                        "from": safe_name("Router", from_idx),
                        "from_port": from_port,
                        "to": safe_name("Router", to_idx),
                        "to_port": to_port,
                    })

        if edge_count > 0 and edge_count < num_routers and backbone_router_indices:
            for edge_idx in range(edge_count):
                to_idx = backbone_router_indices[edge_idx % len(backbone_router_indices)]
                from_port = next_router_port(edge_idx)
                to_port = next_router_port(to_idx)
                if from_port is None or to_port is None:
                    continue
                links_config.append({
                    "from": safe_name("Router", edge_idx),
                    "from_port": from_port,
                    "to": safe_name("Router", to_idx),
                    "to_port": to_port,
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
