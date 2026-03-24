"""Scenario-driven physical layout for PKT generator."""
from __future__ import annotations

from typing import Any, Tuple

from .layout_core import (
    LayoutParams,
    build_graph,
    center_layout,
    is_endpoint,
    is_firewall,
    is_router,
    is_server,
    is_switch,
    resolve_overlaps,
)
from .layout_scenarios import (
    choose_layout_scenario,
    get_layout_dispatcher,
    layout_lan_with_services_layers,
    layout_one_switch_multiple_vlan,
)


def calculate_device_coordinates(
    index: int,
    total_devices: int,
    start_x: int = 200,
    start_y: int = 200,
    col_spacing: int = 250,
    row_spacing: int = 200,
) -> Tuple[int, int]:
    """Legacy grid layout logic kept for compatibility with old unit tests."""
    if total_devices <= 4:
        cols = 2
    elif total_devices <= 9:
        cols = 3
    else:
        cols = 4

    row = index // cols
    col = index % cols
    col_effective = (cols - 1 - col) if (row % 2 == 1) else col
    default_x = start_x + (col_effective * col_spacing)
    default_y = start_y + (row * row_spacing)

    x_offset = (index % 2) * 30
    y_offset = (index % 2) * 50
    return (default_x + x_offset, default_y + y_offset)


def apply_hierarchical_layout(
    devices_config: list[dict[str, Any]],
    links_config: list[dict[str, Any]],
) -> None:
    """Assign X/Y coordinates to devices using scenario-based layout rules."""
    if not devices_config:
        return

    params = LayoutParams()
    device_map, adjacency = build_graph(devices_config, links_config or [])
    devices = list(device_map.values())

    routers = [d["name"] for d in devices if is_router(d)]
    switches = [d["name"] for d in devices if is_switch(d)]
    firewalls = [d["name"] for d in devices if is_firewall(d)]
    servers = [d["name"] for d in devices if is_server(d)]
    endpoints = [d["name"] for d in devices if is_endpoint(d)]
    scenario = choose_layout_scenario(devices_config, links_config or [])

    pos: dict[str, tuple[float, float]] = {}

    if scenario == "lan_with_services_layers":
        layout_lan_with_services_layers(
            pos,
            routers,
            firewalls,
            servers,
            switches,
            endpoints,
            adjacency,
            params,
        )
    elif scenario == "one_switch_multiple_vlan":
        layout_one_switch_multiple_vlan(
            pos,
            routers,
            switches,
            endpoints,
            device_map,
            params,
        )
    else:
        layout_fn = get_layout_dispatcher().get(scenario)
        if layout_fn is None:
            layout_fn = get_layout_dispatcher()["generic_hierarchical"]
        layout_fn(pos, routers, switches, endpoints, adjacency, params)

    # Per gli scenari generici manteniamo la vecchia logica di overlap+centering.
    # Evitiamo lo spostamento "a caso" dei client nei backbone multi-router.
    if scenario not in ("lan_with_services_layers", "one_switch_multiple_vlan"):
        if scenario != "multi_router_backbone":
            resolve_overlaps(pos)
        center_layout(pos, params)

    fallback_x, fallback_y = params.base_x, params.base_y + 2 * params.dy_layer
    for idx, device in enumerate(devices_config):
        name = device.get("name", "")
        x, y = pos.get(
            name,
            (fallback_x + idx * 40, fallback_y + (idx % 2) * 30),
        )
        device["x"] = int(round(x))
        device["y"] = int(round(y))


__all__ = [
    "LayoutParams",
    "calculate_device_coordinates",
    "choose_layout_scenario",
    "apply_hierarchical_layout",
]
