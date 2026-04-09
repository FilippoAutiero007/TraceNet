from __future__ import annotations

import ipaddress
from collections import defaultdict
from typing import Any


def build_lan_segments(subnets: list[Any], dhcp_dns: Any) -> list[dict[str, Any]]:
    lan_segments: list[dict[str, Any]] = []
    for subnet in subnets:
        usable_range = getattr(subnet, "usable_range", None)
        if not isinstance(usable_range, list) or len(usable_range) != 2:
            continue
        try:
            start_ip = ipaddress.ip_address(str(usable_range[0]))
            end_ip = ipaddress.ip_address(str(usable_range[1]))
        except ValueError:
            continue

        mask = str(getattr(subnet, "mask", "255.255.255.0"))
        gateway = getattr(subnet, "gateway", None)
        try:
            gw_ip = ipaddress.ip_address(str(gateway)) if gateway else start_ip
        except ValueError:
            gw_ip = start_ip

        lan_segments.append(
            {
                "name": str(getattr(subnet, "name", "")),
                "network": str(getattr(subnet, "network", "")),
                "mask": mask,
                "gateway": str(gw_ip),
                "dns_server": dhcp_dns if dhcp_dns else getattr(subnet, "dns_server", None),
                "start_ip": start_ip,
                "end_ip": end_ip,
                "next_ip": start_ip,
            }
        )
    return lan_segments


def normalize_vlans(vlans: list[Any]) -> list[dict[str, Any]]:
    vlan_sequence: list[dict[str, Any]] = []
    for vlan in vlans:
        if not isinstance(vlan, dict):
            continue
        try:
            vlan_id = int(vlan.get("id", vlan.get("vlan_id")))
        except Exception:
            continue
        if not (1 <= vlan_id <= 4094):
            continue
        vlan_entry = dict(vlan)
        vlan_entry["id"] = vlan_id
        vlan_sequence.append(vlan_entry)
    return vlan_sequence


def map_segments_to_vlans(
    lan_segments: list[dict[str, Any]],
    vlan_sequence: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    segment_by_vlan_id: dict[int, dict[str, Any]] = {}
    if not vlan_sequence:
        return segment_by_vlan_id

    for idx, seg in enumerate(lan_segments):
        vlan = vlan_sequence[idx % len(vlan_sequence)]
        seg["vlan_id"] = vlan["id"]
        seg["vlan_name"] = str(vlan.get("name") or f"VLAN_{vlan['id']}")
        segment_by_vlan_id[vlan["id"]] = seg
    return segment_by_vlan_id


def is_router_on_a_stick(
    vlan_sequence: list[dict[str, Any]],
    *,
    num_switches: int,
    lan_segments: list[dict[str, Any]],
    num_routers: int,
) -> bool:
    return bool(vlan_sequence) and num_switches == 1 and len(lan_segments) > 1 and num_routers > 0


def build_switch_segment_maps(
    switches_config: list[dict[str, Any]],
    lan_segments: list[dict[str, Any]],
    *,
    router_on_a_stick: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    switch_to_lan: dict[str, dict[str, Any]] = {}
    switch_to_segments: dict[str, list[dict[str, Any]]] = {}
    if not lan_segments:
        return switch_to_lan, switch_to_segments

    for sw in switches_config:
        switch_name = str(sw.get("name", ""))
        if router_on_a_stick:
            switch_to_segments[switch_name] = list(lan_segments)
            switch_to_lan[switch_name] = lan_segments[0]
            continue
        seg = lan_segments[_switch_index(switch_name) % len(lan_segments)]
        switch_to_lan[switch_name] = seg
        switch_to_segments[switch_name] = [seg]
    return switch_to_lan, switch_to_segments


def upsert_router_interface(
    router_cfg: dict[str, Any],
    if_name: str,
    *,
    ip: str,
    mask: str,
    role: str,
    dns_server: str | None = None,
    **extra: Any,
) -> None:
    interfaces = router_cfg.setdefault("interfaces", [])
    iface_ip = router_cfg.setdefault("interface_ips", {})
    iface_ip[str(if_name)] = str(ip)

    payload = {"name": str(if_name), "ip": str(ip), "mask": str(mask), "role": role, **extra}
    if dns_server is not None:
        payload["dns_server"] = str(dns_server)

    for entry in interfaces:
        if str(entry.get("name", "")) == if_name:
            entry.update(payload)
            break
    else:
        interfaces.append(payload)

    if role == "lan" and not router_cfg.get("ip"):
        router_cfg["ip"] = str(ip)
        router_cfg["subnet"] = str(mask)
        router_cfg["gateway_ip"] = str(ip)


def assign_router_lan_interfaces(
    links_config: list[dict[str, Any]],
    routers_config: list[dict[str, Any]],
    switch_to_lan: dict[str, dict[str, Any]],
    switch_to_segments: dict[str, list[dict[str, Any]]],
    *,
    router_on_a_stick: bool,
) -> None:
    for link in links_config:
        frm = str(link.get("from", ""))
        to = str(link.get("to", ""))
        if not (frm.startswith("Router") and to.startswith("Switch")):
            continue

        router_port = str(link.get("from_port", "")).strip()
        if not router_port:
            continue

        seg = switch_to_lan.get(to)
        segments = switch_to_segments.get(to) or ([seg] if seg is not None else [])
        if not segments:
            continue

        router_cfg = next((r for r in routers_config if r["name"] == frm), None)
        if router_cfg is None:
            continue

        if router_on_a_stick:
            for current_seg in segments:
                vlan_id = current_seg.get("vlan_id")
                if vlan_id is None:
                    continue
                upsert_router_interface(
                    router_cfg,
                    f"{router_port}.{vlan_id}",
                    ip=current_seg["gateway"],
                    mask=current_seg["mask"],
                    role="lan",
                    dns_server=current_seg.get("dns_server"),
                    encapsulation=f"dot1Q {vlan_id}",
                    vlan_id=vlan_id,
                )
            continue

        upsert_router_interface(
            router_cfg,
            router_port,
            ip=seg["gateway"],
            mask=seg["mask"],
            role="lan",
            dns_server=seg.get("dns_server"),
        )


def assign_router_wan_interfaces(
    links_config: list[dict[str, Any]],
    routers_config: list[dict[str, Any]],
    *,
    wan_network_str: str,
    wan_prefix: int,
) -> int:
    try:
        wan_base = ipaddress.ip_network(f"{wan_network_str}/{wan_prefix}", strict=False)
        block_size = 2 ** (32 - wan_prefix)
    except Exception:
        wan_base = ipaddress.ip_network("11.0.0.0/30", strict=False)
        block_size = 4
        wan_prefix = 30

    rr_links = [
        link
        for link in links_config
        if str(link.get("from", "")).startswith("Router") and str(link.get("to", "")).startswith("Router")
    ]

    for idx, link in enumerate(rr_links):
        net_addr = int(wan_base.network_address) + (idx * block_size)
        try:
            net = ipaddress.IPv4Network((ipaddress.IPv4Address(net_addr), wan_prefix), strict=False)
        except Exception:
            break

        from_router = str(link.get("from"))
        to_router = str(link.get("to"))
        from_port = str(link.get("from_port", "")).strip()
        to_port = str(link.get("to_port", "")).strip()
        if not from_port or not to_port:
            continue

        ip1 = str(ipaddress.IPv4Address(int(net.network_address) + 1))
        ip2 = str(ipaddress.IPv4Address(int(net.network_address) + 2))
        mask = str(net.netmask)
        r1 = next((r for r in routers_config if r["name"] == from_router), None)
        r2 = next((r for r in routers_config if r["name"] == to_router), None)
        if r1:
            upsert_router_interface(r1, from_port, ip=ip1, mask=mask, role="wan")
        if r2:
            upsert_router_interface(r2, to_port, ip=ip2, mask=mask, role="wan")

    return wan_prefix


def attach_acl_to_router_interfaces(
    routers_config: list[dict[str, Any]],
    acl_global: list[dict[str, Any]],
) -> None:
    for router_cfg in routers_config:
        interfaces = router_cfg.get("interfaces") or []
        for acl in acl_global:
            if not isinstance(acl, dict):
                continue

            apply_to_interface = str(acl.get("apply_to_interface", "")).strip()
            raw_vlan = acl.get("apply_to_vlan", acl.get("vlan_id"))
            try:
                apply_to_vlan = int(raw_vlan) if raw_vlan is not None else None
            except Exception:
                apply_to_vlan = None

            acl_ref: dict[str, Any] = {"direction": str(acl.get("direction", "in")).strip().lower() or "in"}
            if acl.get("id"):
                acl_ref["id"] = str(acl["id"]).strip()
            elif acl.get("name"):
                acl_ref["name"] = str(acl["name"]).strip()
            else:
                continue

            for iface in interfaces:
                iface_name = str(iface.get("name", "")).strip()
                iface_vlan = iface.get("vlan_id")
                if apply_to_interface and iface_name == apply_to_interface:
                    iface["acl"] = acl_ref
                    break
                if apply_to_vlan is not None and iface_vlan == apply_to_vlan:
                    iface["acl"] = acl_ref
                    break


def collect_host_switch_links(
    links_config: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    link_to_switch: dict[str, str] = {}
    link_to_switch_port: dict[str, str] = {}
    for link in links_config:
        frm = str(link.get("from", ""))
        to = str(link.get("to", ""))
        if frm.startswith("Switch") and (to.startswith("PC") or to.startswith("Server")):
            link_to_switch[to] = frm
            link_to_switch_port[to] = str(link.get("from_port", "")).strip()
    return link_to_switch, link_to_switch_port


def default_vlan_id(vlans_global: list[Any]) -> int | None:
    for vlan in vlans_global:
        try:
            return int(vlan.get("id", vlan.get("vlan_id")))
        except Exception:
            continue
    return None


def alloc_ip(seg: dict[str, Any]) -> str | None:
    nxt = seg.get("next_ip")
    if not isinstance(nxt, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
        return None
    if int(nxt) > int(seg["end_ip"]):
        return None
    seg["next_ip"] = ipaddress.ip_address(int(nxt) + 1)
    return str(nxt)


def segment_for_host(
    switch_name: str | None,
    *,
    explicit_cfg: dict[str, Any] | None,
    fallback_index: int,
    switch_to_segments: dict[str, list[dict[str, Any]]],
    lan_segments: list[dict[str, Any]],
    segment_by_vlan_id: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    explicit_cfg = explicit_cfg or {}
    if switch_name and switch_name in switch_to_segments:
        segments = switch_to_segments[switch_name]
    else:
        segments = lan_segments
    if not segments:
        return None

    raw_vlan = explicit_cfg.get("vlan_id")
    if raw_vlan is not None:
        try:
            vlan_id = int(raw_vlan)
        except Exception:
            vlan_id = None
        if vlan_id is not None and vlan_id in segment_by_vlan_id:
            return segment_by_vlan_id[vlan_id]

    return segments[fallback_index % len(segments)]


def apply_switch_port_roles(
    switches_config: list[dict[str, Any]],
    link_to_switch: dict[str, str],
    link_to_switch_port: dict[str, str],
    devices_config: list[dict[str, Any]],
    links_config: list[dict[str, Any]],
    *,
    vlans_global: list[Any],
    vlan_sequence: list[dict[str, Any]],
    default_vlan: int | None,
) -> None:
    switches_by_name = {sw["name"]: sw for sw in switches_config}
    for host_name, sw_name in link_to_switch.items():
        sw = switches_by_name.get(sw_name)
        if sw is None:
            continue
        port = link_to_switch_port.get(host_name) or ""
        if not port:
            continue
        vlan_id = None
        host = next((device for device in devices_config if device.get("name") == host_name), None)
        if host is not None and host.get("vlan_id") is not None:
            try:
                vlan_id = int(host["vlan_id"])
            except Exception:
                vlan_id = None
        if vlan_id is None and default_vlan is not None:
            vlan_id = default_vlan
        if vlan_id is not None:
            sw.setdefault("access_ports", {})[port] = vlan_id

    if not vlans_global:
        return

    for link in links_config:
        frm = str(link.get("from", ""))
        to = str(link.get("to", ""))
        if frm.startswith("Switch") and to.startswith("Router"):
            sw = switches_by_name.get(frm)
            if sw:
                sw.setdefault("trunk_ports", []).append(str(link.get("from_port", "")).strip() or "FastEthernet0/1")
        if frm.startswith("Router") and to.startswith("Switch"):
            sw = switches_by_name.get(to)
            if sw:
                sw.setdefault("trunk_ports", []).append(str(link.get("to_port", "")).strip() or "FastEthernet0/1")
        if frm.startswith("Switch") and to.startswith("Switch"):
            sw1 = switches_by_name.get(frm)
            sw2 = switches_by_name.get(to)
            if sw1:
                sw1.setdefault("trunk_ports", []).append(str(link.get("from_port", "")).strip())
            if sw2:
                sw2.setdefault("trunk_ports", []).append(str(link.get("to_port", "")).strip())

    allowed_vlans = [vlan["id"] for vlan in vlan_sequence]
    for sw in switches_config:
        if allowed_vlans:
            sw["trunk_allowed_vlans"] = allowed_vlans


def build_mail_server_index(
    devices_config: list[dict[str, Any]],
    link_to_switch: dict[str, str],
    normalize_services: Any,
) -> dict[tuple[str, int | None], dict[str, Any]]:
    mail_server_index: dict[tuple[str, int | None], dict[str, Any]] = {}
    for dev in devices_config:
        if str(dev.get("type", "")).lower() != "server":
            continue
        services = normalize_services(dev.get("server_services"))
        if not {"smtp", "pop3", "email"}.intersection(services):
            continue
        server_name = str(dev.get("name", ""))
        switch_name = link_to_switch.get(server_name)
        if not switch_name or not str(dev.get("ip", "")).strip():
            continue
        raw_vlan = dev.get("vlan_id")
        try:
            vlan_id = int(raw_vlan) if raw_vlan is not None else None
        except Exception:
            vlan_id = None
        mail_server_index.setdefault((switch_name, vlan_id), dev)
        mail_server_index.setdefault((switch_name, None), dev)
    return mail_server_index


def resolve_mail_server(
    mail_server_index: dict[tuple[str, int | None], dict[str, Any]],
    *,
    switch_name: str | None,
    vlan_id: int | None,
) -> dict[str, Any] | None:
    if not switch_name:
        return None
    return mail_server_index.get((switch_name, vlan_id)) or mail_server_index.get((switch_name, None))


def init_mail_user_counters() -> dict[str, int]:
    return defaultdict(int)


def _switch_index(switch_name: str) -> int:
    if switch_name.startswith("Switch"):
        try:
            return int(switch_name.replace("Switch", ""))
        except ValueError:
            return 0
    return 0
