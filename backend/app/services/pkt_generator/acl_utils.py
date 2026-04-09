from __future__ import annotations

import ipaddress
from typing import Any


def mask_to_wildcard(mask: str) -> str:
    mask_ip = ipaddress.IPv4Address(str(mask).strip())
    wildcard_int = int(ipaddress.IPv4Address("255.255.255.255")) - int(mask_ip)
    return str(ipaddress.IPv4Address(wildcard_int))


def render_acl_endpoint(rule: dict[str, Any], prefix: str) -> str:
    any_key = f"{prefix}_any"
    host_key = f"{prefix}_host"
    net_key = f"{prefix}_network"
    wildcard_key = f"{prefix}_wildcard"
    mask_key = f"{prefix}_mask"
    fallback_key = "source" if prefix == "src" else "destination"
    value = str(rule.get(prefix, rule.get(fallback_key, "any"))).strip()

    if bool(rule.get(any_key)):
        return "any"

    host = str(rule.get(host_key, "")).strip()
    if host:
        return f"host {host}"

    network = str(rule.get(net_key, value)).strip() or "any"
    if network.lower() == "any":
        return "any"
    if network.lower().startswith("host "):
        return network

    wildcard = str(rule.get(wildcard_key, "")).strip()
    if not wildcard:
        mask = str(rule.get(mask_key, rule.get("mask", ""))).strip()
        if mask:
            try:
                wildcard = mask_to_wildcard(mask)
            except Exception:
                wildcard = ""

    if wildcard:
        return f"{network} {wildcard}"
    return network


def render_acl_port(rule: dict[str, Any], prefix: str = "dst") -> str:
    operator = str(rule.get(f"{prefix}_port_op", rule.get("port_op", "eq"))).strip().lower()
    port = rule.get(f"{prefix}_port", rule.get("dport", rule.get("dest_port")))
    if prefix == "src":
        port = rule.get(f"{prefix}_port", rule.get("sport", rule.get("source_port")))
    if port in (None, ""):
        return ""
    if isinstance(port, (list, tuple)) and len(port) == 2:
        return f" range {port[0]} {port[1]}"

    port_text = str(port).strip()
    if not port_text:
        return ""
    if operator not in {"eq", "neq", "lt", "gt", "range"}:
        operator = "eq"
    if operator == "range":
        parts = [p for p in port_text.replace(",", " ").split() if p]
        if len(parts) >= 2:
            return f" range {parts[0]} {parts[1]}"
        return ""
    return f" {operator} {port_text}"
