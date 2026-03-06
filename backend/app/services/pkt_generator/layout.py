"""
Hierarchical layout logic for PKT generator.
Calculates device coordinates using a tree-like pattern (routers -> switches -> hosts)
to minimize cable crossings.
"""
from typing import Any, Tuple


def calculate_device_coordinates(
    index: int, 
    total_devices: int, 
    start_x: int = 200, 
    start_y: int = 200, 
    col_spacing: int = 250, 
    row_spacing: int = 200
) -> Tuple[int, int]:
    """
    Legacy grid layout logic to avoid breaking old test imports.
    """
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


def _get_level(device_name: str, device_type: str) -> int:
    name_lower = device_name.lower()
    type_lower = device_type.lower()
    if "router" in name_lower or "router" in type_lower:
        return 0
    if "switch" in name_lower or "switch" in type_lower:
        return 1
    return 2


def _resolve_collisions(nodes: list[str], coords_x: dict[str, float], min_spacing: float) -> None:
    if not nodes:
        return
    # Maintain the initial order defined by barycenter
    nodes.sort(key=lambda n: coords_x[n])
    
    # Relaxation passes to resolve overlaps
    for _ in range(50):
        changed = False
        for i in range(len(nodes) - 1):
            curr, nxt = nodes[i], nodes[i+1]
            diff = coords_x[nxt] - coords_x[curr]
            if diff < min_spacing:
                overlap = min_spacing - diff
                coords_x[curr] -= overlap / 2.0
                coords_x[nxt] += overlap / 2.0
                changed = True
        if not changed:
            break
    
    # Enforce exact order post-relaxation just in case
    nodes.sort(key=lambda n: coords_x[n])


def apply_hierarchical_layout(devices_config: list[dict[str, Any]], links_config: list[dict[str, Any]]) -> None:
    """
    Applies a hierarchical layout to the devices, mutating the device dictionaries
    by inserting 'x' and 'y' keys.
    """
    if not devices_config:
        return

    # 1. Assign levels (0: Router, 1: Switch, 2: Host)
    levels: dict[int, list[str]] = {0: [], 1: [], 2: []}
    device_map = {d["name"]: d for d in devices_config}
    
    for d in devices_config:
        lvl = _get_level(d["name"], d.get("type", ""))
        levels[lvl].append(d["name"])
        
    # 2. Build adjacency mapping for barycenter computation
    parents: dict[str, list[str]] = {d["name"]: [] for d in devices_config}
    
    for link in (links_config or []):
        u = link.get("from")
        v = link.get("to")
        if not u or not v or u not in device_map or v not in device_map:
            continue
            
        lvl_u = _get_level(u, device_map[u].get("type", ""))
        lvl_v = _get_level(v, device_map[v].get("type", ""))
        
        # We only care about parent -> child relationships for layout
        if lvl_u < lvl_v:
            parents[v].append(u)
        elif lvl_v < lvl_u:
            parents[u].append(v)
            
    # 3. Order nodes within level using barycenter heuristic
    def get_barycenter(node: str, parent_list: list[str]) -> float:
        node_parents = parents[node]
        if not node_parents:
            return 0.0
        indices = [parent_list.index(p) for p in node_parents if p in parent_list]
        return sum(indices) / len(indices) if indices else 0.0

    levels[1].sort(key=lambda n: get_barycenter(n, levels[0]))
    levels[2].sort(key=lambda n: get_barycenter(n, levels[1]))
    
    # 4. Compute X, Y coordinates
    y_levels = {0: 100, 1: 250, 2: 400}
    spacing_x = 250.0
    start_x = 200.0
    
    coords_x: dict[str, float] = {}
    
    # Position Level 0 (Routers) evenly
    for i, node in enumerate(levels[0]):
        coords_x[node] = start_x + i * spacing_x
        
    # Position Level 1 (Switches)
    for i, node in enumerate(levels[1]):
        node_parents = parents[node]
        if node_parents and all(p in coords_x for p in node_parents):
            coords_x[node] = sum(coords_x[p] for p in node_parents) / len(node_parents)
        else:
            coords_x[node] = start_x + (i + 0.5) * spacing_x # slight offset if disconnected
            
    _resolve_collisions(levels[1], coords_x, spacing_x)
    
    # Position Level 2 (Hosts)
    host_spacing_x = 150.0 # Hosts can be packed slightly tighter
    for i, node in enumerate(levels[2]):
        node_parents = parents[node]
        if node_parents and all(p in coords_x for p in node_parents):
            coords_x[node] = sum(coords_x[p] for p in node_parents) / len(node_parents)
        else:
            coords_x[node] = start_x + i * host_spacing_x
            
    _resolve_collisions(levels[2], coords_x, host_spacing_x)
    
    # 5. Apply coordinates back to config
    for d in devices_config:
        name = d["name"]
        lvl = _get_level(name, d.get("type", ""))
        d["x"] = int(coords_x.get(name, start_x))
        d["y"] = y_levels.get(lvl, 200)

    # 6. Global centering for small standalone LANs
    if len(levels[0]) == 1 and len(devices_config) <= 8:
        min_x = min(d["x"] for d in devices_config)
        max_x = max(d["x"] for d in devices_config)
        min_y = min(d["y"] for d in devices_config)
        max_y = max(d["y"] for d in devices_config)
        
        target_cx = 400.0
        target_cy = 300.0
        
        current_cx = (min_x + max_x) / 2.0
        current_cy = (min_y + max_y) / 2.0
        
        offset_x = target_cx - current_cx
        offset_y = target_cy - current_cy
        
        for d in devices_config:
            d["x"] = int(d["x"] + offset_x)
            d["y"] = int(d["y"] + offset_y)

