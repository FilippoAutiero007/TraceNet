# backend/app/services/pkt_generator/entrypoint.py

from __future__ import annotations

import ipaddress
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from collections import defaultdict

from app.services.pkt_crypto import decrypt_pkt_data
from .template import get_pkt_generator, get_template_path
from .topology import build_links_config
from .utils import safe_name
from .config_generator import calculate_static_routes
from .server_config import build_server_configs

logger = logging.getLogger(__name__)


def save_pkt_file(subnets: list, config: dict[str, Any], output_dir: str) -> dict[str, Any]:
    logger.info("Generating PKT file with template-based approach")

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        pkt_filename = f"network_{timestamp}.pkt"
        xml_filename = f"network_{timestamp}.xml"

        pkt_path = str(Path(output_dir) / pkt_filename)
        xml_path = str(Path(output_dir) / xml_filename)

        template_path = str(get_template_path())
        generator = get_pkt_generator(template_path)

        device_counts = config.get("devices", {})
        num_routers = int(device_counts.get("routers", 1))
        num_switches = int(device_counts.get("switches", 1))
        num_pcs = int(device_counts.get("pcs", 0))
        num_servers = int(device_counts.get("servers", 0))
        topology_cfg = config.get("topology", {})
        if not isinstance(topology_cfg, dict):
            topology_cfg = {}

        raw_edge_routers = topology_cfg.get("edge_routers", topology_cfg.get("edge_lan_routers"))
        edge_routers: int | None
        try:
            edge_routers = int(raw_edge_routers) if raw_edge_routers is not None else None
        except (TypeError, ValueError):
            edge_routers = None
        backbone_mode = str(topology_cfg.get("backbone_mode", "chain"))

        # Generate links first to determine router port requirements
        links_config = build_links_config(
            num_routers, num_switches, num_pcs,
            num_servers=num_servers,
            edge_routers=edge_routers,
            backbone_mode=backbone_mode,
        )

        # Backward-compatible defaults (preserve current behavior unless explicitly requested).
        routing_protocol = str(config.get("routing_protocol", "static")).strip()
        dhcp_from_router = bool(config.get("dhcp_from_router", False))
        dhcp_dns = config.get("dhcp_dns")
        server_services = list(config.get("server_services") or [])
        servers_config_list = config.get("servers_config") or []
        if not isinstance(servers_config_list, list):
            servers_config_list = []
        vlans_global = list(config.get("vlans") or [])
        nat_global = config.get("nat")
        acl_global = list(config.get("acl") or [])

        # Count ports used by each router
        router_port_count: dict[str, int] = defaultdict(int)
        for link in links_config:
            frm = link.get("from", "")
            to = link.get("to", "")
            if frm.startswith("Router"):
                router_port_count[frm] += 1
            if to.startswith("Router"):
                router_port_count[to] += 1

        def _choose_router_type(num_ports: int) -> str:
            n = max(1, num_ports)
            if n <= 10:
                return f"router-{n}port"
            return "router-10port"

        devices_config: list[dict[str, Any]] = []
        routers_config: list[dict[str, Any]] = []
        switches_config: list[dict[str, Any]] = []

        # Router: select model based on required ports
        for i in range(num_routers):
            router_name = safe_name("Router", i)
            ports_needed = router_port_count.get(router_name, 1)
            router_type = _choose_router_type(ports_needed)
            router_cfg = {
                "name": router_name,
                "type": router_type,
                "routing_protocol": routing_protocol,
                "dhcp_from_router": dhcp_from_router,
                "dhcp_dns": dhcp_dns,
                "nat": nat_global,
                "acl": acl_global,
                # Filled below after link analysis
                "interfaces": [],
                "interface_ips": {},
            }
            devices_config.append(router_cfg)
            routers_config.append(router_cfg)

        # Switch: ad esempio Cisco 2960 a 24 porte (id dal JSON)
        for i in range(num_switches):
            sw_cfg = {
                "name": safe_name("Switch", i),
                "type": "switch-24port",
                "vlans": vlans_global,
                "access_ports": {},
                "trunk_ports": [],
            }
            devices_config.append(sw_cfg)
            switches_config.append(sw_cfg)

        # Build LAN segments (VLSM results) used for router LAN interfaces and host addressing.
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
            # Gateway: use VLSM gateway if present; else fallback to "first usable" by convention.
            vlsm_gw = getattr(subnet, "gateway", None)
            try:
                gw_ip = ipaddress.ip_address(str(vlsm_gw)) if vlsm_gw else start_ip
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

        def _switch_index(switch_name: str) -> int:
            if switch_name.startswith("Switch"):
                try:
                    return int(switch_name.replace("Switch", ""))
                except ValueError:
                    return 0
            return 0

        switch_to_lan: dict[str, dict[str, Any]] = {}
        if lan_segments:
            for sw in switches_config:
                seg = lan_segments[_switch_index(sw["name"]) % len(lan_segments)]
                switch_to_lan[sw["name"]] = seg

        # Helper: add/update router interface config (so config_generator can build IOS config).
        def _set_router_iface(
            router_cfg: dict[str, Any],
            if_name: str,
            *,
            ip: str,
            mask: str,
            role: str,
            dns_server: str | None = None,
        ) -> None:
            interfaces = router_cfg.setdefault("interfaces", [])
            iface_ip = router_cfg.setdefault("interface_ips", {})
            iface_ip[str(if_name)] = str(ip)
            for entry in interfaces:
                if str(entry.get("name", "")) == if_name:
                    entry.update({"ip": str(ip), "mask": str(mask), "role": role})
                    if dns_server is not None:
                        entry["dns_server"] = str(dns_server)
                    break
            else:
                iface_entry = {"name": str(if_name), "ip": str(ip), "mask": str(mask), "role": role}
                if dns_server is not None:
                    iface_entry["dns_server"] = str(dns_server)
                interfaces.append(iface_entry)

            # Backward-compat: ensure base router ip/subnet exists for downstream code.
            if role == "lan" and not router_cfg.get("ip"):
                router_cfg["ip"] = str(ip)
                router_cfg["subnet"] = str(mask)
                router_cfg["gateway_ip"] = str(ip)

        # 1) Assign router LAN interfaces from router->switch links.
        for link in links_config:
            frm = str(link.get("from", ""))
            to = str(link.get("to", ""))
            if not (frm.startswith("Router") and to.startswith("Switch")):
                continue
            router_name = frm
            switch_name = to
            router_port = str(link.get("from_port", "")).strip()
            if not router_port:
                continue
            seg = switch_to_lan.get(switch_name)
            if seg is None:
                continue
            router_cfg = next((r for r in routers_config if r["name"] == router_name), None)
            if router_cfg is None:
                continue
            _set_router_iface(
                router_cfg,
                router_port,
                ip=seg["gateway"],
                mask=seg["mask"],
                role="lan",
                dns_server=seg.get("dns_server"),
            )

        # 2) Assign router WAN interfaces for router-router links.
        # L'utente può specificare wan_network e wan_prefix in topology config.
        wan_network_str = topology_cfg.get("wan_network", "11.0.0.0")
        wan_prefix = int(topology_cfg.get("wan_prefix", 30))
        try:
            wan_base = ipaddress.ip_network(f"{wan_network_str}/{wan_prefix}", strict=False)
            block_size = 2 ** (32 - wan_prefix)
        except Exception:
            wan_base = ipaddress.ip_network("11.0.0.0/30", strict=False)
            block_size = 4
            wan_prefix = 30

        rr_links = [
            l
            for l in links_config
            if str(l.get("from", "")).startswith("Router") and str(l.get("to", "")).startswith("Router")
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
                _set_router_iface(r1, from_port, ip=ip1, mask=mask, role="wan")
            if r2:
                _set_router_iface(r2, to_port, ip=ip2, mask=mask, role="wan")

        # 3) Host (PC/Server) address allocation by switch LAN; PCs become DHCP clients if requested.
        link_to_switch: dict[str, str] = {}
        link_to_switch_port: dict[str, str] = {}
        for link in links_config:
            frm = str(link.get("from", ""))
            to = str(link.get("to", ""))
            if frm.startswith("Switch") and (to.startswith("PC") or to.startswith("Server")):
                link_to_switch[to] = frm
                link_to_switch_port[to] = str(link.get("from_port", "")).strip()

        # Default VLAN selection for access ports when VLANs are present.
        default_vlan_id: int | None = None
        for v in vlans_global:
            try:
                default_vlan_id = int(v.get("id", v.get("vlan_id")))
                break
            except Exception:
                continue

        def _alloc_ip(seg: dict[str, Any]) -> str | None:
            nxt = seg.get("next_ip")
            if not isinstance(nxt, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
                return None
            if int(nxt) > int(seg["end_ip"]):
                return None
            seg["next_ip"] = ipaddress.ip_address(int(nxt) + 1)
            return str(nxt)

        # Allocate servers first (static IPs are useful for DNS/HTTP).
        for srv_idx in range(num_servers):
            name = safe_name("Server", srv_idx)
            switch = link_to_switch.get(name)
            seg = switch_to_lan.get(switch) if switch else (lan_segments[srv_idx % len(lan_segments)] if lan_segments else None)
            srv_cfg: dict[str, Any] = {"name": name, "type": "server"}
            if seg is not None:
                ip = _alloc_ip(seg)
                if ip:
                    srv_cfg.update(
                        {
                            "ip": ip,
                            "subnet": seg["mask"],
                            "gateway_ip": seg["gateway"],
                            "network": seg.get("network", ""),
                        }
                    )
            devices_config.append(srv_cfg)

        build_server_configs(
            num_servers=num_servers,
            servers_config_list=servers_config_list,
            server_services_global=server_services,
            devices_config=devices_config,
        )


        # Inject dns_records from root config into the DNS server device
        _root_dns_records = config.get("dns_records") or []
        if _root_dns_records:
            for _dev in devices_config:
                if str(_dev.get("type", "")).lower() == "server":
                    _svc = {str(s).lower() for s in (_dev.get("server_services") or [])}
                    if "dns" in _svc and not _dev.get("dns_records"):
                        _dev["dns_records"] = _root_dns_records
                        break
        # Prepara i dhcp_pools per i server DHCP (per ora: un pool per la LAN principale del server).
        for d in devices_config:
            if str(d.get("type", "")).lower() != "server":
                continue
            services = {str(s).strip().lower() for s in (d.get("server_services") or [])}
            if "dhcp" not in services:
                continue

            server_ip = str(d.get("ip", "")).strip()
            mask = str(d.get("subnet", "255.255.255.0")).strip()
            gw = str(d.get("gateway_ip", "")).strip()
            if not gw:
                # Se manca gateway esplicito, usa il server come fallback
                gw = server_ip

            # Calcola network address della LAN del server
            try:
                net = ipaddress.IPv4Network(f"{server_ip}/{mask}", strict=False)
                network_addr = str(net.network_address)
            except Exception:
                network_addr = "0.0.0.0"

            d["dhcp_pools"] = [
                {
                    "name": f"{d.get('name', 'server')}_pool",
                    "network": network_addr,
                    "mask": mask,
                    "gateway": gw,
                    "dns": server_ip,
                    # start_ip/end_ip verranno calcolati automaticamente in write_dhcp_config
                }
            ]

        # Propaga dhcp_server_ip ai router per ip helper-address
        for d in devices_config:
            if d.get("type") == "server" and d.get("ip"):
                svc = {str(s).lower() for s in (d.get("server_services") or [])}
                if "dhcp" in svc:
                    for r in routers_config:
                        r["dhcp_server_ip"] = d["ip"]
                    break

        pc_idx = 0
        # Verifica se c'è un server DHCP dedicato tra i server già aggiunti
        has_dhcp_server = any(
            "dhcp" in {str(s).lower() for s in (d.get("server_services") or [])}
            for d in devices_config
            if str(d.get("type", "")).lower() == "server"
        )

        # Trova l'IP del server DHCP (se esiste)
        dhcp_srv_ip: str | None = None
        if has_dhcp_server:
            for d in devices_config:
                if str(d.get("type", "")).lower() != "server":
                    continue
                services = {str(s).strip().lower() for s in (d.get("server_services") or [])}
                if "dhcp" in services and d.get("ip"):
                    dhcp_srv_ip = str(d["ip"])
                    break

        while pc_idx < num_pcs:
            name = safe_name("PC", pc_idx)
            switch = link_to_switch.get(name)
            seg = switch_to_lan.get(switch) if switch else (
                lan_segments[pc_idx % len(lan_segments)] if lan_segments else None
            )

            pc_cfg: dict[str, Any] = {
                "name": name,
                "type": "pc",
            }

            # Decide la modalità IP per il PC: DHCP vs static
            if dhcp_from_router or has_dhcp_server:
                # PC client DHCP (router o server con ip helper-address)
                pc_cfg["dhcp_client"] = True
                pc_cfg["dhcp_mode"] = "dhcp"

                if seg is not None:
                    # gateway della LAN (serve per ENGINE/GATEWAY)
                    pc_cfg["gateway_ip"] = seg["gateway"]

                if dhcp_srv_ip:
                    # usato da _set_pc_dhcp_mode per DHCP_SERVER_IP / PORT_DNS
                    pc_cfg["dhcp_server_ip"] = dhcp_srv_ip

            elif seg is not None:
                ip = _alloc_ip(seg)
                if ip:
                    pc_cfg.update(
                        {
                            "ip": ip,
                            "subnet": seg["mask"],
                            "gateway_ip": seg["gateway"],
                            "dhcp_mode": "static",
                        }
                    )

            devices_config.append(pc_cfg)
            pc_idx += 1


        # 4) Switch VLAN port roles (best-effort; trunks only if VLANs are provided).
        switches_by_name = {sw["name"]: sw for sw in switches_config}
        for host_name, sw_name in link_to_switch.items():
            sw = switches_by_name.get(sw_name)
            if sw is None:
                continue
            port = link_to_switch_port.get(host_name) or ""
            if not port:
                continue
            vid = None
            # Try to read explicit vlan_id from the host config (if user provided it).
            host = next((d for d in devices_config if d.get("name") == host_name), None)
            if host is not None and host.get("vlan_id") is not None:
                try:
                    vid = int(host["vlan_id"])
                except Exception:
                    vid = None
            if vid is None and default_vlan_id is not None:
                vid = default_vlan_id
            if vid is not None:
                sw.setdefault("access_ports", {})[port] = vid

        if vlans_global:
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

        # 5) Static routes: compute automatically after interfaces are populated.
        protocol_norm = routing_protocol.strip().lower()
        if protocol_norm in {"static", "statica"}:
            for r in routers_config:
                r["routes"] = calculate_static_routes(
                    str(r["name"]),
                    devices_config,
                    links_config,
                    wan_prefix=wan_prefix,
                )

        logger.info("Generating %s devices and %s links", len(devices_config), len(links_config))

        generator.generate(devices_config, links_config=links_config, output_path=pkt_path)

        # Export XML of the GENERATED PKT (not the template)
        pkt_bytes = Path(pkt_path).read_bytes()
        generated_xml = decrypt_pkt_data(pkt_bytes).decode("utf-8", errors="strict")
        Path(xml_path).write_text(generated_xml, encoding="utf-8")

        file_size = Path(pkt_path).stat().st_size
        return {
            "success": True,
            "pkt_path": pkt_path,
            "xml_path": xml_path,
            "pkt_file": pkt_filename,
            "xml_file": xml_filename,
            "devices": devices_config,
            "links": links_config,
            "encoding_used": "template_based",
            "file_size": file_size,
            "pka2xml_available": False,
            "method": "template_cloning",
        }

    except Exception as exc:
        logger.error("PKT generation failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}
