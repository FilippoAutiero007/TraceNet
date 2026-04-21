from __future__ import annotations

import ipaddress
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional

from app.models.schemas import PktAnalysisIssue, PktAnalysisResponse
from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.validator import (
    MissingSaveRefIdError,
    OrphanLinkEndpointError,
    validate_pkt_xml,
)


TRANSIT_DEVICE_TYPES = {"switch", "hub", "wireless access point"}
END_DEVICE_TYPES = {"pc", "server", "laptop", "printer"}


@dataclass
class PortInfo:
    name: str
    ip: str
    subnet: str
    gateway: str
    dhcp_enabled: bool
    up_method: str

    @property
    def has_ip(self) -> bool:
        return bool(self.ip.strip())


@dataclass
class DeviceInfo:
    save_ref: str
    name: str
    device_type: str
    ports: list[PortInfo]
    running_config_lines: list[str]
    has_server_dhcp: bool
    has_vlan_config: bool


def analyze_pkt_bytes(pkt_data: bytes, filename: str | None = None) -> PktAnalysisResponse:
    try:
        xml_bytes = decrypt_pkt_data(pkt_data)
        root = ET.fromstring(xml_bytes)
    except Exception as exc:  # noqa: BLE001
        return PktAnalysisResponse(
            success=False,
            filename=filename,
            error=f"Impossibile leggere il file .pkt: {exc}",
            summary="Il file non è stato decifrato o il suo XML interno è corrotto.",
            report=f"Errore bloccante: {exc}",
            issue_count=1,
            issues=[
                PktAnalysisIssue(
                    severity="error",
                    code="PKT_DECODE_FAILED",
                    title="File .pkt non leggibile",
                    message=f"Il file non può essere decifrato o l'XML interno è invalido: {exc}",
                    suggestion="Verifica che il file sia un vero Packet Tracer .pkt e non sia corrotto.",
                )
            ],
        )

    return analyze_pkt_xml(root, filename=filename)


def analyze_pkt_xml(root: ET.Element, filename: str | None = None) -> PktAnalysisResponse:
    issues: list[PktAnalysisIssue] = []
    devices = _parse_devices(root)
    links = _parse_links(root)

    try:
        validate_pkt_xml(root)
    except MissingSaveRefIdError as exc:
        issues.append(
            PktAnalysisIssue(
                severity="error",
                code="MISSING_SAVE_REF_ID",
                title="Riferimenti interni mancanti",
                message=str(exc),
                suggestion="Rigenera il file o correggi i nodi XML dei dispositivi.",
            )
        )
    except OrphanLinkEndpointError as exc:
        issues.append(
            PktAnalysisIssue(
                severity="error",
                code="ORPHAN_LINK_ENDPOINT",
                title="Link verso dispositivi inesistenti",
                message=str(exc),
                suggestion="Controlla i cavi e i riferimenti FROM/TO del file Packet Tracer.",
            )
        )

    if not devices:
        issues.append(
            PktAnalysisIssue(
                severity="error",
                code="NO_DEVICES",
                title="Nessun dispositivo trovato",
                message="Il file .pkt non contiene dispositivi analizzabili.",
                suggestion="Apri il file in Packet Tracer e verifica che la topologia non sia vuota.",
            )
        )

    _analyze_addresses(devices, issues)
    _analyze_end_devices(devices, issues)
    _analyze_router_configs(devices, issues)
    _analyze_segments(devices, links, issues)

    summary = _build_summary(devices, links, issues)
    report = _build_report(summary, issues)
    return PktAnalysisResponse(
        success=True,
        filename=filename,
        summary=summary,
        report=report,
        device_count=len(devices),
        link_count=len(links),
        issue_count=len(issues),
        issues=issues,
    )


def _parse_devices(root: ET.Element) -> list[DeviceInfo]:
    parsed: list[DeviceInfo] = []
    for dev in root.findall("./NETWORK/DEVICES/DEVICE"):
        engine = dev.find("ENGINE")
        if engine is None:
            continue

        name = (engine.findtext("NAME") or "").strip() or "Unknown"
        save_ref = (engine.findtext("SAVE_REF_ID") or engine.findtext("SAVEREFID") or "").strip()
        device_type = (engine.findtext("TYPE") or "").strip().lower()
        running_config_lines = [(line.text or "") for line in engine.findall("RUNNINGCONFIG/LINE")]
        has_server_dhcp = any(
            (node.text or "").strip().lower() in {"1", "true"}
            for node in engine.findall("DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED")
        )
        has_vlan_config = _device_has_vlan_config(engine, running_config_lines)
        parsed.append(
            DeviceInfo(
                save_ref=save_ref,
                name=name,
                device_type=device_type,
                ports=_extract_ports(engine, device_type),
                running_config_lines=running_config_lines,
                has_server_dhcp=has_server_dhcp,
                has_vlan_config=has_vlan_config,
            )
        )
    return parsed


def _extract_ports(engine: ET.Element, device_type: str) -> list[PortInfo]:
    ports: list[PortInfo] = []
    module = engine.find("MODULE")
    if module is None:
        return ports

    slots = module.findall("SLOT")
    for idx, slot in enumerate(slots):
        slot_module = slot.find("MODULE")
        if slot_module is None:
            continue
        port = slot_module.find("PORT")
        if port is None:
            continue
        port_type = (port.findtext("TYPE") or "").strip()
        port_name = _infer_port_name(device_type, idx, port_type)
        ports.append(
            PortInfo(
                name=port_name,
                ip=(port.findtext("IP") or "").strip(),
                subnet=(port.findtext("SUBNET") or "").strip(),
                gateway=((port.findtext("PORT_GATEWAY") or engine.findtext("GATEWAY") or "").strip()),
                dhcp_enabled=(port.findtext("PORT_DHCP_ENABLE") or "").strip().lower() == "true"
                or (port.findtext("UP_METHOD") or "").strip() == "1",
                up_method=(port.findtext("UP_METHOD") or "").strip(),
            )
        )
    return ports


def _infer_port_name(device_type: str, slot_idx: int, port_type: str) -> str:
    lower_type = port_type.lower()
    if device_type in END_DEVICE_TYPES:
        if "wireless" in lower_type:
            return "Wireless0"
        return "FastEthernet0"
    if "gigabit" in lower_type:
        return f"GigabitEthernet{slot_idx}/0"
    if "serial" in lower_type:
        return f"Serial{slot_idx}/0"
    if device_type == "switch":
        return f"FastEthernet{slot_idx}/1"
    return f"FastEthernet{slot_idx}/0"


def _device_has_vlan_config(engine: ET.Element, running_config_lines: list[str]) -> bool:
    vlan_nodes = engine.findall("VLANS/VLAN")
    custom_vlans = [node for node in vlan_nodes if (node.attrib.get("number") or "") not in {"1", "1002", "1003", "1004", "1005"}]
    if custom_vlans:
        return True
    joined = "\n".join(running_config_lines).lower()
    return "switchport access vlan" in joined or "switchport trunk" in joined or "interface fastethernet0/0." in joined


def _parse_links(root: ET.Element) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for cable in root.findall("./NETWORK/LINKS/LINK/CABLE"):
        ports = [((node.text or "").strip()) for node in cable.findall("PORT")]
        links.append(
            {
                "from": (cable.findtext("FROM") or "").strip(),
                "to": (cable.findtext("TO") or "").strip(),
                "from_port": ports[0] if len(ports) > 0 else "",
                "to_port": ports[1] if len(ports) > 1 else "",
            }
        )
    return links


def _analyze_addresses(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    ip_owners: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for device in devices:
        for port in device.ports:
            network = _safe_network(port.ip, port.subnet)
            if port.ip and not network:
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="INVALID_IP_OR_MASK",
                        title="IP o subnet mask non valida",
                        message=f"{device.name} {port.name} ha IP/mask non validi: {port.ip} {port.subnet}",
                        device=device.name,
                        interface=port.name,
                        suggestion="Correggi indirizzo IP e subnet mask nel dispositivo.",
                    )
                )
                continue
            if network and _is_reserved_host_address(port.ip, network):
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="RESERVED_HOST_ADDRESS",
                        title="Indirizzo host non utilizzabile",
                        message=f"{device.name} {port.name} usa {port.ip}, che coincide con network o broadcast di {network}.",
                        device=device.name,
                        interface=port.name,
                        suggestion="Assegna un IP host valido all'interno della subnet.",
                    )
                )
            if port.ip:
                ip_owners[port.ip].append((device.name, port.name))

    for ip, owners in ip_owners.items():
        if len(owners) < 2:
            continue
        owner_text = ", ".join(f"{device} {iface}" for device, iface in owners)
        issues.append(
            PktAnalysisIssue(
                severity="error",
                code="DUPLICATE_IP_ADDRESS",
                title="Indirizzo IP duplicato",
                message=f"L'indirizzo IP {ip} è usato più volte: {owner_text}.",
                suggestion="Assegna IP univoci ai dispositivi nella stessa rete.",
            )
        )


def _analyze_end_devices(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    router_interfaces = _collect_router_interfaces(devices)
    dhcp_capable_networks = _collect_dhcp_capable_networks(devices)

    for device in devices:
        if device.device_type not in END_DEVICE_TYPES:
            continue
        if not device.ports:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="MISSING_INTERFACE",
                    title="Interfaccia di rete assente",
                    message=f"{device.name} non ha una porta di rete analizzabile.",
                    device=device.name,
                )
            )
            continue

        port = device.ports[0]
        network = _safe_network(port.ip, port.subnet)
        if port.dhcp_enabled:
            if port.ip or port.subnet:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="DHCP_STATIC_RESIDUE",
                        title="Client DHCP con residui statici",
                        message=f"{device.name} è in DHCP ma conserva IP/subnet valorizzati su {port.name}.",
                        device=device.name,
                        interface=port.name,
                        suggestion="Pulisci IP statico residuo o reimposta la scheda in DHCP puro.",
                    )
                )
            if not dhcp_capable_networks:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="DHCP_PROVIDER_NOT_FOUND",
                        title="Nessun provider DHCP individuato",
                        message=f"{device.name} usa DHCP ma nel file non emerge alcun router/server DHCP attivo.",
                        device=device.name,
                        interface=port.name,
                        suggestion="Configura un pool DHCP sul router o abilita un server DHCP.",
                    )
                )
            continue

        if not port.ip or not port.subnet:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="MISSING_STATIC_IP",
                    title="IP statico incompleto",
                    message=f"{device.name} non ha un IP statico completo su {port.name}.",
                    device=device.name,
                    interface=port.name,
                    suggestion="Imposta IP e subnet mask oppure abilita DHCP.",
                )
            )
            continue

        if not network:
            continue

        if not port.gateway:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="MISSING_DEFAULT_GATEWAY",
                    title="Gateway predefinito mancante",
                    message=f"{device.name} ha IP statico ma non ha un gateway configurato.",
                    device=device.name,
                    interface=port.name,
                    suggestion="Imposta il gateway del router della LAN, ad esempio l'indirizzo dell'interfaccia router nella stessa subnet.",
                )
            )
            continue

        gateway_ip = _safe_ip(port.gateway)
        if gateway_ip is None:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="INVALID_DEFAULT_GATEWAY",
                    title="Gateway non valido",
                    message=f"{device.name} ha un gateway non valido: {port.gateway}.",
                    device=device.name,
                    interface=port.name,
                    suggestion="Inserisci un indirizzo IP valido come gateway.",
                )
            )
            continue

        if gateway_ip not in network:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="GATEWAY_OUTSIDE_SUBNET",
                    title="Gateway fuori subnet",
                    message=f"{device.name} usa gateway {port.gateway}, ma l'host {port.ip}/{port.subnet} appartiene a {network}.",
                    device=device.name,
                    interface=port.name,
                    suggestion="Gateway e host devono stare nella stessa subnet.",
                )
            )
            continue

        if port.gateway not in router_interfaces:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="GATEWAY_NOT_FOUND",
                    title="Gateway non trovato tra i router",
                    message=f"{device.name} punta a {port.gateway}, ma nessuna interfaccia router con quell'IP è stata trovata nel file.",
                    device=device.name,
                    interface=port.name,
                    suggestion="Verifica IP del router o collegamento della LAN.",
                )
            )


def _analyze_router_configs(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    routers = [device for device in devices if device.device_type == "router"]
    if len(routers) > 1:
        router_protocols = [_parse_running_config(device.running_config_lines) for device in routers]
        has_dynamic = any(data["dynamic_routing"] for data in router_protocols)
        has_static = any(data["static_routes"] for data in router_protocols)
        if not has_dynamic and not has_static:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="MISSING_ROUTING_CONFIGURATION",
                    title="Routing tra router assente",
                    message="Ci sono più router, ma nei running-config non risultano né protocolli dinamici né rotte statiche.",
                    suggestion="Configura OSPF/RIP/EIGRP oppure aggiungi rotte statiche tra i router.",
                )
            )

    for device in routers:
        networks: dict[str, str] = {}
        config_data = _parse_running_config(device.running_config_lines)
        for port in device.ports:
            network = _safe_network(port.ip, port.subnet)
            if network is None:
                continue
            key = str(network)
            previous_iface = networks.get(key)
            if previous_iface and previous_iface != port.name:
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="ROUTER_OVERLAPPING_SUBNETS",
                        title="Sottoreti sovrapposte sul router",
                        message=f"{device.name} usa la stessa subnet {key} su più interfacce ({previous_iface}, {port.name}).",
                        device=device.name,
                        suggestion="Rivedi il piano VLSM e assegna subnet diverse alle interfacce router.",
                    )
                )
            else:
                networks[key] = port.name

        for iface, addr in config_data["interface_ips"].items():
            xml_port = next((port for port in device.ports if port.name == iface), None)
            if xml_port is None:
                continue
            xml_addr = f"{xml_port.ip} {xml_port.subnet}".strip()
            rc_addr = f"{addr[0]} {addr[1]}".strip()
            if xml_addr != rc_addr:
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="ROUTER_XML_CONFIG_MISMATCH",
                        title="Mismatch tra XML e running-config",
                        message=f"{device.name} {iface} ha {xml_addr or 'vuoto'} nell'XML ma {rc_addr} nel running-config.",
                        device=device.name,
                        interface=iface,
                        suggestion="Allinea configurazione IOS e valori salvati nella porta del dispositivo.",
                    )
                )


def _analyze_segments(devices: list[DeviceInfo], links: list[dict[str, str]], issues: list[PktAnalysisIssue]) -> None:
    by_ref = {device.save_ref: device for device in devices if device.save_ref}
    adjacency: dict[str, set[str]] = defaultdict(set)
    for link in links:
        if link["from"] and link["to"]:
            adjacency[link["from"]].add(link["to"])
            adjacency[link["to"]].add(link["from"])

    visited: set[str] = set()
    for device in devices:
        if device.save_ref in visited or not device.save_ref or device.device_type == "router":
            continue
        segment = _switch_segment(device.save_ref, adjacency, by_ref)
        visited.update(segment)
        segment_devices = [by_ref[ref] for ref in segment if ref in by_ref]
        if not segment_devices:
            continue
        if any(item.has_vlan_config for item in segment_devices):
            continue

        subnets: dict[str, list[str]] = defaultdict(list)
        for item in segment_devices:
            if item.device_type not in END_DEVICE_TYPES | {"router"}:
                continue
            for port in item.ports:
                network = _safe_network(port.ip, port.subnet)
                if network is not None:
                    subnets[str(network)].append(item.name)

        if len(subnets) > 1:
            summary = "; ".join(f"{subnet}: {', '.join(sorted(set(names)))}" for subnet, names in sorted(subnets.items()))
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="LAN_SUBNET_MISMATCH",
                    title="Sottoreti diverse nella stessa LAN",
                    message=f"Nello stesso segmento layer-2 compaiono subnet diverse: {summary}. Possibile errore di VLSM o gateway.",
                    suggestion="Verifica subnet mask, gateway e assegnazione delle LAN; se usi VLAN esplicite, assicurati che siano configurate correttamente.",
                )
            )


def _switch_segment(start_ref: str, adjacency: dict[str, set[str]], by_ref: dict[str, DeviceInfo]) -> set[str]:
    seen: set[str] = set()
    queue = [start_ref]
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        current_type = by_ref.get(current).device_type if current in by_ref else ""
        for neighbor in adjacency.get(current, set()):
            if neighbor in seen:
                continue
            neighbor_type = by_ref.get(neighbor).device_type if neighbor in by_ref else ""
            if current_type in TRANSIT_DEVICE_TYPES or current == start_ref:
                queue.append(neighbor)
            elif neighbor_type in TRANSIT_DEVICE_TYPES:
                queue.append(neighbor)
    return seen


def _collect_router_interfaces(devices: Iterable[DeviceInfo]) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    for device in devices:
        if device.device_type != "router":
            continue
        for port in device.ports:
            if port.ip:
                found[port.ip] = (device.name, port.name)
    return found


def _collect_dhcp_capable_networks(devices: Iterable[DeviceInfo]) -> set[str]:
    found: set[str] = set()
    for device in devices:
        if device.device_type == "router":
            joined = "\n".join(device.running_config_lines).lower()
            if "ip dhcp pool" in joined:
                for port in device.ports:
                    network = _safe_network(port.ip, port.subnet)
                    if network is not None:
                        found.add(str(network))
        if device.has_server_dhcp:
            for port in device.ports:
                network = _safe_network(port.ip, port.subnet)
                if network is not None:
                    found.add(str(network))
    return found


def _parse_running_config(lines: list[str]) -> dict[str, object]:
    interface_ips: dict[str, tuple[str, str]] = {}
    dynamic_routing: set[str] = set()
    static_routes: list[str] = []
    current_iface: Optional[str] = None

    for raw_line in lines:
        line = raw_line.strip()
        lower = line.lower()
        if lower.startswith("interface "):
            current_iface = line.split(None, 1)[1]
            continue
        if line == "!":
            current_iface = None
            continue
        if current_iface and lower.startswith("ip address "):
            parts = line.split()
            if len(parts) >= 4:
                interface_ips[current_iface] = (parts[2], parts[3])
            continue
        if lower.startswith("router ospf"):
            dynamic_routing.add("ospf")
        elif lower.startswith("router rip"):
            dynamic_routing.add("rip")
        elif lower.startswith("router eigrp"):
            dynamic_routing.add("eigrp")
        elif lower.startswith("ip route "):
            static_routes.append(line)

    return {
        "interface_ips": interface_ips,
        "dynamic_routing": sorted(dynamic_routing),
        "static_routes": static_routes,
    }


def _safe_ip(value: str) -> Optional[ipaddress.IPv4Address]:
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _safe_network(ip_value: str, mask_value: str) -> Optional[ipaddress.IPv4Network]:
    if not ip_value or not mask_value:
        return None
    try:
        return ipaddress.ip_network(f"{ip_value}/{mask_value}", strict=False)
    except ValueError:
        return None


def _is_reserved_host_address(ip_value: str, network: ipaddress.IPv4Network) -> bool:
    ip_addr = _safe_ip(ip_value)
    if ip_addr is None:
        return False
    return ip_addr == network.network_address or ip_addr == network.broadcast_address


def _build_summary(devices: list[DeviceInfo], links: list[dict[str, str]], issues: list[PktAnalysisIssue]) -> str:
    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = sum(1 for issue in issues if issue.severity == "warning")
    return (
        f"Analizzati {len(devices)} dispositivi e {len(links)} link. "
        f"Trovati {errors} errori e {warnings} avvisi."
    )


def _build_report(summary: str, issues: list[PktAnalysisIssue]) -> str:
    if not issues:
        return f"{summary}\n\nNon sono stati individuati errori evidenti nel file .pkt."
    lines = [summary, ""]
    for index, issue in enumerate(issues, start=1):
        location = " - ".join(part for part in [issue.device, issue.interface] if part)
        header = f"{index}. [{issue.severity.upper()}] {issue.title}"
        if location:
            header += f" ({location})"
        lines.append(header)
        lines.append(issue.message)
        if issue.suggestion:
            lines.append(f"Suggerimento: {issue.suggestion}")
        lines.append("")
    return "\n".join(lines).strip()
