"""Shared primitives for PKT topology layout."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LayoutParams:
    base_x: int = 760
    base_y: int = 120
    dx_router: int = 230
    dx_switch: int = 420
    dx_host: int = 130
    dy_layer: int = 170
    dy_host_row: int = 105
    max_hosts_per_row: int = 6
    canvas_center_x: int = 1100
    canvas_center_y: int = 360
    min_canvas_x: int = 80
    min_canvas_y: int = 80


def type_token(device: dict[str, Any]) -> str:
    return f"{device.get('name', '')} {device.get('type', '')}".lower()


def is_router(device: dict[str, Any]) -> bool:
    return "router" in type_token(device)


def is_switch(device: dict[str, Any]) -> bool:
    return "switch" in type_token(device)


def is_firewall(device: dict[str, Any]) -> bool:
    token = type_token(device)
    return "firewall" in token or "asa" in token


def is_server(device: dict[str, Any]) -> bool:
    return "server" in type_token(device)


def is_endpoint(device: dict[str, Any]) -> bool:
    return not is_router(device) and not is_switch(device) and not is_firewall(device)


def build_graph(
    devices_config: list[dict[str, Any]], links_config: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    device_map = {d["name"]: d for d in devices_config if d.get("name")}
    adjacency: dict[str, list[str]] = {name: [] for name in device_map}
    for link in links_config or []:
        left = link.get("from")
        right = link.get("to")
        if left in device_map and right in device_map:
            adjacency[left].append(right)
            adjacency[right].append(left)
    return device_map, adjacency


def center_row(names: list[str], center_x: float, spacing: float) -> dict[str, tuple[float, float]]:
    if not names:
        return {}
    start_x = center_x - ((len(names) - 1) * spacing / 2.0)
    return {name: (start_x + i * spacing, 0.0) for i, name in enumerate(names)}


def set_row(
    pos: dict[str, tuple[float, float]],
    names: list[str],
    center_x: float,
    y: float,
    spacing: float,
    y_stagger: float = 0.0,
) -> None:
    row = center_row(names, center_x, spacing)
    for idx, name in enumerate(names):
        x, _ = row[name]
        pos[name] = (x, y + (y_stagger if (idx % 2) else 0.0))


def assign_hosts_under_switches(
    pos: dict[str, tuple[float, float]],
    hosts_by_parent: dict[str, list[str]],
    switch_y: float,
    params: LayoutParams,
    host_base_layer_gap: float = 170.0,
) -> None:
    for parent_name, hosts in hosts_by_parent.items():
        parent_x, _ = pos.get(parent_name, (params.base_x, switch_y))
        for idx, host_name in enumerate(hosts):
            row_idx = idx // params.max_hosts_per_row
            col_idx = idx % params.max_hosts_per_row
            row_count = min(len(hosts) - row_idx * params.max_hosts_per_row, params.max_hosts_per_row)
            row_mid = (row_count - 1) / 2.0
            x = parent_x + (col_idx - row_mid) * params.dx_host
            y = switch_y + host_base_layer_gap + row_idx * params.dy_host_row
            pos[host_name] = (x, y)


def switches_by_router(
    routers: list[str], switches: list[str], adjacency: dict[str, list[str]]
) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {r: [] for r in routers}
    if not routers:
        return mapping
    router_set = set(routers)
    for sw in switches:
        parents = [n for n in adjacency.get(sw, []) if n in router_set]
        if parents:
            mapping[parents[0]].append(sw)
        else:
            mapping[routers[0]].append(sw)
    return mapping


def hosts_by_parent(
    hosts: list[str], candidate_parents: list[str], adjacency: dict[str, list[str]]
) -> dict[str, list[str]]:
    parent_set = set(candidate_parents)
    grouped: dict[str, list[str]] = {p: [] for p in candidate_parents}
    if not candidate_parents:
        return grouped
    default_parent = candidate_parents[0]
    for host in hosts:
        parents = [n for n in adjacency.get(host, []) if n in parent_set]
        grouped[parents[0] if parents else default_parent].append(host)
    return grouped


def resolve_overlaps(pos: dict[str, tuple[float, float]], min_dx: float = 110.0, min_dy: float = 70.0) -> None:
    names = sorted(pos.keys())
    for _ in range(10):
        moved = False
        for i, left_name in enumerate(names):
            x1, y1 = pos[left_name]
            for right_name in names[i + 1:]:
                x2, y2 = pos[right_name]
                if abs(x2 - x1) < min_dx and abs(y2 - y1) < min_dy:
                    pos[right_name] = (x2 + min_dx * 0.75, y2 + min_dy * 0.25)
                    moved = True
        if not moved:
            break


def center_layout(pos: dict[str, tuple[float, float]], params: LayoutParams) -> None:
    if not pos:
        return
    xs = [coord[0] for coord in pos.values()]
    ys = [coord[1] for coord in pos.values()]
    current_cx = (min(xs) + max(xs)) / 2.0
    current_cy = (min(ys) + max(ys)) / 2.0
    shift_x = float(params.canvas_center_x) - current_cx
    shift_y = float(params.canvas_center_y) - current_cy

    if (min(xs) + shift_x) < params.min_canvas_x:
        shift_x += params.min_canvas_x - (min(xs) + shift_x)
    if (min(ys) + shift_y) < params.min_canvas_y:
        shift_y += params.min_canvas_y - (min(ys) + shift_y)

    for name, (x, y) in list(pos.items()):
        pos[name] = (x + shift_x, y + shift_y)
