"""Scenario selection and placement rules for PKT topology layout."""
from __future__ import annotations

import math
from typing import Any, Callable

from .layout_core import (
    LayoutParams,
    assign_hosts_under_switches,
    hosts_by_parent,
    is_endpoint,
    is_firewall,
    is_router,
    is_server,
    is_switch,
    set_row,
    switches_by_router,
)


def choose_layout_scenario(devices_config: list[dict[str, Any]], links_config: list[dict[str, Any]]) -> str:
    from .layout_core import build_graph

    device_map, adjacency = build_graph(devices_config, links_config)
    devices = list(device_map.values())
    routers = [d["name"] for d in devices if is_router(d)]
    switches = [d["name"] for d in devices if is_switch(d)]
    firewalls = [d["name"] for d in devices if is_firewall(d)]
    servers = [d["name"] for d in devices if is_server(d)]
    endpoints = [d["name"] for d in devices if is_endpoint(d)]
    total_hosts = len(endpoints)

    lan_tags: set[str] = set()
    vlan_tags: set[str] = set()
    site_tags: set[str] = set()
    for d in devices:
        if d.get("lan"):
            lan_tags.add(str(d["lan"]))
        if d.get("subnet"):
            lan_tags.add(str(d["subnet"]))
        if d.get("vlan"):
            vlan_tags.add(str(d["vlan"]))
        if d.get("site"):
            site_tags.add(str(d["site"]))

    router_router_edges = 0
    switch_switch_edges = 0
    for name, neighs in adjacency.items():
        for neigh in neighs:
            if name < neigh:
                left = device_map[name]
                right = device_map[neigh]
                if is_router(left) and is_router(right):
                    router_router_edges += 1
                if is_switch(left) and is_switch(right):
                    switch_switch_edges += 1

    many_switch_chain = len(switches) >= 4 and switch_switch_edges >= (len(switches) - 1)
    has_services = bool(firewalls or servers) or any(d.get("dmz") for d in devices)
    multiple_lans = len(lan_tags) > 1
    multiple_vlans = len(vlan_tags) > 1
    multiple_sites = len(site_tags) > 1

    if (
        len(routers) == 1
        and len(lan_tags) <= 1
        and len(switches) <= 3
        and total_hosts <= 10
        and not multiple_sites
        and not has_services
        and not multiple_vlans
    ):
        return "single_small_lan_center"
    if len(routers) == 1 and multiple_lans and total_hosts <= 24:
        return "one_router_multiple_lans_same_band"
    if len(routers) > 1 and router_router_edges > 0 and not multiple_sites:
        return "multi_router_backbone"
    if multiple_sites and len(routers) > 1:
        branch_count = max(0, len(routers) - 1)
        return "hub_and_spoke_big" if branch_count >= 6 else "central_with_branches"
    if len(routers) == 1 and many_switch_chain:
        return "single_lan_switch_cascade"
    if has_services:
        return "lan_with_services_layers"
    if multiple_vlans and len(switches) <= 2:
        return "one_switch_multiple_vlan"
    if switch_switch_edges >= len(switches) and len(switches) >= 3:
        return "switch_ring_layout"
    return "generic_hierarchical"


def layout_single_small_lan_center(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    set_row(pos, routers, params.base_x, params.base_y, params.dx_router)
    switch_y = params.base_y + params.dy_layer + 50
    set_row(pos, switches, params.base_x, switch_y, params.dx_switch)

    # Separa server da PC tra gli endpoint
    servers = [n for n in endpoints if "server" in n.lower()]
    pcs = [n for n in endpoints if n not in servers]

    # PC sotto gli switch
    grouped = hosts_by_parent(pcs, switches, adjacency)
    assign_hosts_under_switches(pos, grouped, switch_y, params)

    # Server a destra, stessa Y dei PC
    pc_y = switch_y + params.dy_layer
    for idx, srv in enumerate(servers):
        pos[srv] = (
            params.base_x + params.dx_switch + (idx + 1) * (params.dx_host + 20),
            pc_y,
        )


def layout_one_router_multiple_lans_same_band(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    if routers:
        pos[routers[0]] = (params.base_x + 220, params.base_y)

    switch_y = params.base_y + params.dy_layer
    left_anchor = params.base_x - 120
    set_row(pos, switches, left_anchor, switch_y, params.dx_switch)

    grouped = hosts_by_parent(endpoints, switches, adjacency)
    assign_hosts_under_switches(pos, grouped, switch_y, params)

    if routers:
        router = routers[0]
        placed_hosts = {h for v in grouped.values() for h in v}
        direct_neighbors = [n for n in adjacency.get(router, []) if n in endpoints and n not in placed_hosts]
        for idx, name in enumerate(sorted(direct_neighbors)):
            pos[name] = (params.base_x + 220, params.base_y + params.dy_layer + (idx + 1) * 75)


def layout_multi_router_backbone(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    if not routers:
        return

    switch_set = set(switches)

    # Separa router edge (collegati a switch) da router backbone (solo router-router)
    edge_routers = []
    backbone_routers = []
    for r in routers:
        neighbors = adjacency.get(r, [])
        if any(n in switch_set for n in neighbors):
            edge_routers.append(r)
        else:
            backbone_routers.append(r)

    # Fallback se non si trovano edge/backbone
    if not backbone_routers and len(routers) > 1:
        backbone_routers = routers[len(edge_routers):]
    if not edge_routers:
        edge_routers = routers[:1]
        backbone_routers = routers[1:]

    n_edge = len(edge_routers)
    n_backbone = len(backbone_routers)
    center_x = params.base_x
    total_width = max((n_edge - 1) * (params.dx_router + 100), (n_backbone - 1) * (params.dx_router - 20), 600)

    # Backbone in semicerchio in alto
    backbone_y = params.base_y
    if n_backbone == 0:
        pass
    elif n_backbone == 1:
        pos[backbone_routers[0]] = (center_x, backbone_y)
    elif n_backbone == 2:
        pos[backbone_routers[0]] = (center_x - (params.dx_router - 20), backbone_y)
        pos[backbone_routers[1]] = (center_x + (params.dx_router - 20), backbone_y)
    else:
        radius_x = total_width / 2
        radius_y = radius_x * 0.35
        for idx, r in enumerate(backbone_routers):
            angle = math.pi * idx / max(1, n_backbone - 1)
            x = center_x - math.cos(angle) * radius_x
            y = backbone_y + math.sin(angle) * radius_y
            pos[r] = (x, y)

    # Edge router ai lati, sotto il backbone
    edge_y = backbone_y + params.dy_layer + 100
    if n_edge == 1:
        pos[edge_routers[0]] = (center_x, edge_y)
    elif n_edge == 2:
        spacing = max(total_width * 0.55, params.dx_router + 150)
        pos[edge_routers[0]] = (center_x - spacing / 2, edge_y)
        pos[edge_routers[1]] = (center_x + spacing / 2, edge_y)
    else:
        set_row(pos, edge_routers, center_x, edge_y, params.dx_router + 80)

    # Switch sotto i router edge
    switch_y = edge_y + params.dy_layer
    router_to_switches = switches_by_router(edge_routers or routers, switches, adjacency)
    for router in (edge_routers or routers):
        rx, _ = pos[router]
        set_row(pos, router_to_switches.get(router, []), rx, switch_y, params.dx_switch)

    # PC sotto gli switch
    local_params = LayoutParams(
        base_x=params.base_x,
        base_y=params.base_y,
        dx_router=params.dx_router,
        dx_switch=params.dx_switch,
        dx_host=params.dx_host - 20,
        dy_layer=params.dy_layer,
        dy_host_row=params.dy_host_row,
        max_hosts_per_row=4,
    )
    grouped = hosts_by_parent(endpoints, switches, adjacency)
    assign_hosts_under_switches(pos, grouped, switch_y, local_params)



def layout_central_with_branches(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    if not routers:
        return
    center = routers[0]
    branches = routers[1:]
    pos[center] = (params.base_x, params.base_y)
    set_row(pos, branches, params.base_x, params.base_y + params.dy_layer, params.dx_router - 10, y_stagger=30.0)

    switch_y = params.base_y + 2 * params.dy_layer + 30
    branch_to_switches = switches_by_router(branches or [center], switches, adjacency)
    for branch in branches or [center]:
        bx, _ = pos[branch]
        set_row(pos, branch_to_switches.get(branch, []), bx, switch_y, params.dx_switch)

    grouped = hosts_by_parent(endpoints, switches, adjacency)
    assign_hosts_under_switches(pos, grouped, switch_y, params)


def layout_hub_and_spoke_big(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    if not routers:
        return
    hub = routers[0]
    spokes = routers[1:]
    pos[hub] = (params.base_x, params.base_y)

    radius = params.dx_router + 40
    for idx, spoke in enumerate(spokes):
        angle = math.pi * (idx + 1) / (len(spokes) + 1)
        x = params.base_x + math.cos(angle) * radius
        y = params.base_y + 70 + math.sin(angle) * 90 + (25 if idx % 2 else 0)
        pos[spoke] = (x, y)

    switch_y = params.base_y + 2 * params.dy_layer + 20
    spoke_to_switches = switches_by_router(spokes or [hub], switches, adjacency)
    for spoke in spokes or [hub]:
        sx, _ = pos[spoke]
        set_row(pos, spoke_to_switches.get(spoke, []), sx, switch_y, params.dx_switch - 20)

    grouped = hosts_by_parent(endpoints, switches, adjacency)
    assign_hosts_under_switches(pos, grouped, switch_y, params)


def layout_single_lan_switch_cascade(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    if routers:
        pos[routers[0]] = (params.base_x, params.base_y)
    if switches:
        pos[switches[0]] = (params.base_x, params.base_y + params.dy_layer)
    for idx, sw in enumerate(switches[1:], start=1):
        pos[sw] = (
            params.base_x + idx * (params.dx_switch * 0.7),
            params.base_y + params.dy_layer + idx * 45,
        )

    grouped = hosts_by_parent(endpoints, switches, adjacency)
    for sw in switches:
        _, sw_y = pos.get(sw, (params.base_x, params.base_y + params.dy_layer))
        assign_hosts_under_switches(pos, {sw: grouped.get(sw, [])}, sw_y, params)
        for host in grouped.get(sw, []):
            hx, hy = pos[host]
            pos[host] = (hx, hy + 30)


def layout_lan_with_services_layers(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    firewalls: list[str],
    servers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    set_row(pos, routers, params.base_x, params.base_y, params.dx_router)
    set_row(pos, firewalls, params.base_x, params.base_y + params.dy_layer, params.dx_switch - 40)
    dmz_servers = [s for s in servers if "dmz" in s.lower()]
    internal_servers = [s for s in servers if s not in dmz_servers]
    set_row(pos, dmz_servers, params.base_x, params.base_y + params.dy_layer + 90, params.dx_host)

    # Switch più vicino al router se non ci sono firewall
    switch_gap = params.dy_layer if firewalls else params.dy_layer // 2
    switch_y = params.base_y + switch_gap + 40
    set_row(pos, switches, params.base_x, switch_y, params.dx_switch)

    # Server interni a fianco dei PC, vicino allo switch
    if switches:
        sw_x, _ = pos.get(switches[0], (params.base_x, switch_y))
    else:
        sw_x = params.base_x
    for idx, srv in enumerate(internal_servers):
        pos[srv] = (
            sw_x + params.dx_host * (idx + 1),
            switch_y + params.dy_layer,
        )


    grouped = hosts_by_parent([h for h in endpoints if h not in servers], switches, adjacency)
    assign_hosts_under_switches(pos, grouped, switch_y, params)


def layout_one_switch_multiple_vlan(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    device_map: dict[str, dict[str, Any]],
    params: LayoutParams,
) -> None:
    set_row(pos, routers, params.base_x, params.base_y, params.dx_router)
    switch_y = params.base_y + params.dy_layer
    set_row(pos, switches, params.base_x, switch_y, params.dx_switch)
    parent = switches[0] if switches else (routers[0] if routers else "")
    parent_x = pos.get(parent, (params.base_x, switch_y))[0]

    vlan_groups: dict[str, list[str]] = {}
    for host in endpoints:
        vlan = str(device_map.get(host, {}).get("vlan", "default"))
        vlan_groups.setdefault(vlan, []).append(host)

    ordered = sorted(vlan_groups.items(), key=lambda item: item[0])
    for group_idx, (_, hosts) in enumerate(ordered):
        block_x = parent_x + (group_idx - (len(ordered) - 1) / 2.0) * (params.dx_switch + 30)
        for idx, host in enumerate(hosts):
            row_idx = idx // params.max_hosts_per_row
            col_idx = idx % params.max_hosts_per_row
            row_count = min(len(hosts) - row_idx * params.max_hosts_per_row, params.max_hosts_per_row)
            row_mid = (row_count - 1) / 2.0
            x = block_x + (col_idx - row_mid) * params.dx_host
            y = switch_y + 145 + row_idx * params.dy_host_row + (16 if group_idx % 2 else 0)
            pos[host] = (x, y)


def layout_switch_ring(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    set_row(pos, routers, params.base_x, params.base_y, params.dx_router)
    ring_center_y = params.base_y + params.dy_layer + 20
    radius_x = max(params.dx_switch, (len(switches) * 46))
    radius_y = 120
    for idx, sw in enumerate(switches):
        angle = math.pi * (idx / max(1, len(switches) - 1))
        x = params.base_x - math.cos(angle) * radius_x
        y = ring_center_y + math.sin(angle) * radius_y
        pos[sw] = (x, y)

    grouped = hosts_by_parent(endpoints, switches, adjacency)
    for sw in switches:
        _, sw_y = pos.get(sw, (params.base_x, ring_center_y))
        assign_hosts_under_switches(pos, {sw: grouped.get(sw, [])}, sw_y, params)
        for host in grouped.get(sw, []):
            hx, hy = pos[host]
            pos[host] = (hx, hy + 30)


def layout_generic_hierarchical(
    pos: dict[str, tuple[float, float]],
    routers: list[str],
    switches: list[str],
    endpoints: list[str],
    adjacency: dict[str, list[str]],
    params: LayoutParams,
) -> None:
    router_rows = [routers[i:i + 4] for i in range(0, len(routers), 4)]
    for row_idx, row in enumerate(router_rows):
        set_row(pos, row, params.base_x, params.base_y + row_idx * 70, params.dx_router)

    switch_top = params.base_y + params.dy_layer + max(0, len(router_rows) - 1) * 70
    switch_rows = [switches[i:i + 5] for i in range(0, len(switches), 5)]
    for row_idx, row in enumerate(switch_rows):
        set_row(pos, row, params.base_x, switch_top + row_idx * 90, params.dx_switch)

    grouped = hosts_by_parent(endpoints, switches or routers, adjacency)
    parent_y = switch_top + (len(switch_rows) - 1) * 90 if switch_rows else (params.base_y + params.dy_layer)
    assign_hosts_under_switches(pos, grouped, parent_y, params)


ScenarioLayoutFn = Callable[
    [
        dict[str, tuple[float, float]],
        list[str],
        list[str],
        list[str],
        dict[str, list[str]],
        LayoutParams,
    ],
    None,
]


def get_layout_dispatcher() -> dict[str, ScenarioLayoutFn]:
    return {
        "single_small_lan_center": layout_single_small_lan_center,
        "one_router_multiple_lans_same_band": layout_one_router_multiple_lans_same_band,
        "multi_router_backbone": layout_multi_router_backbone,
        "central_with_branches": layout_central_with_branches,
        "hub_and_spoke_big": layout_hub_and_spoke_big,
        "single_lan_switch_cascade": layout_single_lan_switch_cascade,
        "switch_ring_layout": layout_switch_ring,
        "generic_hierarchical": layout_generic_hierarchical,
    }
