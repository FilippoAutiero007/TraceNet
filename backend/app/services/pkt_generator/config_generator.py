from __future__ import annotations

import ipaddress
from collections import deque
from typing import Any, Iterable, Optional


def _as_ipv4_network(ip: str, mask: str) -> Optional[ipaddress.IPv4Network]:
    try:
        iface = ipaddress.IPv4Interface(f"{ip}/{mask}")
    except Exception:
        return None
    return iface.network


def _normalize_protocol(value: Any) -> str:
    proto = str(value or "").strip().lower()
    if proto in {"rip", "ripv2"}:
        return "rip"
    if proto in {"static", "statica"}:
        return "static"
    if proto in {"ospf"}:
        return "ospf"
    return proto


def _iter_router_devices(all_devices: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    routers: list[dict[str, Any]] = []
    for d in all_devices:
        name = str(d.get("name", "")).strip()
        if not name:
            continue
        dtype = str(d.get("type", "")).lower()
        category = str(d.get("category", "")).lower()
        if "router" in dtype or "router" in category or name.lower().startswith("router"):
            routers.append(d)
    return routers


def _build_router_graph(
    routers: list[dict[str, Any]],
    links_config: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str]]]:
    """
    Graph edges: router -> list[(neighbor_router, neighbor_ip_on_shared_link)].

    Requires entrypoint to have populated per-router `interface_ips` mapping.
    """
    iface_ip: dict[str, dict[str, str]] = {}
    for r in routers:
        name = str(r.get("name", "")).strip()
        if not name:
            continue
        iface_ip[name] = {str(k): str(v) for k, v in (r.get("interface_ips") or {}).items() if v}

    graph: dict[str, list[tuple[str, str]]] = {str(r.get("name", "")): [] for r in routers if r.get("name")}
    for link in links_config or []:
        a = str(link.get("from", ""))
        b = str(link.get("to", ""))
        if not a.startswith("Router") or not b.startswith("Router"):
            continue
        a_port = str(link.get("from_port", "")).strip()
        b_port = str(link.get("to_port", "")).strip()
        if not a_port or not b_port:
            continue
        a_to_b_ip = iface_ip.get(b, {}).get(b_port, "")
        b_to_a_ip = iface_ip.get(a, {}).get(a_port, "")
        if a_to_b_ip:
            graph.setdefault(a, []).append((b, a_to_b_ip))
        if b_to_a_ip:
            graph.setdefault(b, []).append((a, b_to_a_ip))
    return graph


def _bfs_next_hop(start: str, goal: str, graph: dict[str, list[tuple[str, str]]]) -> Optional[str]:
    if start == goal:
        return None
    q: deque[str] = deque([start])
    prev: dict[str, Optional[str]] = {start: None}
    while q:
        cur = q.popleft()
        for nxt, _nxt_ip in graph.get(cur, []):
            if nxt in prev:
                continue
            prev[nxt] = cur
            if nxt == goal:
                q.clear()
                break
            q.append(nxt)
    if goal not in prev:
        return None
    # Walk backwards: goal -> ... -> start; return the node right after start.
    cur = goal
    while prev.get(cur) is not None and prev[cur] != start:
        cur = prev[cur]  # type: ignore[assignment]
    return cur if prev.get(cur) == start else None


def calculate_static_routes(
    router_name: str,
    all_devices: list[dict[str, Any]],
    links_config: list[dict[str, Any]],
    *,
    wan_prefix: int = 30,
) -> list[dict[str, str]]:
    """
    Calcola le rotte statiche per un router dato.

    Logica:
    1. Trova le interfacce LAN del router (role=lan) → subnet direttamente connesse
    2. Costruisce un grafo router-router usando le interfacce WAN (role=wan)
    3. Per ogni subnet LAN remota, calcola il primo hop e usa come next-hop l'IP WAN del router vicino

    Returns: lista di {"network": "x.x.x.x", "mask": "x.x.x.x", "next_hop": "x.x.x.x"}
    """
    _ = wan_prefix

    router_map = {d["name"]: d for d in _iter_router_devices(all_devices) if d.get("name")}
    me = router_map.get(router_name)
    if not me:
        return []

    def _iter_iface_networks(dev: dict[str, Any], *, role: str) -> list[ipaddress.IPv4Network]:
        out: list[ipaddress.IPv4Network] = []
        for iface in dev.get("interfaces") or []:
            if str(iface.get("role", "")).lower() != role:
                continue
            ip = str(iface.get("ip", "")).strip()
            mask = str(iface.get("mask", "")).strip()
            net = _as_ipv4_network(ip, mask)
            if net is not None:
                out.append(net)
        # Backward-compatible single-interface configs
        if role == "lan" and not out and dev.get("ip") and dev.get("subnet"):
            net = _as_ipv4_network(str(dev["ip"]), str(dev["subnet"]))
            if net is not None:
                out.append(net)
        return out

    my_lan_networks = {n.with_prefixlen for n in _iter_iface_networks(me, role="lan")}

    remote_lans: dict[str, list[ipaddress.IPv4Network]] = {}
    for r_name, r in router_map.items():
        if r_name == router_name:
            continue
        nets = [n for n in _iter_iface_networks(r, role="lan") if n.with_prefixlen not in my_lan_networks]
        if nets:
            remote_lans[r_name] = nets

    # Build WAN adjacency: router -> neighbors, and (router, neighbor) -> neighbor WAN IP.
    graph: dict[str, list[str]] = {name: [] for name in router_map}
    nh_ip: dict[tuple[str, str], str] = {}

    def _get_iface_ip(dev: dict[str, Any], port: str) -> str:
        for iface in dev.get("interfaces") or []:
            if str(iface.get("name", "")).strip() != port:
                continue
            if str(iface.get("role", "")).lower() != "wan":
                continue
            return str(iface.get("ip", "")).strip()
        return ""

    for link in links_config or []:
        a = str(link.get("from", "")).strip()
        b = str(link.get("to", "")).strip()
        if not a.startswith("Router") or not b.startswith("Router"):
            continue
        a_port = str(link.get("from_port", "")).strip()
        b_port = str(link.get("to_port", "")).strip()
        if not a_port or not b_port:
            continue
        ra = router_map.get(a)
        rb = router_map.get(b)
        if not ra or not rb:
            continue
        a_ip = _get_iface_ip(ra, a_port)
        b_ip = _get_iface_ip(rb, b_port)
        if not a_ip or not b_ip:
            continue
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
        nh_ip[(a, b)] = b_ip
        nh_ip[(b, a)] = a_ip

    def _first_hop(start: str, goal: str) -> Optional[str]:
        if start == goal:
            return None
        q: deque[str] = deque([start])
        prev: dict[str, Optional[str]] = {start: None}
        while q:
            cur = q.popleft()
            for nxt in graph.get(cur, []):
                if nxt in prev:
                    continue
                prev[nxt] = cur
                if nxt == goal:
                    q.clear()
                    break
                q.append(nxt)
        if goal not in prev:
            return None
        cur = goal
        while prev.get(cur) is not None and prev[cur] != start:
            cur = prev[cur]  # type: ignore[assignment]
        return cur if prev.get(cur) == start else None

    routes: list[dict[str, str]] = []
    added: set[str] = set()
    for dst_router, nets in remote_lans.items():
        hop = _first_hop(router_name, dst_router)
        if not hop:
            continue
        next_hop_ip = nh_ip.get((router_name, hop), "")
        if not next_hop_ip:
            continue
        for net in nets:
            key = net.with_prefixlen
            if key in my_lan_networks or key in added:
                continue
            added.add(key)
            routes.append(
                {
                    "network": str(net.network_address),
                    "mask": str(net.netmask),
                    "next_hop": str(next_hop_ip),
                }
            )

    return routes


def generate_router_config(
    dev_cfg: dict[str, Any],
    all_devices: list[dict[str, Any]],
    links_config: list[dict[str, Any]],
    topology: Any = None,
) -> list[str]:
    _ = topology
    name = str(dev_cfg.get("name", "Router")).strip() or "Router"

    commands: list[str] = ["!"]
    commands.append(f"hostname {name}")
    commands.append("no ip domain-lookup")
    commands.append("!")

    # ACL definitions (best-effort, permissive schema)
    for acl in dev_cfg.get("acl") or []:
        acl_type = str(acl.get("type", acl.get("kind", ""))).strip().lower()
        if acl_type in {"standard", "std"}:
            acl_id = str(acl.get("id", acl.get("number", "10"))).strip() or "10"
            for rule in acl.get("rules") or acl.get("entries") or []:
                action = str(rule.get("action", "permit")).strip().lower()
                src = str(rule.get("source", rule.get("src", ""))).strip()
                wc = str(rule.get("wildcard", "")).strip()
                if not src:
                    continue
                if not wc:
                    # If a mask was provided, convert to wildcard; else assume host.
                    mask = str(rule.get("mask", "")).strip()
                    if mask:
                        try:
                            wc = str(ipaddress.IPv4Address(int(ipaddress.IPv4Address("255.255.255.255")) - int(ipaddress.IPv4Address(mask))))
                        except Exception:
                            wc = ""
                if wc:
                    commands.append(f"access-list {acl_id} {action} {src} {wc}")
                else:
                    commands.append(f"access-list {acl_id} {action} {src}")
            if acl.get("deny_any", True):
                commands.append(f"access-list {acl_id} deny any")
            commands.append("!")
        elif acl_type in {"extended", "ext"}:
            acl_name = str(acl.get("name", acl.get("id", "ACL"))).strip() or "ACL"
            commands.append(f"ip access-list extended {acl_name}")
            for rule in acl.get("rules") or acl.get("entries") or []:
                line = str(rule.get("line", "")).strip()
                if line:
                    commands.append(f" {line}")
                    continue
                action = str(rule.get("action", "permit")).strip().lower()
                proto = str(rule.get("proto", rule.get("protocol", "ip"))).strip().lower()
                src = str(rule.get("src", rule.get("source", "any"))).strip() or "any"
                dst = str(rule.get("dst", rule.get("destination", "any"))).strip() or "any"
                dport = rule.get("dport", rule.get("dest_port"))
                if dport:
                    commands.append(f" {action} {proto} {src} {dst} eq {dport}")
                else:
                    commands.append(f" {action} {proto} {src} {dst}")
            commands.append("!")

    # Interfaces
    interfaces = dev_cfg.get("interfaces") or []
    if not interfaces and dev_cfg.get("ip") and dev_cfg.get("subnet"):
        interfaces = [
            {"name": "FastEthernet0/0", "ip": dev_cfg.get("ip"), "mask": dev_cfg.get("subnet"), "role": "lan"}
        ]

    # Track directly-connected networks for routing protocols
    connected_nets: set[str] = set()
    for iface in interfaces:
        if_name = str(iface.get("name", "")).strip()
        ip = str(iface.get("ip", "")).strip()
        mask = str(iface.get("mask", "")).strip()
        if not if_name:
            continue
        commands.append(f"interface {if_name}")
        encap = str(iface.get("encapsulation", "")).strip()
        if encap:
            commands.append(f" encapsulation {encap}")
        if ip and mask:
            commands.append(f" ip address {ip} {mask}")
            net = _as_ipv4_network(ip, mask)
            if net is not None:
                connected_nets.add(str(net.network_address))

        # NAT role
        nat_role = str(iface.get("nat", "")).strip().lower()
        if nat_role in {"inside", "outside"}:
            commands.append(f" ip nat {nat_role}")

        # Interface ACL application (best-effort)
        acl_apply = iface.get("acl") or {}
        if isinstance(acl_apply, dict) and acl_apply.get("id"):
            acl_id = str(acl_apply["id"]).strip()
            direction = str(acl_apply.get("direction", "in")).strip().lower()
            if direction not in {"in", "out"}:
                direction = "in"
            commands.append(f" ip access-group {acl_id} {direction}")
        elif isinstance(acl_apply, dict) and acl_apply.get("name"):
            acl_name = str(acl_apply["name"]).strip()
            direction = str(acl_apply.get("direction", "in")).strip().lower()
            if direction not in {"in", "out"}:
                direction = "in"
            commands.append(f" ip access-group {acl_name} {direction}")

        commands.append(" no shutdown")

        # ip helper-address per DHCP relay se c'è un server DHCP dedicato
        dhcp_server_ip = dev_cfg.get("dhcp_server_ip", "")
        role = str(iface.get("role", "")).strip().lower()
        if dhcp_server_ip and role == "lan":
            commands.append(f" ip helper-address {dhcp_server_ip}")
        commands.append("!")

    # DHCP from router (IOS DHCP server)
    if bool(dev_cfg.get("dhcp_from_router")):
        for iface in interfaces:
            if str(iface.get("role", "")).lower() != "lan":
                continue
            ip = str(iface.get("ip", "")).strip()
            mask = str(iface.get("mask", "")).strip()
            if not ip or not mask:
                continue
            net = _as_ipv4_network(ip, mask)
            if net is None:
                continue
            pool_name = str(iface.get("dhcp_pool", iface.get("role_name", net.network_address.exploded))).strip()
            # Exclude gateway + next 4 addresses when available.
            try:
                gw = ipaddress.IPv4Address(ip)
                excl_end = ipaddress.IPv4Address(int(gw) + 4)
                if excl_end in net:
                    commands.append(f"ip dhcp excluded-address {gw} {excl_end}")
                else:
                    commands.append(f"ip dhcp excluded-address {gw}")
            except Exception:
                pass
            commands.append(f"ip dhcp pool {pool_name}")
            commands.append(f" network {net.network_address} {net.netmask}")
            commands.append(f" default-router {ip}")
            dns = str(dev_cfg.get("dhcp_dns", "8.8.8.8")).strip() or "8.8.8.8"
            commands.append(f" dns-server {dns}")
            commands.append("!")

    # NAT (static/dynamic/pat) - best-effort permissive schema
    nat = dev_cfg.get("nat") or {}
    if isinstance(nat, dict) and nat.get("type"):
        nat_type = str(nat.get("type", "")).strip().lower()
        if nat_type == "static":
            inside = str(nat.get("inside_local", nat.get("local", ""))).strip()
            outside = str(nat.get("inside_global", nat.get("global", ""))).strip()
            if inside and outside:
                commands.append(f"ip nat inside source static {inside} {outside}")
                commands.append("!")
        elif nat_type in {"dynamic", "pool"}:
            pool = str(nat.get("pool_name", "POOL")).strip() or "POOL"
            start = str(nat.get("start", "")).strip()
            end = str(nat.get("end", "")).strip()
            netmask = str(nat.get("netmask", "")).strip()
            acl_id = str(nat.get("acl", "1")).strip() or "1"
            inside_net = str(nat.get("inside_network", "")).strip()
            inside_wc = str(nat.get("inside_wildcard", "")).strip()
            if start and end and netmask:
                commands.append(f"ip nat pool {pool} {start} {end} netmask {netmask}")
            if inside_net and inside_wc:
                commands.append(f"access-list {acl_id} permit {inside_net} {inside_wc}")
            commands.append(f"ip nat inside source list {acl_id} pool {pool}")
            commands.append("!")
        elif nat_type in {"pat", "overload"}:
            acl_id = str(nat.get("acl", "1")).strip() or "1"
            inside_net = str(nat.get("inside_network", "")).strip()
            inside_wc = str(nat.get("inside_wildcard", "")).strip()
            outside_iface = str(nat.get("outside_interface", "")).strip() or "FastEthernet0/1"
            if inside_net and inside_wc:
                commands.append(f"access-list {acl_id} permit {inside_net} {inside_wc}")
            commands.append(f"ip nat inside source list {acl_id} interface {outside_iface} overload")
            commands.append("!")

    protocol = _normalize_protocol(dev_cfg.get("routing") or dev_cfg.get("routing_protocol"))
    if protocol == "rip":
        commands.append("router rip")
        commands.append(" version 2")
        commands.append(" no auto-summary")
        # Aggiungi network per ogni interfaccia configurata
        networks_added = set()
        for iface in dev_cfg.get("interfaces", []):
            ip = str(iface.get("ip", "")).strip()
            mask = str(iface.get("mask", "")).strip()
            if not ip or not mask:
                continue
            try:
                import ipaddress

                # RIP vuole il network address classful
                net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                net_str = str(net.network_address)
                if net_str not in networks_added:
                    networks_added.add(net_str)
                    commands.append(f" network {net_str}")
            except Exception:
                continue
        commands.append("!")
    elif protocol == "static":
        routes = dev_cfg.get("routes") or calculate_static_routes(name, all_devices, links_config)
        for r in routes or []:
            net = str(r.get("network", "")).strip()
            mask = str(r.get("mask", "")).strip()
            nh = str(r.get("next_hop", "")).strip()
            if net and mask and nh:
                commands.append(f"ip route {net} {mask} {nh}")
        commands.append("!")

    commands.append("end")
    return commands


def generate_switch_config(dev_cfg: dict[str, Any], vlans: list[dict[str, Any]] | None = None) -> list[str]:
    name = str(dev_cfg.get("name", "Switch")).strip() or "Switch"
    commands: list[str] = ["!", f"hostname {name}", "!"]

    vlan_defs: dict[int, str] = {}
    for v in (vlans or []) + (dev_cfg.get("vlans") or []):
        try:
            vid = int(v.get("id", v.get("vlan_id")))
        except Exception:
            continue
        if not (1 <= vid <= 4094):
            continue
        vname = str(v.get("name", f"VLAN_{vid}")).strip() or f"VLAN_{vid}"
        vlan_defs[vid] = vname

    # Ports gathered by entrypoint (best effort)
    access_ports: dict[str, int] = {}
    for port, vid in (dev_cfg.get("access_ports") or {}).items():
        try:
            access_ports[str(port)] = int(vid)
        except Exception:
            continue

    trunk_ports = [str(p) for p in (dev_cfg.get("trunk_ports") or []) if p]

    # Create VLANs
    for vid in sorted(vlan_defs):
        commands.append(f"vlan {vid}")
        commands.append(f" name {vlan_defs[vid]}")
        commands.append("!")

    # Access ports
    for port in sorted(access_ports):
        vid = access_ports[port]
        if vid not in vlan_defs:
            # Still configure it; PT will create VLAN implicitly on some platforms.
            vlan_defs.setdefault(vid, f"VLAN_{vid}")
        commands.append(f"interface {port}")
        commands.append(" switchport mode access")
        commands.append(f" switchport access vlan {vid}")
        commands.append("!")

    # Trunks
    for port in sorted(set(trunk_ports)):
        commands.append(f"interface {port}")
        commands.append(" switchport mode trunk")
        commands.append("!")

    commands.append("end")
    return commands


def generate_server_config(dev_cfg: dict[str, Any]) -> dict[str, Any]:
    services = {str(s).strip().lower() for s in (dev_cfg.get("server_services") or dev_cfg.get("services") or [])}
    return {
        "http": "http" in services,
        "https": "https" in services,
        "dns": "dns" in services,
        "dhcp": "dhcp" in services,
        "ftp": "ftp" in services,
        "smtp": "smtp" in services,
        "pop3": "pop3" in services,
        # Optional service parameters (best-effort defaults).
        "ftp_user": str(dev_cfg.get("ftp_user", "cisco")),
        "ftp_password": str(dev_cfg.get("ftp_password", "cisco")),
        "smtp_domain": str(dev_cfg.get("smtp_domain", dev_cfg.get("email_domain", "")) or "example.com"),
    }
