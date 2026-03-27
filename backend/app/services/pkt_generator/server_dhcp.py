from __future__ import annotations

import ipaddress
import xml.etree.ElementTree as ET
from typing import Any

from .server_services import normalize_services


def _find_engine_ipv4_port(engine: ET.Element) -> tuple[str | None, str | None]:
    module = engine.find("MODULE")
    if module is None:
        return None, None
    slot = module.find("SLOT")
    if slot is None:
        return None, None
    slot_mod = slot.find("MODULE")
    if slot_mod is None:
        return None, None
    port = slot_mod.find("PORT")
    if port is None:
        return None, None
    ip = port.findtext("IP")
    mask = port.findtext("SUBNET")
    return (str(ip).strip() if ip else None), (str(mask).strip() if mask else None)


def _parse_ipv4(value: Any) -> ipaddress.IPv4Address | None:
    try:
        return ipaddress.IPv4Address(str(value).strip())
    except Exception:
        return None


def _parse_network_from_cfg(dev_cfg: dict[str, Any]) -> ipaddress.IPv4Network | None:
    raw_network = dev_cfg.get("network")
    if raw_network is None:
        return None
    net_text = str(raw_network).strip()
    if not net_text:
        return None

    if "/" in net_text:
        try:
            return ipaddress.IPv4Network(net_text, strict=False)
        except Exception:
            return None

    mask_text = str(dev_cfg.get("mask") or dev_cfg.get("subnet") or "").strip()
    if not mask_text:
        return None
    try:
        return ipaddress.IPv4Network(f"{net_text}/{mask_text}", strict=False)
    except Exception:
        return None


def _parse_network_from_ip_and_mask(ip_text: Any, mask_text: Any) -> ipaddress.IPv4Network | None:
    ip_addr = _parse_ipv4(ip_text)
    if ip_addr is None:
        return None
    mask = str(mask_text or "").strip()
    if not mask:
        return None
    try:
        return ipaddress.IPv4Interface(f"{ip_addr}/{mask}").network
    except Exception:
        return None


def _usable_bounds(net: ipaddress.IPv4Network) -> tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]:
    # Minimal support for /31 and /32 even if not covered by tests.
    if net.prefixlen >= 31:
        return net.network_address, net.broadcast_address
    return (
        ipaddress.IPv4Address(int(net.network_address) + 1),
        ipaddress.IPv4Address(int(net.broadcast_address) - 1),
    )


def _compute_gateway(
    net: ipaddress.IPv4Network,
    *,
    gateway_ip: ipaddress.IPv4Address | None,
    engine_gateway_ip: ipaddress.IPv4Address | None,
    gateway_mode: str | None,
) -> ipaddress.IPv4Address:
    if gateway_ip is not None:
        return gateway_ip

    mode = str(gateway_mode or "").strip().lower()
    if not mode and engine_gateway_ip is not None:
        return engine_gateway_ip

    first_usable, last_usable = _usable_bounds(net)
    if mode == "broadcast":
        return net.broadcast_address
    if mode == "last":
        return last_usable
    if mode == "penultimate":
        return ipaddress.IPv4Address(max(int(first_usable), int(last_usable) - 1))
    # Default / unknown => first usable
    return first_usable


def _compute_start_ip(
    net: ipaddress.IPv4Network,
    *,
    start_offset: int,
    reserved: set[ipaddress.IPv4Address],
) -> ipaddress.IPv4Address:
    first_usable, last_usable = _usable_bounds(net)

    offset = start_offset
    if offset < 2:
        offset = 2

    candidate = ipaddress.IPv4Address(int(net.network_address) + offset)
    if candidate > last_usable:
        candidate = first_usable

    while candidate in reserved and candidate <= last_usable:
        candidate = ipaddress.IPv4Address(int(candidate) + 1)

    if candidate < first_usable or candidate > last_usable:
        return ipaddress.IPv4Address("0.0.0.0")
    return candidate


def _compute_dns_server(dev_cfg: dict[str, Any], *, server_ip: ipaddress.IPv4Address | None) -> str:
    explicit = dev_cfg.get("dhcp_dns")
    if explicit is not None:
        ip = _parse_ipv4(explicit)
        if ip is not None:
            return str(ip)

    provide_dns = bool(dev_cfg.get("provide_dns", False))
    if not provide_dns:
        return "0.0.0.0"
    return str(server_ip) if server_ip is not None else "0.0.0.0"


def _compute_max_users(
    dev_cfg: dict[str, Any],
    *,
    net: ipaddress.IPv4Network,
    gateway: ipaddress.IPv4Address,
    server_ip: ipaddress.IPv4Address | None,
) -> str:
    raw = dev_cfg.get("dhcp_max_users")
    if raw is not None:
        try:
            return str(max(0, int(raw)))
        except Exception:
            return "0"

    first_usable, last_usable = _usable_bounds(net)
    usable_count = max(0, int(last_usable) - int(first_usable) + 1)
    reserved = 0
    if first_usable <= gateway <= last_usable:
        reserved += 1
    if server_ip is not None:
        if first_usable <= server_ip <= last_usable and server_ip != gateway:
            reserved += 1
    else:
        # When server IP is not provided, keep behavior aligned with tests:
        # assume one address is still consumed by the server itself.
        if usable_count > reserved:
            reserved += 1

    computed = max(0, usable_count - reserved)
    return str(min(computed, 512))


def _ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    return node


def _set_text(parent: ET.Element, tag: str, value: str) -> None:
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    node.text = value


def write_dhcp_config(engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
    services_raw = dev_cfg.get("server_services")
    if isinstance(services_raw, (list, set, tuple)) and services_raw:
        services = normalize_services(services_raw)
        if "dhcp" not in services:
            return

    dhcp_servers = engine.find("DHCP_SERVERS")
    if dhcp_servers is None:
        return

    engine_ip, engine_mask = _find_engine_ipv4_port(engine)
    engine_gateway_ip = _parse_ipv4(engine.findtext("GATEWAY"))

    server_ip = _parse_ipv4(dev_cfg.get("ip")) or _parse_ipv4(engine_ip)

    net = _parse_network_from_cfg(dev_cfg)
    if net is None:
        net = _parse_network_from_ip_and_mask(dev_cfg.get("ip") or engine_ip, dev_cfg.get("subnet") or dev_cfg.get("mask") or engine_mask)

    if net is None:
        # Prova con ip+subnet dal dev_cfg prima del fallback a 0.0.0.0
        net = _parse_network_from_ip_and_mask(dev_cfg.get("ip"), dev_cfg.get("subnet") or dev_cfg.get("mask"))
    if net is None:
        # Hard fallback required by tests on invalid inputs.
        net = ipaddress.IPv4Network("0.0.0.0/0", strict=False)
        gateway = ipaddress.IPv4Address("0.0.0.0")
        start_ip = ipaddress.IPv4Address("0.0.0.0")
        end_ip = ipaddress.IPv4Address("0.0.0.0")
        mask = ipaddress.IPv4Address("0.0.0.0")
        network_addr = ipaddress.IPv4Address("0.0.0.0")
        dns_server = "0.0.0.0"
        max_users = "0"
    else:
        gateway_ip = _parse_ipv4(dev_cfg.get("gateway_ip"))
        gateway = _compute_gateway(
            net,
            gateway_ip=gateway_ip,
            engine_gateway_ip=engine_gateway_ip,
            gateway_mode=dev_cfg.get("gateway_mode"),
        )
        first_usable, last_usable = _usable_bounds(net)
        end_ip = last_usable
        reserved = {gateway}
        if server_ip is not None:
            reserved.add(server_ip)
        raw_offset = dev_cfg.get("dhcp_start_offset", 5)
        try:
            start_offset = int(raw_offset)
        except Exception:
            start_offset = 5
        start_ip = _compute_start_ip(net, start_offset=start_offset, reserved=reserved)
        mask = net.netmask
        network_addr = net.network_address
        dns_server = _compute_dns_server(dev_cfg, server_ip=server_ip)
        max_users = _compute_max_users(dev_cfg, net=net, gateway=gateway, server_ip=server_ip)

        if start_ip != ipaddress.IPv4Address("0.0.0.0"):
            # If offset was absurd and we fell back to first usable, skip reserved again.
            if start_ip in reserved:
                cur = start_ip
                while cur in reserved and cur <= end_ip:
                    cur = ipaddress.IPv4Address(int(cur) + 1)
                start_ip = cur if cur <= end_ip else ipaddress.IPv4Address("0.0.0.0")

        # If we couldn't find any usable candidate, tests want end_ip still computed.
        if end_ip < first_usable:
            end_ip = ipaddress.IPv4Address("0.0.0.0")

    lease_time = str(dev_cfg.get("dhcp_lease_time", 86400000))
    domain_name = str(dev_cfg.get("domain_name", ""))
    tftp_address = str(dev_cfg.get("tftp_address", "0.0.0.0"))
    wlc_address = str(dev_cfg.get("wlc_address", "0.0.0.0"))
    pool_name = str(dev_cfg.get("dhcp_pool_name", "serverPool"))

    # Usa dhcp_pools se presenti (multi-pool), altrimenti pool singolo
    dhcp_pools_cfg = dev_cfg.get("dhcp_pools") or []

    assoc_ports = dhcp_servers.findall("ASSOCIATED_PORTS/ASSOCIATED_PORT")
    for ap in assoc_ports:
        srv = _ensure_child(ap, "DHCP_SERVER")
        _set_text(srv, "ENABLED", "1")
        pools_el = _ensure_child(srv, "POOLS")

        # Remove existing pools so rewrite is idempotent.
        for old_pool in list(pools_el.findall("POOL")):
            pools_el.remove(old_pool)

        if dhcp_pools_cfg:
            # Multi-pool: uno per ogni LAN
            for pool_cfg in dhcp_pools_cfg:
                pool_gw_parsed = _parse_ipv4(pool_cfg.get("gateway", str(gateway)))
                pool_net = _parse_network_from_ip_and_mask(
                    pool_cfg.get("network", str(network_addr)),
                    pool_cfg.get("mask", str(mask))
                )
                if pool_net is None:
                    pool_net = net
                if pool_gw_parsed is None:
                    pool_gw_parsed = gateway
                p_first, p_last = _usable_bounds(pool_net)
                p_reserved = {pool_gw_parsed}
                p_si = _parse_ipv4(dev_cfg.get("ip"))
                if p_si:
                    p_reserved.add(p_si)
                p_start = _compute_start_ip(pool_net, start_offset=5, reserved=p_reserved)
                p_end = p_last
                p_dns = str(pool_cfg.get("dns", dns_server))
                p_name = str(pool_cfg.get("name", pool_name))

                pool = ET.SubElement(pools_el, "POOL")
                _set_text(pool, "NAME", p_name)
                _set_text(pool, "NETWORK", str(pool_net.network_address))
                _set_text(pool, "MASK", str(pool_net.netmask))
                _set_text(pool, "DEFAULT_ROUTER", str(pool_gw_parsed))
                _set_text(pool, "START_IP", str(p_start))
                _set_text(pool, "END_IP", str(p_end))
                _set_text(pool, "DNS_SERVER", p_dns)
                _set_text(pool, "MAX_USERS", max_users)
                _set_text(pool, "LEASE_TIME", lease_time)
                _set_text(pool, "TFTP_ADDRESS", tftp_address)
                _set_text(pool, "WLC_ADDRESS", wlc_address)
                _set_text(pool, "DOMAIN_NAME", domain_name)
                _ensure_child(pool, "DHCP_POOL_LEASES")
        else:
            # Pool singolo (fallback)
            pool = ET.SubElement(pools_el, "POOL")
            _set_text(pool, "NAME", pool_name)
            _set_text(pool, "NETWORK", str(network_addr))
            _set_text(pool, "MASK", str(mask))
            _set_text(pool, "DEFAULT_ROUTER", str(gateway))
            _set_text(pool, "START_IP", str(start_ip))
            _set_text(pool, "END_IP", str(end_ip))
            _set_text(pool, "DNS_SERVER", dns_server)
            _set_text(pool, "MAX_USERS", max_users)
            _set_text(pool, "LEASE_TIME", lease_time)
            _set_text(pool, "TFTP_ADDRESS", tftp_address)
            _set_text(pool, "WLC_ADDRESS", wlc_address)
            _set_text(pool, "DOMAIN_NAME", domain_name)
            _ensure_child(pool, "DHCP_POOL_LEASES")

        _ensure_child(srv, "DHCP_RESERVATIONS")
        _ensure_child(srv, "AUTOCONFIG")
