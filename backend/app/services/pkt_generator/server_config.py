from __future__ import annotations

import ipaddress
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

_SERVER_NAME_RE = re.compile(r"^Server(\d+)$", re.IGNORECASE)
logger = logging.getLogger(__name__)


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
        raw_cfg = (
            servers_config_list[idx]
            if idx < len(servers_config_list)
            and isinstance(servers_config_list[idx], dict)
            else {}
        )
        services = _normalize_services(raw_cfg.get("services"))
        if not services:
            services = global_services
        hostname = _normalize_hostname(raw_cfg.get("hostname")) or f"server{idx}.local"

        dev["server_services"] = services
        dev["hostname"] = hostname
        if raw_cfg.get("ftp_users"):
            dev["ftp_users"] = raw_cfg["ftp_users"]

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

    # FIX: guard esplicito invece di assegnazione diretta su tipo potenzialmente None
    if dns_server is not None:
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
        logging.getLogger("tracenet").warning("Processing DNS record: hostname=%s, ip=%s", hostname, ip)
        name = hostname.split(".")[0] if "." in hostname else hostname

        rr = ET.SubElement(db, "RESOURCE-RECORD")
        ET.SubElement(rr, "TYPE").text = "A-REC"
        ET.SubElement(rr, "NAME").text = name
        ET.SubElement(rr, "TTL").text = "86400"
        ET.SubElement(rr, "IPADDRESS").text = ip


def write_dhcp_config(engine: ET.Element, dev_cfg: dict) -> None:
    """
    Configura DHCP su ENGINE/DHCP_SERVERS in modo dinamico per qualsiasi subnet.

    Esempio 1 — /24 classe C, gateway_mode="first", offset=5, no DNS
    dev_cfg = {
        "network": "192.168.0.0/24",
        "ip": "192.168.0.2",
        "dhcp_start_offset": 5,
        "provide_dns": False,
    }
    XML atteso:
      NETWORK=192.168.0.0, MASK=255.255.255.0, DEFAULT_ROUTER=192.168.0.1,
      START_IP=192.168.0.6, END_IP=192.168.0.254, DNS_SERVER=0.0.0.0

    Esempio 2 — /16 classe B, gateway esplicito, offset=2, DNS dal server stesso
    dev_cfg = {
        "network": "172.16.0.0/16",
        "gateway_ip": "172.16.0.1",
        "ip": "172.16.0.2",
        "provide_dns": True,
        "dhcp_start_offset": 2,
    }
    XML atteso:
      NETWORK=172.16.0.0, MASK=255.255.0.0, DEFAULT_ROUTER=172.16.0.1,
      START_IP=172.16.0.3, END_IP=172.16.255.254, DNS_SERVER=172.16.0.2

    Esempio 3 — /28 classe C piccola, gateway_mode="last", offset=2, DNS esterno
    dev_cfg = {
        "network": "192.168.1.0/28",
        "gateway_mode": "last",
        "ip": "192.168.1.2",
        "dhcp_dns": "8.8.8.8",
        "dhcp_start_offset": 2,
    }
    XML atteso:
      NETWORK=192.168.1.0, MASK=255.255.255.240, DEFAULT_ROUTER=192.168.1.14,
      START_IP=192.168.1.3, END_IP=192.168.1.14, DNS_SERVER=8.8.8.8
    """
    dhcp_servers = engine.find("DHCP_SERVERS")
    if dhcp_servers is None:
        return

    # Leggi pool secondario opzionale da dev_cfg
    primary_pool: dict[str, Any] = {}
    raw_pools = dev_cfg.get("dhcp_pools")
    if isinstance(raw_pools, list):
        for pool_item in raw_pools:
            if isinstance(pool_item, dict):
                primary_pool = pool_item
                break

    # Leggi IP/mask dall'interfaccia ENGINE come ultimo fallback
    engine_port_ip: str = ""
    engine_port_mask: str = ""
    engine_gateway: str = ""
    port = engine.find("MODULE/SLOT/MODULE/PORT")
    if port is not None:
        engine_port_ip = str(port.findtext("IP") or "").strip()
        engine_port_mask = str(port.findtext("SUBNET") or "").strip()
    engine_gateway = str(engine.findtext("GATEWAY") or "").strip()

    # Parametri rete con priorità esplicita
    network_src: str = str(
        dev_cfg.get("network") or primary_pool.get("network") or ""
    ).strip()
    mask_src: str = str(
        dev_cfg.get("mask")
        or dev_cfg.get("subnet")
        or primary_pool.get("mask")
        or engine_port_mask
        or ""
    ).strip()
    gateway_raw: str = str(
        dev_cfg.get("gateway_ip")
        or dev_cfg.get("gateway")
        or primary_pool.get("gateway")
        or primary_pool.get("default_router")
        or engine_gateway
        or ""
    ).strip()
    gateway_mode: str = str(dev_cfg.get("gateway_mode", "first")).strip().lower() or "first"
    server_ip_raw: str = str(dev_cfg.get("ip") or engine_port_ip or "").strip()
    dns_from_cfg: str = str(
        dev_cfg.get("dhcp_dns") or primary_pool.get("dns") or ""
    ).strip()
    provide_dns: bool = bool(dev_cfg.get("provide_dns", False))

    # Calcolo indirizzi
    network_addr: str = "0.0.0.0"
    mask: str = "0.0.0.0"
    gateway_ip: str = "0.0.0.0"
    start_ip: str = "0.0.0.0"
    end_ip: str = "0.0.0.0"
    num_hosts: int = 0
    server_ip: str = ""

    try:
        if server_ip_raw:
            server_ip = str(ipaddress.IPv4Address(server_ip_raw))

        # Costruisci oggetto network
        net: ipaddress.IPv4Network
        if network_src:
            if "/" not in network_src and mask_src:
                net = ipaddress.IPv4Network(f"{network_src}/{mask_src}", strict=False)
            else:
                net = ipaddress.IPv4Network(network_src, strict=False)
        elif mask_src:
            base_ip = server_ip_raw or gateway_raw or "0.0.0.0"
            if not (server_ip_raw or gateway_raw):
                logger.warning(
                    "DHCP network mancante: derivo da mask/subnet con base 0.0.0.0."
                )
            net = ipaddress.IPv4Network(f"{base_ip}/{mask_src}", strict=False)
        else:
            logger.warning("DHCP network/mask/subnet mancanti. Uso 0.0.0.0/0.")
            net = ipaddress.IPv4Network("0.0.0.0/0", strict=False)

        network_addr = str(net.network_address)
        mask = str(net.netmask)
        num_hosts = max(0, net.num_addresses - 2) if net.num_addresses >= 2 else 0

        # Calcola interi degli host limite
        first_host_int: int | None = None
        last_host_int: int | None = None
        penultimate_host_int: int | None = None
        if num_hosts > 0:
            first_host_int = int(net.network_address) + 1
            last_host_int = int(net.broadcast_address) - 1
            penultimate_host_int = last_host_int - 1 if num_hosts > 1 else last_host_int

        # Calcola gateway
        if gateway_raw:
            gateway_ip = str(ipaddress.IPv4Address(gateway_raw))
        else:
            if gateway_mode == "broadcast":
                gateway_ip = str(net.broadcast_address)
            elif gateway_mode == "last":
                gateway_ip = (
                    str(ipaddress.IPv4Address(last_host_int))
                    if last_host_int is not None
                    else "0.0.0.0"
                )
            elif gateway_mode == "penultimate":
                gateway_ip = (
                    str(ipaddress.IPv4Address(penultimate_host_int))
                    if penultimate_host_int is not None
                    else "0.0.0.0"
                )
            else:  # "first" (default)
                gateway_ip = (
                    str(ipaddress.IPv4Address(first_host_int))
                    if first_host_int is not None
                    else "0.0.0.0"
                )

        # Calcola END_IP
        end_ip = (
            str(ipaddress.IPv4Address(last_host_int))
            if last_host_int is not None
            else "0.0.0.0"
        )

        # Calcola START_IP con offset configurabile
        offset_raw = dev_cfg.get("dhcp_start_offset", 5)
        try:
            start_offset: int = int(offset_raw)
        except Exception:
            start_offset = 5
        if start_offset < 2:
            start_offset = 2

        # FIX: annotazione esplicita per evitare errore Pyre2 su tipo None
        safe_last_host_int: int = (
            last_host_int if last_host_int is not None else int(net.network_address)
        )

        broadcast_str = str(net.broadcast_address)
        network_str = str(net.network_address)

        # FIX: annotazione esplicita int per evitare errore Pyre2 su +=
        candidate_int: int = int(net.network_address) + start_offset
        while candidate_int <= safe_last_host_int:
            candidate = str(ipaddress.IPv4Address(candidate_int))
            if (
                candidate != gateway_ip
                and candidate != server_ip
                and candidate != network_str
                and candidate != broadcast_str
            ):
                start_ip = candidate
                break
            candidate_int += 1

        # Fallback: se offset troppo alto, prendi il primo host disponibile
        if start_ip == "0.0.0.0" and first_host_int is not None:
            fallback_int: int = first_host_int
            attempts = 0
            while fallback_int <= safe_last_host_int and attempts < 256:
                candidate = str(ipaddress.IPv4Address(fallback_int))
                if (
                    candidate != gateway_ip
                    and candidate != server_ip
                    and candidate != network_str
                    and candidate != broadcast_str
                ):
                    start_ip = candidate
                    break
                fallback_int += 1
                attempts += 1

    except Exception as exc:
        logger.warning(
            "DHCP IP calc fallito (network=%r, mask=%r, subnet=%r, "
            "gateway_ip=%r, gateway=%r, server_ip=%r): %s. Uso fallback 0.0.0.0.",
            dev_cfg.get("network"),
            dev_cfg.get("mask"),
            dev_cfg.get("subnet"),
            dev_cfg.get("gateway_ip"),
            dev_cfg.get("gateway"),
            dev_cfg.get("ip"),
            exc,
        )
        network_addr = "0.0.0.0"
        mask = "0.0.0.0"
        gateway_ip = "0.0.0.0"
        start_ip = "0.0.0.0"
        end_ip = "0.0.0.0"
        num_hosts = 0
        server_ip = ""

    # DNS: valorizzato solo se esplicitamente richiesto
    dns_ip = "0.0.0.0"
    if dns_from_cfg:
        try:
            dns_ip = str(ipaddress.IPv4Address(dns_from_cfg))
        except Exception as exc:
            logger.warning(
                "dhcp_dns non valido '%s': %s. Uso 0.0.0.0.", dns_from_cfg, exc
            )
            dns_ip = "0.0.0.0"
    elif provide_dns and server_ip:
        dns_ip = server_ip

    # MAX_USERS
    max_users_cfg = dev_cfg.get("dhcp_max_users")
    if max_users_cfg is None:
        max_users: int = max(0, min(512, num_hosts - 2))
    else:
        try:
            max_users = max(0, int(max_users_cfg))
        except Exception:
            logger.warning(
                "dhcp_max_users non valido '%s'. Uso default dinamico.", max_users_cfg
            )
            max_users = max(0, min(512, num_hosts - 2))

    # LEASE_TIME
    lease_cfg = dev_cfg.get("dhcp_lease_time", 86400000)
    try:
        lease_time: int = max(0, int(lease_cfg))
    except Exception:
        logger.warning(
            "dhcp_lease_time non valido '%s'. Uso 86400000.", lease_cfg
        )
        lease_time = 86400000

    tftp_address: str = str(dev_cfg.get("tftp_address", "0.0.0.0")).strip() or "0.0.0.0"
    wlc_address: str = str(dev_cfg.get("wlc_address", "0.0.0.0")).strip() or "0.0.0.0"
    domain_name: str = str(dev_cfg.get("domain_name", "")).strip()

    def _st(pool_elem: ET.Element, tag: str, val: Any) -> None:
        """Crea o aggiorna un tag nel pool DHCP (idempotente)."""
        elem = pool_elem.find(tag)
        if elem is None:
            elem = ET.SubElement(pool_elem, tag)
        elem.text = str(val)

    for ap in dhcp_servers.findall("ASSOCIATED_PORTS/ASSOCIATED_PORT"):
        dhcp_server = ap.find("DHCP_SERVER")
        if dhcp_server is None:
            dhcp_server = ET.SubElement(ap, "DHCP_SERVER")

        enabled = dhcp_server.find("ENABLED")
        if enabled is None:
            enabled = ET.SubElement(dhcp_server, "ENABLED")
        enabled.text = "1"

        pools = dhcp_server.find("POOLS")
        if pools is None:
            pools = ET.SubElement(dhcp_server, "POOLS")

        pool = pools.find("POOL")
        if pool is None:
            pool = ET.SubElement(pools, "POOL")

        _st(pool, "NAME", "serverPool")
        _st(pool, "NETWORK", network_addr)
        _st(pool, "MASK", mask)
        _st(pool, "DEFAULT_ROUTER", gateway_ip)
        _st(pool, "START_IP", start_ip)
        _st(pool, "END_IP", end_ip)
        _st(pool, "DNS_SERVER", dns_ip)
        _st(pool, "MAX_USERS", str(max_users))
        _st(pool, "LEASE_TIME", str(lease_time))
        _st(pool, "TFTP_ADDRESS", tftp_address)
        _st(pool, "WLC_ADDRESS", wlc_address)
        _st(pool, "DOMAIN_NAME", domain_name)

        if pool.find("DHCP_POOL_LEASES") is None:
            ET.SubElement(pool, "DHCP_POOL_LEASES")
        if dhcp_server.find("DHCP_RESERVATIONS") is None:
            ET.SubElement(dhcp_server, "DHCP_RESERVATIONS")
        if dhcp_server.find("AUTOCONFIG") is None:
            ET.SubElement(dhcp_server, "AUTOCONFIG")

def write_ftp_users(engine: ET.Element, dev_cfg: dict) -> None:
 
    """
    Scrive utenti FTP nel tag ENGINE/FTP_SERVER/USERS.
    - Mantiene sempre l'utente default cisco/cisco con tutti i permessi.
    - Utenti custom da dev_cfg["ftp_users"]:
        - username mancante → user1, user2, ... (progressivo)
        - password mancante → "1234"
        - permessi mancanti → tutti 1 (lettura+scrittura+tutto)
        - se write/delete/rename = 0 esplicito → solo lettura
    """
    import logging
    ftp = engine.find("FTP_SERVER")
    if ftp is None:
        return

    users_node = ftp.find("USERS")
    if users_node is None:
        users_node = ET.SubElement(ftp, "USERS")

    # Utente default cisco sempre presente
    default_cisco = {
        "username": "cisco",
        "password": "cisco",
        "read": 1, "write": 1, "delete": 1, "rename": 1, "list": 1,
    }

    # Costruisci lista utenti da scrivere
    users_to_write: list[dict] = [default_cisco]
    custom_users = dev_cfg.get("ftp_users")

    if isinstance(custom_users, list):
        counter = 1
        for u in custom_users:
            if not isinstance(u, dict):
                continue

            # Username: se mancante → user1, user2, ...
            username = str(u.get("username") or "").strip()
            if not username:
                username = f"user{counter}"
            counter += 1

            # Password: se mancante → "1234"
            password = str(u.get("password") or "").strip()
            if not password:
                password = "1234"

            # Permessi: se mancanti → 1 (default tutto abilitato)
            # L'utente può esplicitare 0 per disabilitare singoli permessi
            read   = int(bool(u.get("read",   1)))
            write  = int(bool(u.get("write",  1)))
            delete = int(bool(u.get("delete", 1)))
            rename = int(bool(u.get("rename", 1)))
            lst    = int(bool(u.get("list",   1)))

            entry = {
                "username": username,
                "password": password,
                "read":   read,
                "write":  write,
                "delete": delete,
                "rename": rename,
                "list":   lst,
            }

            # Se stesso username di cisco → sovrascrive, altrimenti aggiunge
            users_to_write = [x for x in users_to_write if x["username"] != username]
            users_to_write.append(entry)

    # Riscrivi nodo USERS
    users_node.clear()
    for u in users_to_write:
        user_node = ET.SubElement(users_node, "USER")
        ET.SubElement(user_node, "USERNAME").text = u["username"]
        ET.SubElement(user_node, "PASSWORD").text = u["password"]

        perm = ET.SubElement(user_node, "PERMISSION")
        ET.SubElement(perm, "READ").text   = str(u["read"])
        ET.SubElement(perm, "WRITE").text  = str(u["write"])
        ET.SubElement(perm, "DELETE").text = str(u["delete"])
        ET.SubElement(perm, "RENAME").text = str(u["rename"])
        ET.SubElement(perm, "LIST").text   = str(u["list"])

    # Riscrivi USER_ACCOUNT_MNGR (struttura che PT legge effettivamente)
    acct_mgr = ftp.find("USER_ACCOUNT_MNGR")
    if acct_mgr is None:
        acct_mgr = ET.SubElement(ftp, "USER_ACCOUNT_MNGR")
    acct_mgr.clear()
    for u in users_to_write:
        acct = ET.SubElement(acct_mgr, "ACCOUNT")
        ET.SubElement(acct, "USERNAME").text = u["username"]
        ET.SubElement(acct, "PASSWORD").text = u["password"]
        perms = ""
        if u["read"]:   perms += "R"
        if u["write"]:  perms += "W"
        if u["delete"]: perms += "D"
        if u["rename"]: perms += "N"
        if u["list"]:   perms += "L"
        ET.SubElement(acct, "PERMISSIONS").text = perms
