from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from .server_dhcp import write_dhcp_config
from .server_mail import get_mail_users_and_domain, write_email_config


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
        hostname = _normalize_hostname(raw_cfg.get("hostname"))
        if not hostname:
            if "dns" in services:
                hostname = f"dns{idx+1}.local"
            elif "http" in services or "web" in services:
                hostname = f"web{idx+1}.local"
            elif "ftp" in services:
                hostname = f"ftp{idx+1}.local"
            else:
                hostname = f"server{idx}.local"

        dev["server_services"] = services
        dev["hostname"] = hostname
        if raw_cfg.get("dns_records"):
            dev["dns_records"] = raw_cfg["dns_records"]
        if raw_cfg.get("auto_dns_records"):
            dev["auto_dns_records"] = raw_cfg["auto_dns_records"]
        if raw_cfg.get("ftp_users"):
            dev["ftp_users"] = raw_cfg["ftp_users"]
        if raw_cfg.get("ftp_user"):
            dev["ftp_user"] = raw_cfg["ftp_user"]
        if raw_cfg.get("ftp_password"):
            dev["ftp_password"] = raw_cfg["ftp_password"]
        if raw_cfg.get("mail_users"):
            dev["mail_users"] = raw_cfg["mail_users"]
        if raw_cfg.get("dhcp_pools"):
            dev["dhcp_pools"] = raw_cfg["dhcp_pools"]
        if raw_cfg.get("mail_domain"):
            dev["mail_domain"] = raw_cfg["mail_domain"]

    dns_server: dict | None = None
    for _idx, dev in servers:
        services = {str(s).strip().lower() for s in (dev.get("server_services") or [])}
        if "dns" in services:
            dns_server = dev
            break

    if dns_server is None:
        return
    # Se l'utente ha giÃ  specificato dns_records â†’ rispetta la sua scelta, niente auto-generazione
    if isinstance(dns_server.get("dns_records"), list) and dns_server["dns_records"] and not dns_server.get("auto_dns_records"):
        return
        
    SERVICE_PREFIX = {
        "http": "web", "web": "web", "ftp": "ftp",
        "smtp": "mail", "email": "mail", "ntp": "ntp",
        "syslog": "syslog", "tftp": "tftp",
        "aaa": "aaa", "radius": "radius",
    }
    EXCLUDED = {"dhcp", "dhcpv6", "dns"}

    dns_records: list[dict[str, str]] = []
    counters: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for _idx, dev in servers:
        services = {str(s).strip().lower() for s in (dev.get("server_services") or [])}
        ip = str(dev.get("ip", "")).strip()
        if not ip:
            continue
        for svc in services:
            if svc in EXCLUDED:
                continue
            prefix = SERVICE_PREFIX.get(svc, svc)
            counters[prefix] = counters.get(prefix, 0) + 1
            hostname = f"{prefix}{counters[prefix]}"
            key = (hostname, ip)
            if key in seen:
                continue
            seen.add(key)
            dns_records.append({"hostname": hostname, "ip": ip})

    if dns_records:
        existing = dns_server.get("dns_records") or []
        existing_hostnames = {r.get("hostname") for r in existing if isinstance(r, dict)}
        for r in dns_records:
            if r.get("hostname") not in existing_hostnames:
                existing.append(r)
        dns_server["dns_records"] = existing

def write_dns_records(engine: ET.Element, dev_cfg: dict) -> None:
    """
    Scrive i record DNS nel tag ENGINE/DNS_SERVER/NAMESERVER-DATABASE del server PT.

    Struttura XML attesa da PT 8.2.2:
    <DNS_SERVER>
      <ENABLED>1</ENABLED>
      <NAMESERVER-DATABASE>
        <A_RECORD>
          <DOMAIN_NAME>web.local</DOMAIN_NAME>
          <DETAIL>192.168.1.3</DETAIL>
        </A_RECORD>
      </NAMESERVER-DATABASE>
    </DNS_SERVER>

    dev_cfg["dns_records"] = [{"hostname": "web.local", "ip": "192.168.1.3"}]
    """
    records = dev_cfg.get("dns_records")
    dns = engine.find("DNS_SERVER")
    if dns is None:
        return

    db = dns.find("NAMESERVER-DATABASE")
    if db is None:
        db = ET.SubElement(dns, "NAMESERVER-DATABASE")
    db.clear()

    if not isinstance(records, list) or not records:
        return

    for rec in records:
        if not isinstance(rec, dict):
            continue
        hostname = str(rec.get("hostname") or rec.get("name", "")).strip()
        ip = str(rec.get("ip", "")).strip()
        if not hostname or not ip:
            continue
        rr = ET.SubElement(db, "RESOURCE-RECORD")
        ET.SubElement(rr, "TYPE").text = "A-REC"
        ET.SubElement(rr, "NAME").text = hostname
        ET.SubElement(rr, "TTL").text = "86400"
        ET.SubElement(rr, "IPADDRESS").text = ip

def write_ftp_users(engine: ET.Element, dev_cfg: dict) -> None:
    """
    Scrive utenti FTP nel tag ENGINE/FTP_SERVER/USERS e USER_ACCOUNT_MNGR.
    - Mantiene sempre l'utente default cisco/cisco con tutti i permessi.
    - Utenti custom da dev_cfg["ftp_users"].
    """
    services = {str(s).strip().lower() for s in (dev_cfg.get("server_services") or [])}
    if "ftp" not in services:
        return

    ftp = engine.find("FTP_SERVER")
    if ftp is None:
        return

    enabled = ftp.find("ENABLED")
    if enabled is None:
        enabled = ET.SubElement(ftp, "ENABLED")
    enabled.text = "1"

    users_node = ftp.find("USERS")
    if users_node is None:
        users_node = ET.SubElement(ftp, "USERS")

    # Utente default cisco sempre presente
    default_cisco = {
        "username": "cisco",
        "password": "cisco",
        "read": 1, "write": 1, "delete": 1, "rename": 1, "list": 1,
    }

    users_to_write: list[dict] = [default_cisco]
    custom_users = dev_cfg.get("ftp_users")

    if isinstance(custom_users, list):
        counter = 1
        for u in custom_users:
            if not isinstance(u, dict):
                continue
            username = str(u.get("username") or "").strip()
            if not username:
                username = f"user{counter}"
            counter += 1
            password = str(u.get("password") or "1234").strip()
            perms = str(u.get("permissions") or "rw").strip().lower()
            read   = 1 if "r" in perms else 0
            write  = 1 if "w" in perms else 0
            entry = {
                "username": username,
                "password": password,
                "read":   read,
                "write":  write,
                "delete": write,
                "rename": write,
                "list":   1,
            }
            # Se stesso username di cisco â†’ sovrascrive, altrimenti aggiunge
            users_to_write = [x for x in users_to_write if x["username"] != username]
            users_to_write.append(entry)

    # Scrivi nodo USERS
    users_node.clear()
    for u in users_to_write:
        user_node = ET.SubElement(users_node, "USER")
        ET.SubElement(user_node, "USERNAME").text  = u["username"]
        ET.SubElement(user_node, "PASSWORD").text  = u["password"]
        ET.SubElement(user_node, "WRITE").text     = str(u["write"])
        ET.SubElement(user_node, "READ").text      = str(u["read"])
        ET.SubElement(user_node, "DELETE").text    = str(u["delete"])
        ET.SubElement(user_node, "RENAME").text    = str(u["rename"])
        ET.SubElement(user_node, "LIST").text      = str(u["list"])

    # USER_ACCOUNT_MNGR: usato da PT per mostrare utenti nella GUI
    acct_mgr = ftp.find("USER_ACCOUNT_MNGR")
    if acct_mgr is None:
        acct_mgr = ET.SubElement(ftp, "USER_ACCOUNT_MNGR")
    acct_mgr.clear()
    for u in users_to_write:
        acct = ET.SubElement(acct_mgr, "ACCOUNT")
        ET.SubElement(acct, "USERNAME").text = u["username"]
        ET.SubElement(acct, "PASSWORD").text = u["password"]
        perms_str = ""
        if u["write"]:  perms_str += "W"
        if u["read"]:   perms_str += "R"
        if u["delete"]: perms_str += "D"
        if u["rename"]: perms_str += "N"
        if u["list"]:   perms_str += "L"
        ET.SubElement(acct, "PERMISSIONS").text = perms_str


