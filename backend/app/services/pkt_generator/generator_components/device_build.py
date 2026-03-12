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
from app.services.pkt_generator.server_config import write_dns_records
from app.services.pkt_generator.utils import rand_memaddr, set_text, validate_name, rand_saveref


def _update_device_ip(engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
    module = engine.find("MODULE")
    if module is None:
        return

    slots = module.findall("SLOT")
    if not slots:
        return

    slot_module = slots[0].find("MODULE")
    if slot_module is None:
        return

    port = slot_module.find("PORT")
    if port is None:
        return

    wants_dhcp = bool(dev_cfg.get("dhcp_client"))
    if wants_dhcp:
        # Packet Tracer EndDevices use these tags for IPv4 addressing.
        set_text(port, "IP", "", create=True)
        set_text(port, "SUBNET", "", create=True)
        set_text(port, "PORT_GATEWAY", "", create=True)
        set_text(port, "PORT_DHCP_ENABLE", "true", create=True)
    else:
        set_text(port, "IP", str(dev_cfg.get("ip", "")), create=True)
        set_text(port, "SUBNET", str(dev_cfg.get("subnet", "255.255.255.0")), create=True)
        set_text(port, "PORT_DHCP_ENABLE", "false", create=True)
    set_text(port, "POWER", "true", create=True)
    # Template tag is UP_METHOD (UPMETHOD was a legacy typo in early code).
    set_text(port, "UP_METHOD", "5" if wants_dhcp else "3", create=True)

    gateway = dev_cfg.get("gateway_ip") or dev_cfg.get("gateway", "")
    if gateway and not wants_dhcp:
        set_text(port, "PORT_GATEWAY", str(gateway), create=True)


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

    # DHCP server (server-side), bind to FastEthernet0 pool if present in template.
    if "dhcp" in cfg:
        dhcps = engine.find("DHCP_SERVERS")
        if dhcps is not None:
            assoc = dhcps.find("ASSOCIATED_PORTS/ASSOCIATED_PORT")
            if assoc is None:
                # Create the minimal container if missing.
                assoc_ports = dhcps.find("ASSOCIATED_PORTS") or ET.SubElement(dhcps, "ASSOCIATED_PORTS")
                assoc = ET.SubElement(assoc_ports, "ASSOCIATED_PORT")
                set_text(assoc, "NAME", "FastEthernet0", create=True)
                dhcp_server = ET.SubElement(assoc, "DHCP_SERVER")
            else:
                dhcp_server = assoc.find("DHCP_SERVER") or ET.SubElement(assoc, "DHCP_SERVER")

            set_text(dhcp_server, "ENABLED", "1" if cfg["dhcp"] else "0", create=True)
            if cfg["dhcp"] and dev_cfg.get("ip") and dev_cfg.get("subnet") and dev_cfg.get("gateway_ip"):
                pools = dhcp_server.find("POOLS") or ET.SubElement(dhcp_server, "POOLS")
                pools.clear()
                pool = ET.SubElement(pools, "POOL")
                set_text(pool, "NAME", "LAN", create=True)
                # Pool parameters inferred from the server-connected LAN.
                try:
                    iface = ipaddress.IPv4Interface(f"{dev_cfg['gateway_ip']}/{dev_cfg['subnet']}")
                    net = iface.network
                    start = ipaddress.IPv4Address(int(net.network_address) + 10)
                    end = ipaddress.IPv4Address(int(net.broadcast_address) - 1)
                except Exception:
                    net = None
                    start = None
                    end = None
                if net is not None:
                    set_text(pool, "NETWORK", str(net.network_address), create=True)
                    set_text(pool, "MASK", str(net.netmask), create=True)
                set_text(pool, "DEFAULT_ROUTER", str(dev_cfg.get("gateway_ip")), create=True)
                if start is not None:
                    set_text(pool, "START_IP", str(start), create=True)
                if end is not None:
                    set_text(pool, "END_IP", str(end), create=True)
                # DNS server: prefer the server itself if DNS is enabled, else keep defaults.
                if cfg.get("dns") and dev_cfg.get("ip"):
                    set_text(pool, "DNS_SERVER", str(dev_cfg.get("ip")), create=True)

    # FTP
    if "ftp" in cfg:
        ftp = engine.find("FTP_SERVER") or ET.SubElement(engine, "FTP_SERVER")
        set_text(ftp, "ENABLED", "1" if cfg["ftp"] else "0", create=True)
        if cfg["ftp"]:
            mgr = ftp.find("USER_ACCOUNT_MNGR") or ET.SubElement(ftp, "USER_ACCOUNT_MNGR")
            mgr.clear()
            acct = ET.SubElement(mgr, "ACCOUNT")
            set_text(acct, "USERNAME", str(cfg.get("ftp_user") or "cisco"), create=True)
            set_text(acct, "PASSWORD", str(cfg.get("ftp_password") or "cisco"), create=True)
            set_text(acct, "PERMISSIONS", "RWDNL", create=True)

    # SMTP / POP3 (Packet Tracer uses EMAIL_SERVER with simple flags)
    wants_email = bool(cfg.get("smtp") or cfg.get("pop3"))
    if wants_email:
        email = engine.find("EMAIL_SERVER") or ET.SubElement(engine, "EMAIL_SERVER")
        set_text(email, "SMTP_ENABLED", "1" if cfg.get("smtp") else "0", create=True)
        set_text(email, "POP3_ENABLED", "1" if cfg.get("pop3") else "0", create=True)
        if cfg.get("smtp"):
            set_text(email, "SMTP_DOMAIN", str(cfg.get("smtp_domain") or "example.com"), create=True)


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

    if dev_cfg.get("ip") or dev_cfg.get("dhcp_client"):
        _update_device_ip(engine, dev_cfg)

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
