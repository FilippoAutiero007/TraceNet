from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


_SERVER_NAME_RE = re.compile(r"^Server(\d+)$", re.IGNORECASE)


def _normalize_services(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        s = str(item or "").strip().lower()
        if s:
            out.append(s)
    return out


def _normalize_hostname(value: Any) -> str:
    return str(value or "").strip()


def build_server_configs(
    num_servers: int,
    servers_config_list: list[dict],
    server_services_global: list[str],
    devices_config: list[dict],
) -> None:
    """
    Aggiorna devices_config in-place aggiungendo:
    - server_services specifici per ogni server
    - hostname per ogni server
    - dns_records nel server DNS (record A per tutti i server HTTP)
    """
    global_services = _normalize_services(server_services_global)

    servers: list[tuple[int, dict]] = []
    for dev in devices_config:
        if str(dev.get("type", "")).lower() != "server":
            continue
        name = str(dev.get("name", "")).strip()
        match = _SERVER_NAME_RE.match(name)
        if not match:
            continue
        try:
            idx = int(match.group(1))
        except Exception:
            continue
        servers.append((idx, dev))

    servers.sort(key=lambda item: item[0])
    servers = [s for s in servers if 0 <= s[0] < int(num_servers)]

    for idx, dev in servers:
        raw_cfg = servers_config_list[idx] if idx < len(servers_config_list) and isinstance(servers_config_list[idx], dict) else {}
        services = _normalize_services(raw_cfg.get("services"))
        if not services:
            services = global_services
        hostname = _normalize_hostname(raw_cfg.get("hostname")) or f"server{idx}.local"

        dev["server_services"] = services
        dev["hostname"] = hostname

    dns_server: dict | None = None
    for _idx, dev in servers:
        services = {str(s).strip().lower() for s in (dev.get("server_services") or [])}
        if "dns" in services:
            dns_server = dev
            break

    if dns_server is None:
        return

    dns_records: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _idx, dev in servers:
        services = {str(s).strip().lower() for s in (dev.get("server_services") or [])}
        if "http" not in services:
            continue
        hostname = str(dev.get("hostname", "")).strip()
        ip = str(dev.get("ip", "")).strip()
        if not hostname or not ip:
            continue
        key = (hostname, ip)
        if key in seen:
            continue
        seen.add(key)
        dns_records.append({"hostname": hostname, "ip": ip})

    dns_server["dns_records"] = dns_records


def write_dns_records(engine: ET.Element, dev_cfg: dict) -> None:
    """
    Scrive i record DNS nel tag ENGINE/DNS_SERVER/NAMESERVER-DATABASE del server PT.

    Struttura XML corretta (verificata da PT 8.2.2):
    <DNS_SERVER>
      <ENABLED>1</ENABLED>
      <NAMESERVER-DATABASE>
        <RESOURCE-RECORD>
          <TYPE>A-REC</TYPE>
          <NAME>web</NAME>
          <TTL>86400</TTL>
          <IPADDRESS>192.168.1.3</IPADDRESS>
        </RESOURCE-RECORD>
      </NAMESERVER-DATABASE>
    </DNS_SERVER>

    dev_cfg["dns_records"] = [{"hostname": "web.local", "ip": "192.168.1.3"}]
    """
    records = dev_cfg.get("dns_records")
    if not isinstance(records, list):
        return

    dns = engine.find("DNS_SERVER")
    if dns is None:
        return

    db = dns.find("NAMESERVER-DATABASE")
    if db is None:
        db = ET.SubElement(dns, "NAMESERVER-DATABASE")
    db.clear()

    for rec in records:
        if not isinstance(rec, dict):
            continue
        hostname = str(rec.get("hostname", "")).strip()
        ip = str(rec.get("ip", "")).strip()
        if not hostname or not ip:
            continue
        # PT usa solo il nome host senza dominio (es. "web" non "web.local")
        name = hostname.split(".")[0] if "." in hostname else hostname

        rr = ET.SubElement(db, "RESOURCE-RECORD")
        ET.SubElement(rr, "TYPE").text = "A-REC"
        ET.SubElement(rr, "NAME").text = name
        ET.SubElement(rr, "TTL").text = "86400"
        ET.SubElement(rr, "IPADDRESS").text = ip


