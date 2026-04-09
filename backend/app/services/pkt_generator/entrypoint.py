# backend/app/services/pkt_generator/entrypoint.py

from __future__ import annotations

import ipaddress
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.pkt_crypto import decrypt_pkt_data
from .template import get_pkt_generator, get_template_path
from .topology import build_links_config
from .utils import safe_name
from .config_generator import calculate_static_routes
from .network_plan import (
    alloc_ip,
    apply_switch_port_roles,
    attach_acl_to_router_interfaces,
    assign_router_lan_interfaces,
    assign_router_wan_interfaces,
    build_lan_segments,
    build_mail_server_by_switch,
    build_switch_segment_maps,
    collect_host_switch_links,
    default_vlan_id,
    init_mail_user_counters,
    is_router_on_a_stick,
    map_segments_to_vlans,
    normalize_vlans,
    segment_for_host,
)
from .server_config import build_server_configs
from .server_mail import get_mail_users_and_domain
from .server_services import has_service, normalize_services

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
        pcs_config_list = config.get("pcs_config") or []
        if not isinstance(pcs_config_list, list):
            pcs_config_list = []
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

        lan_segments = build_lan_segments(subnets, dhcp_dns)
        vlan_sequence = normalize_vlans(vlans_global)
        segment_by_vlan_id = map_segments_to_vlans(lan_segments, vlan_sequence)
        router_on_a_stick = is_router_on_a_stick(
            vlan_sequence,
            num_switches=num_switches,
            lan_segments=lan_segments,
            num_routers=num_routers,
        )
        switch_to_lan, switch_to_segments = build_switch_segment_maps(
            switches_config,
            lan_segments,
            router_on_a_stick=router_on_a_stick,
        )

        assign_router_lan_interfaces(
            links_config,
            routers_config,
            switch_to_lan,
            switch_to_segments,
            router_on_a_stick=router_on_a_stick,
        )

        # 2) Assign router WAN interfaces for router-router links.
        # L'utente può specificare wan_network e wan_prefix in topology config.
        wan_network_str = topology_cfg.get("wan_network", "11.0.0.0")
        wan_prefix = assign_router_wan_interfaces(
            links_config,
            routers_config,
            wan_network_str=str(wan_network_str),
            wan_prefix=int(topology_cfg.get("wan_prefix", 30)),
        )

        attach_acl_to_router_interfaces(routers_config, acl_global)

        # 3) Host (PC/Server) address allocation by switch LAN; PCs become DHCP clients if requested.
        link_to_switch, link_to_switch_port = collect_host_switch_links(links_config)
        fallback_vlan_id = default_vlan_id(vlans_global)

        # Allocate servers first (static IPs are useful for DNS/HTTP).
        for srv_idx in range(num_servers):
            name = safe_name("Server", srv_idx)
            switch = link_to_switch.get(name)
            explicit_server_cfg = (
                servers_config_list[srv_idx]
                if srv_idx < len(servers_config_list) and isinstance(servers_config_list[srv_idx], dict)
                else {}
            )
            seg = segment_for_host(
                switch,
                explicit_cfg=explicit_server_cfg,
                fallback_index=srv_idx,
                switch_to_segments=switch_to_segments,
                lan_segments=lan_segments,
                segment_by_vlan_id=segment_by_vlan_id,
            )
            srv_cfg: dict[str, Any] = {"name": name, "type": "server"}
            if seg is not None:
                ip = alloc_ip(seg)
                if ip:
                    srv_cfg.update(
                        {
                            "ip": ip,
                            "subnet": seg["mask"],
                            "gateway_ip": seg["gateway"],
                            "network": seg.get("network", ""),
                        }
                    )
                    if seg.get("vlan_id") is not None:
                        srv_cfg["vlan_id"] = seg["vlan_id"]
            devices_config.append(srv_cfg)

        build_server_configs(
            num_servers=num_servers,
            servers_config_list=servers_config_list,
            server_services_global=server_services,
            devices_config=devices_config,
        )

        # Resolve a single DNS server IP for DHCP pools when DNS and DHCP are split.
        dns_server_ip: str | None = None
        for dev in devices_config:
            if str(dev.get("type", "")).lower() != "server":
                continue
            services = normalize_services(dev.get("server_services"))
            if "dns" in services and str(dev.get("ip", "")).strip():
                dns_server_ip = str(dev["ip"]).strip()
                break

        # Se l'utente ha gia specificato dhcp_pools via servers_config, non sovrascrivere
        # Prepara i dhcp_pools per i server DHCP (per ora: un pool per la LAN principale del server).
        for d in devices_config:
            if str(d.get("type", "")).lower() != "server":
                continue
            services = normalize_services(d.get("server_services"))
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

            # Crea un pool per ogni LAN: serverPool (locale) prima, rete<network> (remote) dopo
            local_pools = []
            remote_pools = []
            for seg in lan_segments:
                seg_net = seg.get("network", "")
                seg_net_base = seg_net.split("/")[0] if "/" in seg_net else seg_net
                if not seg_net:
                    continue
                pool_gw = seg.get("gateway", gw)
                pool_mask = seg.get("mask", mask)
                pool_dns = dns_server_ip or seg.get("dns_server") or server_ip
                if seg_net_base == network_addr:
                    local_pools.append({
                        "name": "serverPool",
                        "network": seg_net_base,
                        "mask": pool_mask,
                        "gateway": pool_gw,
                        "dns": pool_dns,
                    })
                else:
                    remote_pools.append({
                        "name": f"rete{seg_net_base}",
                        "network": seg_net_base,
                        "mask": pool_mask,
                        "gateway": pool_gw,
                        "dns": pool_dns,
                    })
            all_pools = local_pools + remote_pools
            # Fallback: se lan_segments vuoto usa la rete del server stesso
            if not all_pools:
                pool_dns = dns_server_ip or server_ip
                all_pools.append({
                    "name": "serverPool",
                    "network": network_addr,
                    "mask": mask,
                    "gateway": gw,
                    "dns": pool_dns,
                })
            user_pools = d.get("dhcp_pools") or []
            if user_pools:
                # Merge: usa nomi utente ma dati di rete da all_pools
                merged = []
                for i, auto_pool in enumerate(all_pools):
                    user_name = user_pools[i]["name"] if i < len(user_pools) and user_pools[i].get("name") else auto_pool["name"]
                    merged.append({**auto_pool, "name": user_name})
                d["dhcp_pools"] = merged
            else:
                d["dhcp_pools"] = all_pools


        # Propaga dhcp_server_ip per ip helper-address su interfacce LAN remote
        for d in devices_config:
            if str(d.get("type", "")).lower() != "server":
                continue
            svc = normalize_services(d.get("server_services"))
            if "dhcp" not in svc or not d.get("ip"):
                continue
            dhcp_srv_network = None
            try:
                import ipaddress as _ipa
                dhcp_srv_network = str(_ipa.IPv4Network(
                    str(d["ip"]) + "/" + str(d.get("subnet", "255.255.255.0")),
                    strict=False).network_address)
            except Exception:
                pass
            for r in routers_config:
                # Imposta dhcp_server_ip se almeno una interfaccia LAN e in rete diversa dal DHCP server
                has_remote_lan = False
                for iface in r.get("interfaces") or []:
                    if str(iface.get("role", "")).lower() != "lan":
                        continue
                    try:
                        r_net = str(_ipa.IPv4Network(
                            str(iface["ip"]) + "/" + str(iface.get("mask", "255.255.255.0")),
                            strict=False).network_address)
                        if dhcp_srv_network and r_net != dhcp_srv_network:
                            has_remote_lan = True
                            break
                    except Exception:
                        continue
                if has_remote_lan:
                    r["dhcp_server_ip"] = d["ip"]
            break

        pc_idx = 0
        # Verifica se c'è un server DHCP dedicato tra i server già aggiunti
        has_dhcp_server = any(
            has_service(d, "dhcp")
            for d in devices_config
            if str(d.get("type", "")).lower() == "server"
        )

        # Trova l'IP del server DHCP (se esiste)
        dhcp_srv_ip: str | None = None
        if has_dhcp_server:
            for d in devices_config:
                if str(d.get("type", "")).lower() != "server":
                    continue
                services = normalize_services(d.get("server_services"))
                if "dhcp" in services and d.get("ip"):
                    dhcp_srv_ip = str(d["ip"])
                    break

        # Mail servers per LAN (switch): necessari per EMAIL_CLIENT sui PC della stessa rete.
        mail_server_by_switch = build_mail_server_by_switch(
            devices_config,
            link_to_switch,
            normalize_services,
        )
        mail_user_counter_by_switch = init_mail_user_counters()

        while pc_idx < num_pcs:
            name = safe_name("PC", pc_idx)
            switch = link_to_switch.get(name)
            explicit_pc_cfg = (
                pcs_config_list[pc_idx]
                if pc_idx < len(pcs_config_list) and isinstance(pcs_config_list[pc_idx], dict)
                else {}
            )
            seg = segment_for_host(
                switch,
                explicit_cfg=explicit_pc_cfg,
                fallback_index=pc_idx,
                switch_to_segments=switch_to_segments,
                lan_segments=lan_segments,
                segment_by_vlan_id=segment_by_vlan_id,
            )

            pc_cfg: dict[str, Any] = {
                "name": name,
                "type": "pc",
            }
            if seg is not None and seg.get("vlan_id") is not None:
                pc_cfg["vlan_id"] = seg["vlan_id"]

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
                ip = alloc_ip(seg)
                if ip:
                    pc_cfg.update(
                        {
                            "ip": ip,
                            "subnet": seg["mask"],
                            "gateway_ip": seg["gateway"],
                            "dhcp_mode": "static",
                        }
                    )

            # Configurazione client email sul PC se nella stessa LAN di un server mail.
            mail_srv = mail_server_by_switch.get(switch or "")
            if mail_srv is not None:
                users, domain = get_mail_users_and_domain(mail_srv)
                users_by_name = {u["username"]: u["password"] for u in users}

                explicit_user = str(explicit_pc_cfg.get("mail_user") or "").strip()
                explicit_password = str(explicit_pc_cfg.get("mail_password") or "").strip()

                if explicit_user:
                    selected_user = explicit_user
                    selected_password = (
                        explicit_password
                        or users_by_name.get(selected_user)
                        or "1234"
                    )
                    pc_cfg["mail_username"] = selected_user
                    pc_cfg["mail_password"] = selected_password
                    pc_cfg["mail_domain"] = domain
                    pc_cfg["mail_server_ip"] = str(mail_srv.get("ip", "")).strip()
                else:
                    # Assegna utente solo se esiste nel server (non oltre len(users))
                    counter = mail_user_counter_by_switch[switch or ""]
                    if counter < len(users):
                        selected_user = users[counter]["username"]
                        selected_password = users[counter]["password"]
                        mail_user_counter_by_switch[switch or ""] += 1
                        pc_cfg["mail_username"] = selected_user
                        pc_cfg["mail_password"] = selected_password
                        pc_cfg["mail_domain"] = domain
                        pc_cfg["mail_server_ip"] = str(mail_srv.get("ip", "")).strip()
                    # Se counter >= len(users) → PC non configurato, niente email client

            devices_config.append(pc_cfg)
            pc_idx += 1


        # 4) Switch VLAN port roles (best-effort; trunks only if VLANs are provided).
        apply_switch_port_roles(
            switches_config,
            link_to_switch,
            link_to_switch_port,
            devices_config,
            links_config,
            vlans_global=vlans_global,
            vlan_sequence=vlan_sequence,
            default_vlan=fallback_vlan_id,
        )

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
