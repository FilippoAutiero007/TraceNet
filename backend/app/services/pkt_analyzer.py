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
ROUTING_PROTOCOLS = {"rip": "RIP", "ospf": "OSPF", "eigrp": "EIGRP"}


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
    except Exception as exc:
        return PktAnalysisResponse(
            success=False,
            filename=filename,
            error=f"Impossibile leggere il file .pkt: {exc}",
            summary="Il file non e' stato decifrato o il suo XML interno e' corrotto.",
            report=f"Errore bloccante: {exc}",
            issue_count=1,
            issues=[
                PktAnalysisIssue(
                    severity="error",
                    code="PKT_DECODE_FAILED",
                    title="File .pkt non leggibile",
                    message=f"Il file non puo' essere decifrato o l'XML interno e' invalido: {exc}",
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
    _analyze_connectivity(devices, links, issues)
    _analyze_device_configs(devices, issues)
    _analyze_acls(devices, issues)
    _analyze_vlan_topology(devices, links, issues)
    _analyze_dhcp_topology(devices, links, issues)
    _analyze_routing(devices, issues)
    _analyze_nat(devices, issues)
    _analyze_security(devices, issues)
    _analyze_switch_configs(devices, issues)

    summary = _build_summary(devices, links, issues)
    report = _build_report(summary, issues)
    remediation_steps = _build_remediation_steps(issues)
    return PktAnalysisResponse(
        success=True,
        filename=filename,
        summary=summary,
        report=report,
        device_count=len(devices),
        link_count=len(links),
        issue_count=len(issues),
        issues=issues,
        remediation_steps=remediation_steps,
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
                message=f"L'indirizzo IP {ip} e' usato piu' volte: {owner_text}.",
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
                    suggestion="Aggiungi una scheda di rete (ad esempio FastEthernet) al dispositivo in Packet Tracer.",
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
                        message=f"{device.name} e' in DHCP ma conserva IP/subnet valorizzati su {port.name}.",
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
                    message=f"{device.name} punta a {port.gateway}, ma nessuna interfaccia router con quell'IP e' stata trovata nel file.",
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
                    message="Ci sono piu' router, ma nei running-config non risultano ne' protocolli dinamici ne' rotte statiche.",
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
                        message=f"{device.name} usa la stessa subnet {key} su piu' interfacce ({previous_iface}, {port.name}).",
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


def _analyze_connectivity(devices: list[DeviceInfo], links: list[dict[str, str]], issues: list[PktAnalysisIssue]) -> None:
    by_ref = {device.save_ref: device for device in devices if device.save_ref}
    adjacency: dict[str, set[str]] = defaultdict(set)
    for link in links:
        if link["from"]:
            adjacency[link["from"]].add(link["to"])
        if link["to"]:
            adjacency[link["to"]].add(link["from"])

    connected_refs = set(adjacency.keys())
    router_refs = {d.save_ref for d in devices if d.device_type == "router" and d.save_ref}

    for device in devices:
        if not device.save_ref:
            continue
        if device.save_ref in connected_refs:
            if device.device_type in TRANSIT_DEVICE_TYPES:
                has_router_in_segment = False
                if router_refs:
                    segment = _switch_segment(device.save_ref, adjacency, by_ref)
                    has_router_in_segment = bool(router_refs & segment)
                if not has_router_in_segment:
                    issues.append(
                        PktAnalysisIssue(
                            severity="warning",
                            code="SWITCH_NO_UPLINK",
                            title="Switch senza collegamento al router",
                            message=f"{device.name} e' collegato solo a dispositivi finali ma non ha un percorso verso alcun router. I dispositivi in questa LAN non possono uscire dalla rete locale.",
                            device=device.name,
                            suggestion="Collega lo switch a un router (direttamente o tramite un altro switch) per garantire connettivita' verso altre reti.",
                        )
                    )
            continue

        if device.device_type == "router":
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="ROUTER_DISCONNECTED",
                    title="Router non collegato",
                    message=f"{device.name} non ha alcun cavo di collegamento. Non puo' instradare pacchetti.",
                    device=device.name,
                    suggestion="Collega il router a uno switch o direttamente ad altri router usando cavi Copper o Seriali.",
                )
            )
        elif device.has_server_dhcp:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="DHCP_SERVER_DISCONNECTED",
                    title="Server DHCP non collegato alla rete",
                    message=f"{device.name} ha il servizio DHCP attivo ma non ha alcun cavo di collegamento. Nessun dispositivo puo' ricevere indirizzi IP da questo server.",
                    device=device.name,
                    suggestion="Collega il server a uno switch usando un cavo diretto (ad esempio Copper Straight-Through).",
                )
            )
        elif device.device_type in {"server", "pc", "laptop", "printer"}:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="DEVICE_DISCONNECTED",
                    title="Dispositivo non collegato",
                    message=f"{device.name} non ha alcun cavo di collegamento. Non puo' comunicare con altri dispositivi.",
                    device=device.name,
                    suggestion="Collega il dispositivo a uno switch con il cavo appropriato.",
                )
            )


def _analyze_device_configs(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    for device in devices:
        if device.name == "Unknown":
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="DEVICE_UNNAMED",
                    title="Dispositivo senza nome",
                    message=f"Un dispositivo di tipo {device.device_type} non ha un nome configurato (nome predefinito 'Unknown').",
                    suggestion="Assegna un nome descrittivo al dispositivo per identificarlo nella topologia.",
                )
            )

        if not device.ports and device.device_type in TRANSIT_DEVICE_TYPES | {"router"}:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="DEVICE_NO_PORTS",
                    title="Dispositivo senza porte",
                    message=f"{device.name} ({device.device_type}) non ha porte di rete configurate. Non puo' connettersi ad altri dispositivi.",
                    device=device.name,
                    suggestion="Aggiungi moduli di interfaccia al dispositivo o verifica che lo slot non sia vuoto.",
                )
            )

        if device.device_type != "router":
            continue

        config_data = _parse_running_config_detailed(device.running_config_lines)

        for port in device.ports:
            port_has_ip = port.has_ip
            iface_in_config = any(
                port.name in iface or port.name.replace("/0", "") in iface
                for iface in config_data["interfaces"]
            )
            if not port_has_ip and not port.dhcp_enabled and iface_in_config:
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="ROUTER_INTERFACE_NO_IP",
                        title="Interfaccia router senza IP",
                        message=f"{device.name} {port.name} non ha un indirizzo IP configurato ma e' presente nella running-config.",
                        device=device.name,
                        interface=port.name,
                        suggestion="Configura 'ip address' sull'interfaccia o usa 'no ip address' per disabilitarla esplicitamente.",
                    )
                )

        shutdown_interfaces = config_data["interfaces_shutdown"]
        if len(shutdown_interfaces) == len([p for p in device.ports if p.name in config_data["interfaces"]]):
            if shutdown_interfaces:
                iface_list = ", ".join(sorted(shutdown_interfaces))
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="ALL_INTERFACES_SHUTDOWN",
                        title="Tutte le interfacce router sono spente",
                        message=f"{device.name} ha tutte le interfacce in stato 'shutdown': {iface_list}. Il router non puo' instradare pacchetti.",
                        device=device.name,
                        suggestion="Usa 'no shutdown' sulle interfacce che devono essere attive.",
                    )
                )

        for iface in config_data["serial_interfaces_no_clock"]:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="SERIAL_NO_CLOCK_RATE",
                    title="Interfaccia seriale senza clock rate",
                    message=f"{device.name} {iface} e' un'interfaccia seriale ma non ha 'clock rate' configurato sul lato DCE.",
                    device=device.name,
                    interface=iface,
                    suggestion="Configura 'clock rate 64000' o superiore sull'interfaccia seriale DCE.",
                )
            )

        if not device.running_config_lines:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="ROUTER_NO_CONFIG",
                    title="Router senza configurazione",
                    message=f"{device.name} non ha alcuna riga di configurazione (running-config vuota).",
                    device=device.name,
                    suggestion="Apri il router in Packet Tracer e configuralo con IP, routing, ecc.",
                )
            )


def _parse_running_config_detailed(lines: list[str]) -> dict[str, object]:
    interfaces: dict[str, dict[str, object]] = {}
    current_iface: Optional[str] = None
    access_list_entries: set[str] = set()
    serial_interfaces_no_clock: list[str] = []
    dhcp_pool_names: list[str] = []
    has_dhcp_pool = False
    global_config: dict[str, object] = {}

    routing_protocols: dict[str, object] = {}
    current_routing: Optional[str] = None
    nat_inside_interfaces: list[str] = []
    nat_outside_interfaces: list[str] = []
    nat_pools: list[str] = []
    nat_acls: list[str] = []
    has_static_nat = False
    has_dynamic_nat = False
    has_nat_overload = False
    has_default_route = False
    has_enable_secret = False
    has_enable_password = False
    has_password_encryption = False
    has_banner = False
    has_domain_lookup = True
    has_ssh_config = False
    vty_lines: dict[str, object] = {"has_password": False, "transport_ssh": False}

    for raw_line in lines:
        line = raw_line.strip()
        lower = line.lower()

        if lower.startswith("interface "):
            current_iface = line.split(None, 1)[1]
            interfaces[current_iface] = {
                "has_ip": False, "shutdown": False,
                "acl_in": None, "acl_out": None,
                "encapsulation": None, "nat_direction": None,
            }
            if "serial" in current_iface.lower():
                interfaces[current_iface]["is_serial"] = True
            continue

        if line == "!":
            current_iface = None
            continue

        if current_iface is None:
            if lower.startswith("access-list "):
                parts = line.split()
                if len(parts) >= 2:
                    access_list_entries.add(parts[1])

            if lower.startswith("ip dhcp pool "):
                has_dhcp_pool = True
                parts = line.split(None, 3)
                dhcp_pool_names.append(parts[-1] if len(parts) > 3 else "unknown")

            if lower.startswith("router rip"):
                current_routing = "rip"
                if current_routing not in routing_protocols:
                    routing_protocols["rip"] = {"version": None, "networks": [], "passive": []}

            if lower.startswith("router ospf"):
                current_routing = "ospf"
                if current_routing not in routing_protocols:
                    routing_protocols["ospf"] = {"networks": [], "areas": []}

            if lower.startswith("router eigrp"):
                current_routing = "eigrp"
                if current_routing not in routing_protocols:
                    routing_protocols["eigrp"] = {"networks": [], "as_number": None}

            if current_routing == "rip" and lower.startswith("version "):
                routing_protocols["rip"]["version"] = line.split(None, 1)[-1].strip()

            if current_routing and lower.startswith("network "):
                net_parts = line.split(None, 1)
                if len(net_parts) > 1:
                    net_val = net_parts[1].strip()
                    if current_routing in routing_protocols:
                        rp = routing_protocols[current_routing]
                        if isinstance(rp, dict) and "networks" in rp:
                            rp["networks"].append(net_val)

            if current_routing and lower.startswith("passive-interface"):
                if current_routing in routing_protocols:
                    rp = routing_protocols[current_routing]
                    if isinstance(rp, dict) and "passive" in rp:
                        rp["passive"].append(line.split(None, 1)[-1] if len(line.split()) > 1 else "default")

            if lower.startswith("router ") and current_routing is not None:
                current_routing = None

            if lower.startswith("ip route 0.0.0.0 0.0.0.0"):
                has_default_route = True

            if lower.startswith("ip nat pool "):
                parts = line.split()
                if len(parts) >= 2:
                    nat_pools.append(parts[2])

            if lower.startswith("ip nat inside source list "):
                parts = line.split()
                if len(parts) >= 5:
                    nat_acls.append(parts[4])
                    rest = " ".join(parts[5:]).lower()
                    if "overload" in rest:
                        has_nat_overload = True
                    if "pool" in rest:
                        has_dynamic_nat = True

            if lower.startswith("ip nat inside source static "):
                has_static_nat = True

            if "enable secret" in lower:
                has_enable_secret = True
            if "enable password" in lower:
                has_enable_password = True

            if "service password-encryption" in lower:
                has_password_encryption = True

            if lower.startswith("banner motd"):
                has_banner = True

            if "no ip domain-lookup" in lower:
                has_domain_lookup = False

            if lower.startswith("ip domain-name ") or lower.startswith("ip domain name "):
                pass

            if "ip ssh" in lower:
                has_ssh_config = True

            continue

        if lower.startswith("ip address "):
            interfaces[current_iface]["has_ip"] = True
            continue

        if lower == "shutdown":
            interfaces[current_iface]["shutdown"] = True
            continue

        if lower.startswith("ip access-group "):
            parts = line.split()
            if len(parts) >= 3:
                direction = "in" if "in" in lower else "out"
                acl_ref = parts[2]
                interfaces[current_iface][f"acl_{direction}"] = acl_ref

        if lower.startswith("clock rate "):
            if current_iface:
                interfaces[current_iface]["has_clock_rate"] = True

        if lower.startswith("encapsulation dot1q"):
            if current_iface:
                encap_val = line.split(None, 2)[1] if len(line.split()) >= 2 else "dot1q"
                interfaces[current_iface]["encapsulation"] = encap_val

        if lower == "ip nat inside":
            interfaces[current_iface]["nat_direction"] = "inside"
            nat_inside_interfaces.append(current_iface)

        if lower == "ip nat outside":
            interfaces[current_iface]["nat_direction"] = "outside"
            nat_outside_interfaces.append(current_iface)

    for block in lines:
        block_lower = block.strip().lower()
        if "line vty" in block_lower:
            vty_lines["has_password"] = any("password" in l.lower() for l in lines[lines.index(block):])
            vty_lines["transport_ssh"] = any("transport input ssh" in l.lower() for l in lines)

    iface_names = list(interfaces.keys())
    shutdown_ifaces = [name for name, data in interfaces.items() if data.get("shutdown")]
    ip_ifaces = [name for name, data in interfaces.items() if data.get("has_ip")]
    acl_ifaces_in = {name: data.get("acl_in") for name, data in interfaces.items() if data.get("acl_in")}
    acl_ifaces_out = {name: data.get("acl_out") for name, data in interfaces.items() if data.get("acl_out")}
    serial_no_clock = [name for name, data in interfaces.items() if data.get("is_serial") and not data.get("has_clock_rate")]
    subifaces = {name: data.get("encapsulation") for name, data in interfaces.items() if "." in name}
    nat_inside = [name for name, data in interfaces.items() if data.get("nat_direction") == "inside"]
    nat_outside = [name for name, data in interfaces.items() if data.get("nat_direction") == "outside"]

    return {
        "interfaces": iface_names,
        "interfaces_shutdown": shutdown_ifaces,
        "interfaces_with_ip": ip_ifaces,
        "acl_inbound": acl_ifaces_in,
        "acl_outbound": acl_ifaces_out,
        "access_list_entries": sorted(access_list_entries),
        "serial_interfaces_no_clock": serial_no_clock,
        "has_dhcp_pool": has_dhcp_pool,
        "dhcp_pool_names": dhcp_pool_names,
        "subinterfaces": subifaces,
        "nat_inside_interfaces": nat_inside,
        "nat_outside_interfaces": nat_outside,
        "nat_pools": nat_pools,
        "nat_acls": nat_acls,
        "has_static_nat": has_static_nat,
        "has_dynamic_nat": has_dynamic_nat,
        "has_nat_overload": has_nat_overload,
        "has_default_route": has_default_route,
        "has_enable_secret": has_enable_secret,
        "has_enable_password": has_enable_password,
        "has_password_encryption": has_password_encryption,
        "has_banner": has_banner,
        "has_domain_lookup": has_domain_lookup,
        "has_ssh_config": has_ssh_config,
        "vty_has_password": vty_lines["has_password"],
        "vty_transport_ssh": vty_lines["transport_ssh"],
        "routing": routing_protocols,
    }


def _analyze_acls(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    for device in devices:
        if device.device_type != "router":
            continue
        config_data = _parse_running_config_detailed(device.running_config_lines)

        all_acls_applied: set[str] = set()
        for acl_ref in list(config_data["acl_inbound"].values()) + list(config_data["acl_outbound"].values()):
            if acl_ref:
                all_acls_applied.add(acl_ref)

        if not all_acls_applied:
            continue

        for acl_ref in all_acls_applied:
            if acl_ref not in config_data["access_list_entries"]:
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="ACL_REFERENCE_NOT_FOUND",
                        title="ACL referenziata ma non definita",
                        message=f"{device.name} usa 'ip access-group {acl_ref}' ma non esiste una access-list corrispondente nella configurazione.",
                        device=device.name,
                        suggestion="Definisci la access-list con i permessi desiderati, ad esempio: 'access-list {acl_ref} permit ip any any'.",
                    )
                )


def _analyze_vlan_topology(devices: list[DeviceInfo], links: list[dict[str, str]], issues: list[PktAnalysisIssue]) -> None:
    by_ref = {d.save_ref: d for d in devices if d.save_ref}
    adjacency: dict[str, set[str]] = defaultdict(set)
    for link in links:
        if link["from"] and link["to"]:
            adjacency[link["from"]].add(link["to"])
            adjacency[link["to"]].add(link["from"])

    switches_with_vlans = [d for d in devices if d.device_type == "switch" and d.has_vlan_config]
    if switches_with_vlans:
        router_refs = {d.save_ref for d in devices if d.device_type == "router" and d.save_ref}

        has_router_in_topology = False
        for sw in switches_with_vlans:
            if not sw.save_ref:
                continue
            segment = _switch_segment(sw.save_ref, adjacency, by_ref)
            if router_refs & segment:
                has_router_in_topology = True
                break

        if not has_router_in_topology:
            for sw in switches_with_vlans[:1]:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="VLAN_NO_ROUTER",
                        title="VLAN configurate ma nessun router raggiungibile",
                        message=f"{sw.name} ha configurazione VLAN ma nessun router e' collegato allo switch direttamente o tramite altri switch. Il routing inter-VLAN non e' possibile.",
                        device=sw.name,
                        suggestion="Collega un router allo switch configurando un'interfaccia trunk o subinterfacce con 'encapsulation dot1q'.",
                    )
                )
                break

    for device in devices:
        if device.device_type != "router":
            continue
        config_data = _parse_running_config_detailed(device.running_config_lines)
        subifaces = config_data["subinterfaces"]
        for siface, encap in subifaces.items():
            if encap is None:
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="SUBFACE_NO_ENCAPSULATION",
                        title="Subinterfaccia senza encapsulation dot1q",
                        message=f"{device.name} {siface} e' una subinterfaccia ma non ha 'encapsulation dot1q' configurato.",
                        device=device.name,
                        interface=siface,
                        suggestion="Configura 'encapsulation dot1q <vlan-id>' sulla subinterfaccia per abilitare il routing inter-VLAN (Router-on-a-Stick).",
                    )
                )


def _analyze_dhcp_topology(devices: list[DeviceInfo], links: list[dict[str, str]], issues: list[PktAnalysisIssue]) -> None:
    by_ref = {d.save_ref: d for d in devices if d.save_ref}
    adjacency: dict[str, set[str]] = defaultdict(set)
    for link in links:
        if link["from"] and link["to"]:
            adjacency[link["from"]].add(link["to"])
            adjacency[link["to"]].add(link["from"])

    dhcp_servers = [(d, _collect_dhcp_capable_networks([d])) for d in devices if d.has_server_dhcp]

    if dhcp_servers and len(dhcp_servers) >= 2:
        for i in range(len(dhcp_servers)):
            for j in range(i + 1, len(dhcp_servers)):
                dev_a, nets_a = dhcp_servers[i]
                dev_b, nets_b = dhcp_servers[j]
                shared = nets_a & nets_b
                if shared:
                    issues.append(
                        PktAnalysisIssue(
                            severity="warning",
                            code="MULTIPLE_DHCP_SERVERS",
                            title="Server DHCP multipli sulla stessa rete",
                            message=f"{dev_a.name} e {dev_b.name} possono entrambi servire DHCP sulla stessa subnet {', '.join(sorted(shared))}. Possibile conflitto di indirizzi.",
                            suggestion="Configura un solo server DHCP per subnet o usa DHCP pooling con indirizzi mutualmente esclusivi.",
                        )
                    )

    for device in devices:
        if device.device_type != "router":
            continue
        config_data = _parse_running_config_detailed(device.running_config_lines)
        if not config_data["has_dhcp_pool"]:
            continue

        for pool_name in config_data["dhcp_pool_names"]:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="DHCP_POOL_CONFIGURED",
                    title="Pool DHCP configurato sul router",
                    message=f"{device.name} ha un pool DHCP '{pool_name}'. Verifica che la rete del pool corrisponda alla subnet dell'interfaccia LAN.",
                    device=device.name,
                    suggestion="Assicurati che il comando 'network' nel pool DHCP corrisponda alla subnet della LAN collegata.",
                )
            )


def _analyze_routing(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    for device in devices:
        if device.device_type != "router":
            continue

        config_data = _parse_running_config_detailed(device.running_config_lines)
        routing = config_data["routing"]
        if not isinstance(routing, dict):
            continue

        router_nets = set()
        for port in device.ports:
            net = _safe_network(port.ip, port.subnet)
            if net:
                router_nets.add(str(net))

        rip_data = routing.get("rip")
        if isinstance(rip_data, dict):
            ver = rip_data.get("version")
            if ver != "2":
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="RIP_VERSION_NOT_SET",
                        title="RIP versione non impostata a 2",
                        message=f"{device.name} ha 'router rip' configurato ma non usa 'version 2'. RIP v1 e' classful e non supporta VLSM.",
                        device=device.name,
                        suggestion="Aggiungi il comando 'version 2' sotto 'router rip' per supportare subnetting VLSM e CIDR.",
                    )
                )
            rip_nets = rip_data.get("networks", [])
            if not rip_nets and router_nets:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="RIP_NO_NETWORKS",
                        title="RIP senza network statements",
                        message=f"{device.name} ha 'router rip' ma nessun comando 'network'. Le interfacce non parteciperanno al routing RIP.",
                        device=device.name,
                        suggestion="Aggiungi comandi 'network <indirizzo-rete>' per ogni interfaccia che deve partecipare a RIP.",
                    )
                )

        ospf_data = routing.get("ospf")
        if isinstance(ospf_data, dict):
            ospf_nets = ospf_data.get("networks", [])
            if not ospf_nets:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="OSPF_NO_NETWORKS",
                        title="OSPF senza network statements",
                        message=f"{device.name} ha 'router ospf' ma nessun comando 'network'. Le interfacce non parteciperanno al routing OSPF.",
                        device=device.name,
                        suggestion="Aggiungi comandi 'network <ip> <wildcard> area <id>' per ogni interfaccia che deve partecipare a OSPF.",
                    )
                )

        eigrp_data = routing.get("eigrp")
        if isinstance(eigrp_data, dict):
            eigrp_nets = eigrp_data.get("networks", [])
            if not eigrp_nets:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="EIGRP_NO_NETWORKS",
                        title="EIGRP senza network statements",
                        message=f"{device.name} ha 'router eigrp' ma nessun comando 'network'. Le interfacce non parteciperanno al routing EIGRP.",
                        device=device.name,
                        suggestion="Aggiungi comandi 'network <ip> <wildcard>' per ogni interfaccia che deve partecipare a EIGRP.",
                    )
                )

        multi_router = len([d for d in devices if d.device_type == "router"]) > 1
        has_wan = any(p.name and "serial" in p.name.lower() for p in device.ports)

        if (multi_router or has_wan) and not config_data["has_default_route"] and not routing:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="NO_DEFAULT_ROUTE",
                    title="Rotta predefinita mancante",
                    message=f"{device.name} non ha una rotta predefinita (ip route 0.0.0.0 0.0.0.0). Se questo router deve raggiungere Internet, serve una default route.",
                    device=device.name,
                    suggestion="Configura 'ip route 0.0.0.0 0.0.0.0 <next-hop-ip>' per instradare il traffico verso reti sconosciute.",
                )
            )


def _analyze_nat(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    for device in devices:
        if device.device_type != "router":
            continue

        config_data = _parse_running_config_detailed(device.running_config_lines)
        nat_inside = config_data["nat_inside_interfaces"]
        nat_outside = config_data["nat_outside_interfaces"]
        has_static = config_data["has_static_nat"]
        has_dynamic = config_data["has_dynamic_nat"]
        has_overload = config_data["has_nat_overload"]
        nat_acls = config_data["nat_acls"]
        nat_pools = config_data["nat_pools"]
        access_entries = config_data["access_list_entries"]

        any_nat_config = has_static or has_dynamic or has_overload or bool(nat_pools) or bool(nat_acls)
        if not any_nat_config:
            continue

        issues.append(
            PktAnalysisIssue(
                severity="info",
                code="NAT_CONFIGURED",
                title="NAT configurato sul router",
                message=f"{device.name} ha configurazione NAT. Verifica che inside/outside siano corretti.",
                device=device.name,
                suggestion="Assicurati che 'ip nat inside' sia sulle interfacce LAN e 'ip nat outside' sull'interfaccia WAN/Internet.",
            )
        )

        if not nat_inside and not nat_outside:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="NAT_MISSING_INTERFACE_DIRECTION",
                    title="NAT senza interfacce inside/outside",
                    message=f"{device.name} ha comandi NAT ma nessuna interfaccia con 'ip nat inside' o 'ip nat outside'.",
                    device=device.name,
                    suggestion="Configura 'ip nat inside' sulle interfacce LAN e 'ip nat outside' sull'interfaccia WAN/Internet.",
                )
            )
        elif not nat_inside:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="NAT_MISSING_INSIDE",
                    title="NAT senza interfaccia inside",
                    message=f"{device.name} ha NAT configurato ma nessuna interfaccia 'ip nat inside'. Le reti LAN non verranno tradotte.",
                    device=device.name,
                    suggestion="Aggiungi 'ip nat inside' sulle interfacce delle reti private.",
                )
            )
        elif not nat_outside:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="NAT_MISSING_OUTSIDE",
                    title="NAT senza interfaccia outside",
                    message=f"{device.name} ha NAT configurato ma nessuna interfaccia 'ip nat outside'. Il traffico non uscira' verso l'esterno.",
                    device=device.name,
                    suggestion="Aggiungi 'ip nat outside' sull'interfaccia collegata a Internet/WAN.",
                )
            )

        for acl_ref in nat_acls:
            if acl_ref not in access_entries and not acl_ref.startswith("?"):
                issues.append(
                    PktAnalysisIssue(
                        severity="error",
                        code="NAT_ACL_MISSING",
                        title="ACL per NAT non definita",
                        message=f"{device.name} usa 'ip nat inside source list {acl_ref}' ma l'access-list {acl_ref} non esiste. Nessun traffico verra' tradotto.",
                        device=device.name,
                        suggestion="Definisci 'access-list {acl_ref} permit ip <LAN> <wildcard> any' per abilitare la traduzione NAT.",
                    )
                )

        if has_nat_overload and not nat_acls:
            issues.append(
                PktAnalysisIssue(
                    severity="warning",
                    code="NAT_OVERLOAD_NO_ACL",
                    title="NAT Overload senza ACL",
                    message=f"{device.name} usa NAT overload (PAT) ma non c'e' una access-list che definisca il traffico da tradurre.",
                    device=device.name,
                    suggestion="Aggiungi 'access-list <num> permit ip <rete-lan> <wildcard> any' e referenziala con 'ip nat inside source list <num> interface <wan> overload'.",
                )
            )

        if nat_pools and not has_dynamic_nat:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="NAT_POOL_UNUSED",
                    title="Pool NAT definito ma non utilizzato",
                    message=f"{device.name} definisce 'ip nat pool {' '.join(nat_pools)}' ma non c'e' 'ip nat inside source list ... pool ...' che lo usi.",
                    device=device.name,
                    suggestion="Collega il pool a una access-list con 'ip nat inside source list <acl> pool <nome-pool>'.",
                )
            )


def _analyze_security(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    for device in devices:
        if device.device_type != "router":
            continue

        config_data = _parse_running_config_detailed(device.running_config_lines)

        if not config_data["has_enable_secret"]:
            if config_data["has_enable_password"]:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="ENABLE_PASSWORD_WEAK",
                        title="Enable password non cifrata",
                        message=f"{device.name} usa 'enable password' (in chiaro) invece di 'enable secret' (cifrato).",
                        device=device.name,
                        suggestion="Usa 'enable secret <password>' invece di 'enable password' per proteggere l'accesso privilegiato.",
                    )
                )
            else:
                issues.append(
                    PktAnalysisIssue(
                        severity="warning",
                        code="NO_ENABLE_SECRET",
                        title="Accesso privilegiato non protetto",
                        message=f"{device.name} non ha 'enable secret' ne' 'enable password' configurati.",
                        device=device.name,
                        suggestion="Configura 'enable secret <password>' per proteggere la modalita' privilegiata.",
                    )
                )

        if not config_data["has_banner"]:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="NO_BANNER",
                    title="Banner di accesso assente",
                    message=f"{device.name} non ha un banner MOTD configurato.",
                    device=device.name,
                    suggestion="Configura 'banner motd # Messaggio di avviso #' per scopi legali e informativi.",
                )
            )

        if not config_data["has_password_encryption"]:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="NO_PASSWORD_ENCRYPTION",
                    title="Cifratura password non abilitata",
                    message=f"{device.name} non usa 'service password-encryption'. Le password nella configurazione sono in chiaro.",
                    device=device.name,
                    suggestion="Configura 'service password-encryption' per cifrare le password nel file di configurazione.",
                )
            )

        if config_data["has_domain_lookup"]:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="DNS_LOOKUP_ENABLED",
                    title="DNS lookup abilitato di default",
                    message=f"{device.name} ha 'ip domain-lookup' abilitato. I comandi sbagliati causano attese per risoluzione DNS.",
                    device=device.name,
                    suggestion="Configura 'no ip domain-lookup' per evitare attese quando si digitano comandi errati.",
                )
            )

        if config_data["vty_transport_ssh"] and not config_data["has_ssh_config"]:
            issues.append(
                PktAnalysisIssue(
                    severity="error",
                    code="SSH_NOT_CONFIGURED",
                    title="VTY richiede SSH ma SSH non e' configurato",
                    message=f"{device.name} ha 'transport input ssh' sulle linee VTY ma non ha 'ip ssh' configurato.",
                    device=device.name,
                    suggestion="Configura 'ip domain-name <dominio>', genera le chiavi RSA con 'crypto key generate rsa', e abilita 'ip ssh'.",
                )
            )


def _analyze_switch_configs(devices: list[DeviceInfo], issues: list[PktAnalysisIssue]) -> None:
    for device in devices:
        if device.device_type != "switch":
            continue

        if not device.ports:
            continue

        config_lines = "\n".join(device.running_config_lines).lower()

        has_trunk = "switchport mode trunk" in config_lines
        has_access_ports = not has_trunk and len(device.ports) > 0
        has_portfast = "spanning-tree portfast" in config_lines
        has_vlan_config = device.has_vlan_config
        has_trunk_allowed = "switchport trunk allowed vlan" in config_lines

        if has_trunk and not has_trunk_allowed:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="TRUNK_ALLOWS_ALL_VLANS",
                    title="Trunk permette tutte le VLAN",
                    message=f"{device.name} ha porte trunk ma senza 'switchport trunk allowed vlan'. Tutte le VLAN attraversano il trunk.",
                    device=device.name,
                    suggestion="Configura 'switchport trunk allowed vlan <elenco-vlan>' per limitare le VLAN sul trunk.",
                )
            )

        if has_access_ports and not has_portfast:
            issues.append(
                PktAnalysisIssue(
                    severity="info",
                    code="NO_PORTFAST",
                    title="PortFast non configurato sugli access port",
                    message=f"{device.name} ha access port ma 'spanning-tree portfast' non e' configurato. L'avvio dei dispositivi sara' piu' lento.",
                    device=device.name,
                    suggestion="Configura 'spanning-tree portfast' sulle porte di accesso per evitare ritardi all'accensione dei dispositivi.",
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
    sorted_issues = sorted(issues, key=lambda i: (0 if i.severity == "error" else 1 if i.severity == "warning" else 2, i.title))
    for index, issue in enumerate(sorted_issues, start=1):
        location = " - ".join(part for part in [issue.device, issue.interface] if part)
        header = f"{index}. [{issue.severity.upper()}] {issue.title}"
        if location:
            header += f" ({location})"
        lines.append(header)
        lines.append(issue.message)
        if issue.suggestion:
            lines.append(f"--> {issue.suggestion}")
        lines.append("")
    return "\n".join(lines).strip()


def _build_remediation_steps(issues: list[PktAnalysisIssue]) -> list[str]:
    seen: set[str] = set()
    steps: list[str] = []
    for issue in issues:
        candidate = (issue.suggestion or issue.message or "").strip()
        if not candidate:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        steps.append(candidate)
    return steps[:15]
