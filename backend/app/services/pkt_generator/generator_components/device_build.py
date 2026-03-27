from __future__ import annotations

import copy
import ipaddress
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator import utils
from app.services.pkt_generator.config_generator import (
    generate_router_config,
    generate_server_config,
    generate_switch_config,
)
from app.services.pkt_generator.server_dhcp import write_dhcp_config
from app.services.pkt_generator.server_mail import write_email_config
from app.services.pkt_generator.server_config import write_dns_records
from app.services.pkt_generator.utils import rand_memaddr, set_text, validate_name, rand_saveref


def _find_primary_port(engine: ET.Element) -> Optional[ET.Element]:
    """
    Return the primary wired port for end-devices (PC/Server/Laptop templates).

    Packet Tracer templates usually store the main NIC under:
    ENGINE/MODULE/SLOT[0]/MODULE/PORT
    """
    module = engine.find("MODULE")
    if module is None:
        return None
    slots = module.findall("SLOT")
    if not slots:
        return None
    slot_module = slots[0].find("MODULE")
    if slot_module is None:
        return None
    return slot_module.find("PORT")


def _configure_end_device_dhcp(engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
    """
    Configure an end-device as a DHCP client (sets the UI radio button in PT).

    Derived from PT dumps (e.g. pc_dhcp_after.xml):
    - PORT/UP_METHOD = 1
    - PORT/PORT_DHCP_ENABLE = true
    - ENGINE/GATEWAY contains the LAN gateway (optional but typical)
    """
    port = _find_primary_port(engine)
    if port is None:
        return

    # DHCP radio-button state (PT 8.2.2)
    set_text(port, "UP_METHOD", "1", create=True)
    set_text(port, "PORT_DHCP_ENABLE", "true", create=True)

    # Clear any static residue to avoid ambiguous states.
    for tag in ("IP", "SUBNET", "PORT_GATEWAY"):
        set_text(port, tag, "", create=True)

    gateway_ip = str(dev_cfg.get("gateway_ip", "")).strip()
    if gateway_ip:
        set_text(engine, "GATEWAY", gateway_ip, create=True)

    # Only write DHCP server / DNS when explicitly known.
    dhcp_server_ip = str(dev_cfg.get("dhcp_server_ip", "")).strip()
    if dhcp_server_ip:
        set_text(port, "DHCP_SERVER_IP", dhcp_server_ip, create=True)
        # Packet Tracer dumps often mirror this into PORT_DNS for the PC.
        set_text(port, "PORT_DNS", dhcp_server_ip, create=True)

        dns_client = engine.find("DNS_CLIENT")
        if dns_client is None:
            dns_client = ET.SubElement(engine, "DNS_CLIENT")
        set_text(dns_client, "SERVER_IP", dhcp_server_ip, create=True)


def _configure_email_client(engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
    username = str(dev_cfg.get("mail_username") or "").strip()
    password = str(dev_cfg.get("mail_password") or "").strip()
    mail_server_ip = str(dev_cfg.get("mail_server_ip") or "").strip()
    mail_domain = str(dev_cfg.get("mail_domain") or "").strip() or "mail.local"
    if not username or not password or not mail_server_ip:
        return

    email_client = engine.find("EMAIL_CLIENT")
    if email_client is None:
        email_client = ET.SubElement(engine, "EMAIL_CLIENT")

    email_address = f"{username}@{mail_domain}"

    set_text(email_client, "ENABLED", "1", create=True)
    # Legacy/actual PT fields from templates.
    set_text(email_client, "USER", username, create=True)
    set_text(email_client, "PASSWORD", password, create=True)
    set_text(email_client, "MAIL_ID", email_address, create=True)
    set_text(email_client, "NAME", username, create=True)
    set_text(email_client, "POP3_SERVER", mail_server_ip, create=True)
    set_text(email_client, "SMTP_SERVER", mail_server_ip, create=True)

    # Requested field names (explicitly created for PT 8.2.2 compatibility checks).
    set_text(email_client, "USERNAME", username, create=True)
    set_text(email_client, "EMAIL_ADDRESS", email_address, create=True)
    set_text(email_client, "INCOMING_MAIL_SERVER", mail_server_ip, create=True)
    set_text(email_client, "OUTGOING_MAIL_SERVER", mail_server_ip, create=True)


def _update_device_ip(engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
    """Scrive gli IP di tutte le interfacce configurate nei rispettivi slot."""
    module = engine.find("MODULE")
    if module is None:
        return
    slots = module.findall("SLOT")
    if not slots:
        return

    # Mappa nome interfaccia -> slot index
    # FastEthernet0/0 -> slot 0, FastEthernet1/0 -> slot 1, ecc.
    def slot_index_for_port(port_name: str) -> int:
        import re
        m = re.match(r"FastEthernet(\d+)/", port_name or "")
        if m:
            return int(m.group(1))
        m = re.match(r"GigabitEthernet(\d+)/", port_name or "")
        if m:
            return int(m.group(1))
        return 0

    interfaces = dev_cfg.get("interfaces", [])

    if interfaces:
        # Scrivi ogni interfaccia nel suo slot corretto
        for iface in interfaces:
            port_name = str(iface.get("name", "")).strip()
            ip = str(iface.get("ip", "")).strip()
            mask = str(iface.get("mask", "255.255.255.0")).strip()
            if not ip:
                continue
            idx = slot_index_for_port(port_name)
            if idx >= len(slots):
                continue
            slot_module = slots[idx].find("MODULE")
            if slot_module is None:
                continue
            port = slot_module.find("PORT")
            if port is None:
                continue
            set_text(port, "IP", ip, create=True)
            set_text(port, "SUBNET", mask, create=True)
            set_text(port, "POWER", "true", create=True)
            set_text(port, "UP_METHOD", "3", create=True)
            gateway = iface.get("gateway_ip") or dev_cfg.get("gateway_ip", "")
            if gateway and str(iface.get("role","")) == "lan":
                set_text(port, "PORT_GATEWAY", str(gateway), create=True)
                set_text(engine, "GATEWAY", str(gateway), create=True)
                set_text(engine, "GATEWAY", str(gateway), create=True)
    else:
        # Fallback: usa ip/subnet dal dev_cfg sul primo slot
        ip = str(dev_cfg.get("ip", "")).strip()
        mask = str(dev_cfg.get("subnet", "255.255.255.0")).strip()
        if not ip:
            return
        slot_module = slots[0].find("MODULE")
        if slot_module is None:
            return
        port = slot_module.find("PORT")
        if port is None:
            return
        set_text(port, "IP", ip, create=True)
        set_text(port, "SUBNET", mask, create=True)
        set_text(port, "POWER", "true", create=True)
        set_text(port, "UP_METHOD", "3", create=True)
        gateway = dev_cfg.get("gateway_ip", "")
        if gateway:
            set_text(port, "PORT_GATEWAY", str(gateway), create=True)
            set_text(engine, "GATEWAY", str(gateway), create=True)
            set_text(engine, "GATEWAY", str(gateway), create=True)


def _write_running_config_lines(running: ET.Element, commands: list[str]) -> None:
    # Pulisce le linee esistenti
    for line in running.findall("LINE"):
        running.remove(line)
    for cmd in commands:
        line = ET.SubElement(running, "LINE")
        line.text = cmd


def _ensure_router_running_config(
    engine: ET.Element,
    dev_cfg: dict[str, Any] | None = None,
    *,
    all_devices: Optional[list[dict[str, Any]]] = None,
    links_config: Optional[list[dict[str, Any]]] = None,
    topology: Any = None,
) -> None:
    """Scrive la configurazione IOS del router nell'XML (ENGINE/RUNNINGCONFIG/LINE)."""
    running = engine.find("RUNNINGCONFIG")
    if running is None:
        return

    if dev_cfg is None:
        _write_running_config_lines(running, ["!", "end"])
        return

    commands = generate_router_config(
        dev_cfg,
        all_devices=all_devices or [],
        links_config=links_config or [],
        topology=topology,
    )
    _write_running_config_lines(running, commands)
    # PT carica STARTUPCONFIG al boot ? deve essere identica a RUNNINGCONFIG
    startup = engine.find("STARTUPCONFIG")
    if startup is not None:
        _write_running_config_lines(startup, commands)


def _ensure_switch_running_config(engine: ET.Element, dev_cfg: dict[str, Any] | None = None) -> None:
    running = engine.find("RUNNINGCONFIG")
    if running is None or dev_cfg is None:
        return
    commands = generate_switch_config(dev_cfg, vlans=dev_cfg.get("vlans") or [])
    _write_running_config_lines(running, commands)


def _configure_server_services(engine: ET.Element, dev_cfg: dict[str, Any] | None = None) -> None:
    """
    Packet Tracer servers are configured via ENGINE service tags (not IOS RUNNINGCONFIG).
    We toggle a small, well-known subset of services used by TraceNet.
    """
    if dev_cfg is None:
        return

    cfg = generate_server_config(dev_cfg)

    # HTTP / HTTPS
    http = engine.find("HTTP_SERVER")
    if http is not None and "http" in cfg:
        set_text(http, "ENABLED", "1" if cfg["http"] else "0", create=True)
    https = engine.find("HTTPS_SERVER")
    if https is not None and "https" in cfg:
        set_text(https, "HTTPSENABLED", "1" if cfg["https"] else "0", create=True)

    # DNS
    dns = engine.find("DNS_SERVER")
    if dns is not None and "dns" in cfg:
        set_text(dns, "ENABLED", "1" if cfg["dns"] else "0", create=True)
        if cfg["dns"]:
            write_dns_records(engine, dev_cfg)

    # DHCP
    if cfg.get("dhcp"):
        write_dhcp_config(engine, dev_cfg)

    # FTP
    if "ftp" in cfg:
        ftp = engine.find("FTP_SERVER")
        if ftp is None:
            ftp = ET.SubElement(engine, "FTP_SERVER")
        set_text(ftp, "ENABLED", "1" if cfg["ftp"] else "0", create=True)
        if cfg["ftp"]:
            from app.services.pkt_generator.server_config import write_ftp_users
            write_ftp_users(engine, dev_cfg)

    # SMTP / POP3 / EMAIL
    if cfg.get("smtp") or cfg.get("pop3") or cfg.get("email"):
        write_email_config(engine, dev_cfg)


def _assign_unique_macs(new_device: ET.Element, used_macs: set[str], device_type: str) -> None:
    def next_unique_mac() -> str:
        for _ in range(2000):
            mac = utils.rand_realistic_mac(device_type)
            if mac not in used_macs:
                used_macs.add(mac)
                return mac
        raise RuntimeError("Unable to generate unique MAC")

    parent_map: dict[ET.Element, ET.Element] = {}

    def build_parent_map(node: ET.Element) -> None:
        for child in list(node):
            parent_map[child] = node
            build_parent_map(child)

    build_parent_map(new_device)

    for mac_elem in new_device.iter("MACADDRESS"):
        mac = next_unique_mac()
        mac_elem.text = mac
        parent = parent_map.get(mac_elem)
        if parent is None:
            continue
        bia = parent.find("BIA")
        if bia is not None:
            bia.text = mac
        link_local = utils.mac_to_link_local(mac)
        for tag in ("IPV6_LINK_LOCAL", "IPV6_DEFAULT_LINK_LOCAL"):
            ll = parent.find(tag)
            if ll is not None:
                ll.text = link_local.upper() if link_local else ""

    for bia in new_device.iter("BIA"):
        parent = parent_map.get(bia)
        if parent is not None and parent.find("MACADDRESS") is not None:
            continue
        bia.text = next_unique_mac()


def build_device(
    *,
    dev_cfg: dict[str, Any],
    idx: int,
    cols: int,
    all_devices: Optional[list[dict[str, Any]]] = None,
    links_config: Optional[list[dict[str, Any]]] = None,
    topology: Any = None,
    templates_base_dir: Path,
    device_templates: dict[str, dict[str, Any]],
    used_macs: set[str],
    used_dev_addrs: set[str],
    used_mem_addrs: set[str],
) -> tuple[ET.Element, str, str, str, Optional[dict[str, Any]]]:
    name = validate_name(dev_cfg["name"])
    requested_type = str(dev_cfg.get("type", "router-1port")).strip()

    resolved_type = requested_type
    device_meta = device_templates.get(resolved_type)
    if device_meta is None:
        resolved_type = "router-1port"
        device_meta = device_templates[resolved_type]

    relative_template = device_meta.get("template_file") or device_meta.get("base_template", "")
    template_path = templates_base_dir / relative_template
    if not template_path.exists():
        # Backward-compatible alias for historical catalog typo.
        candidate = templates_base_dir / relative_template.replace("FinalPoint/", "EndPoint/")
        if candidate != template_path and candidate.exists():
            template_path = candidate
            relative_template = str(Path("EndPoint") / Path(relative_template).name)

    if not template_path.exists() and resolved_type != "router-1port":
        resolved_type = "router-1port"
        device_meta = device_templates[resolved_type]
        relative_template = device_meta.get("template_file") or device_meta.get("base_template", "")
        template_path = templates_base_dir / relative_template

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    xml_str = decrypt_pkt_data(template_path.read_bytes()).decode("utf-8", errors="strict")
    template_root = ET.fromstring(xml_str)
    template_network = template_root.find("NETWORK")
    if template_network is None:
        raise ValueError(f"Invalid device template {template_path}: missing NETWORK")
    template_devices_node = template_network.find("DEVICES")
    if template_devices_node is None:
        raise ValueError(f"Invalid device template {template_path}: missing DEVICES")
    template_devices = template_devices_node.findall("DEVICE")
    if not template_devices:
        raise ValueError(f"Invalid device template {template_path}: no DEVICE found")

    template_device = template_devices[0]
    new_device = copy.deepcopy(template_device)
    engine = new_device.find("ENGINE")
    if engine is None:
        raise ValueError(f"Invalid device template {template_path}: missing ENGINE")

    set_text(engine, "NAME", name, create=True)
    set_text(engine, "SYSNAME", name, create=False)
    saveref = rand_saveref()
    set_text(engine, "SAVE_REF_ID", saveref, create=True)
    legacy = engine.find("SAVEREFID")
    if legacy is not None:
        legacy.text = saveref

    _assign_unique_macs(new_device, used_macs, requested_type)

    default_x = 200 + (idx % cols) * 250
    default_y = 200 + (idx // cols) * 200
    y_offset = (idx % 2) * 50
    x = int(dev_cfg.get("x", default_x))
    y = int(dev_cfg.get("y", default_y + y_offset))
    utils.set_coords(engine, x, y)

    workspace = new_device.find("WORKSPACE")
    if workspace is not None:
        logical = workspace.find("LOGICAL")
        if logical is not None:
            set_text(logical, "X", str(x), create=True)
            set_text(logical, "Y", str(y), create=True)
            dev_addr = rand_memaddr()
            while dev_addr in used_dev_addrs:
                dev_addr = rand_memaddr()
            used_dev_addrs.add(dev_addr)
            set_text(logical, "DEV_ADDR", dev_addr, create=True)

            mem_addr = rand_memaddr()
            while mem_addr in used_mem_addrs:
                mem_addr = rand_memaddr()
            used_mem_addrs.add(mem_addr)
            set_text(logical, "MEM_ADDR", mem_addr, create=True)

    is_dhcp = bool(dev_cfg.get("dhcp_client")) or str(dev_cfg.get("dhcp_mode", "")).strip().lower() == "dhcp"

    if dev_cfg.get("ip") or dev_cfg.get("dhcp_client") or dev_cfg.get("interfaces") or is_dhcp:
        category_lower = (device_meta.get("category") or resolved_type or "").lower()
        is_router = "router" in category_lower
        is_switch = "switch" in category_lower

        # DHCP client mode for end-devices (PC/Server/Laptop).
        if (not is_router and not is_switch) and is_dhcp:
            _configure_end_device_dhcp(engine, dev_cfg)
        else:
            _update_device_ip(engine, dev_cfg)
    _configure_email_client(engine, dev_cfg)

    category = (device_meta.get("category") or resolved_type or "").lower()
    if "router" in category:
        _ensure_router_running_config(
            engine,
            dev_cfg,
            all_devices=all_devices,
            links_config=links_config,
            topology=topology,
        )
    elif "switch" in category:
        _ensure_switch_running_config(engine, dev_cfg)
    elif "server" in category or name.lower().startswith("server"):
        _configure_server_services(engine, dev_cfg)
    physical_hint: Optional[dict[str, Any]] = None
    phys_text = template_device.findtext("WORKSPACE/PHYSICAL")
    if phys_text:
        path_parts = [part.strip("{} ") for part in phys_text.split(",") if part.strip()]
        if path_parts:
            proto_node: Optional[ET.Element] = None
            pw = template_root.find("PHYSICALWORKSPACE")
            if pw is not None:
                leaf_uuid = path_parts[-1]
                for node in pw.iter("NODE"):
                    uuid_text = (node.findtext("UUID_STR") or "").strip("{} ")
                    if uuid_text == leaf_uuid:
                        proto_node = copy.deepcopy(node)
                        break
            physical_hint = {
                "path_parts": path_parts,
                "proto_node": proto_node,
                "source_template": str(relative_template),
                "source_type": resolved_type,
            }
    return new_device, name, saveref, category, physical_hint
