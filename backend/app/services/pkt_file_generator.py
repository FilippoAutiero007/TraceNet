"""
PKT File Generator Service - Generates Cisco Packet Tracer .pkt files (XML+GZIP)

IMPORTANTE: I file .pkt NON sono file di testo!
Sono file XML compressi con GZIP (binari).
"""

import xml.etree.ElementTree as ET
import gzip
import os
from datetime import datetime
from typing import List, Tuple
from app.models.schemas import NetworkConfig, SubnetResult, RoutingProtocol


def generate_router_config(hostname: str, subnets: List[SubnetResult], protocol: RoutingProtocol) -> str:
    """Genera configurazione IOS per router"""
    lines = [
        f"hostname {hostname}",
        "!",
        "enable secret cisco",
        "service password-encryption",
        "!",
    ]
    
    # Configura interfacce per ogni subnet
    for i, subnet in enumerate(subnets[:2]):  # Max 2 interfacce per Router 1841
        lines.extend([
            f"interface FastEthernet0/{i}",
            f" description LAN_{subnet.name}",
            f" ip address {subnet.gateway} {subnet.mask}",
            " no shutdown",
            "!",
        ])
    
    # Routing protocols
    if protocol == RoutingProtocol.RIP:
        lines.extend([
            "router rip",
            " version 2",
            " no auto-summary",
        ])
        for subnet in subnets:
            net_addr = subnet.network.split('/')[0]
            lines.append(f" network {net_addr}")
        lines.append("!")
        
    elif protocol == RoutingProtocol.OSPF:
        lines.extend(["router ospf 1"])
        for subnet in subnets:
            net_addr = subnet.network.split('/')[0]
            mask_octets = subnet.mask.split('.')
            wildcard = ".".join([str(255 - int(o)) for o in mask_octets])
            lines.append(f" network {net_addr} {wildcard} area 0")
        lines.append("!")
        
    elif protocol == RoutingProtocol.EIGRP:
        lines.extend(["router eigrp 100"])
        for subnet in subnets:
            net_addr = subnet.network.split('/')[0]
            lines.append(f" network {net_addr}")
        lines.extend([" no auto-summary", "!"])
    
    # Console and VTY
    lines.extend([
        "line con 0",
        " password cisco",
        " login",
        "!",
        "line vty 0 4",
        " password cisco",
        " login",
        "!",
        "end",
    ])
    
    return "\n".join(lines)


def generate_switch_config(hostname: str) -> str:
    """Genera configurazione IOS base per switch"""
    return f"""hostname {hostname}
!
enable secret cisco
!
line con 0
 password cisco
 login
!
line vty 0 4
 password cisco
 login
!
end"""


def create_pkt_xml(config: NetworkConfig, subnets: List[SubnetResult]) -> str:
    """
    Crea XML completo per file .pkt di Cisco Packet Tracer 8.x
    
    Args:
        config: Configurazione di rete parsata
        subnets: Lista subnet calcolate con VLSM
        
    Returns:
        Stringa XML formattata
    """
    root = ET.Element("PACKETTRACER5")
    
    # Network node con attributi obbligatori per PT 8.x
    network = ET.SubElement(root, "NETWORK")
    network.set("version", "8.2.1")
    network.set("nodename", "localhost")
    network.set("locale", "en_US")
    
    devices_node = ET.SubElement(network, "DEVICES")
    cables_node = ET.SubElement(network, "CABLES")
    
    device_id = 0
    cable_id = 0
    
    # Layout: Router in alto, Switch al centro, PC in basso
    router_y = 100
    switch_y = 250
    pc_y = 400
    
    # 1. Aggiungi Router
    router_ids = []
    for r in range(config.devices.routers):
        r_id = f"dev_{device_id}"
        router_ids.append(r_id)
        device_id += 1
        
        router = ET.SubElement(devices_node, "DEVICE")
        router.set("id", r_id)
        router.set("deviceType", "Router1841")
        router.set("hostname", f"R{r+1}")
        router.set("x", str(300 + r * 200))
        router.set("y", str(router_y))
        router.set("icon", "router.png")
        
        # Porte router
        ports_node = ET.SubElement(router, "PORTS")
        for i in range(2):
            port = ET.SubElement(ports_node, "PORT")
            port.set("type", "FastEthernet")
            port.set("number", f"0/{i}")
        
        # Configurazione IOS router
        config_node = ET.SubElement(router, "CONFIG")
        ios_config = ET.SubElement(config_node, "IOS_CONFIG")
        ios_config.text = generate_router_config(f"R{r+1}", subnets, config.routing_protocol)
    
    # 2. Aggiungi Switch
    switch_ids = []
    for s in range(max(1, config.devices.switches)):
        s_id = f"dev_{device_id}"
        switch_ids.append(s_id)
        device_id += 1
        
        switch = ET.SubElement(devices_node, "DEVICE")
        switch.set("id", s_id)
        switch.set("deviceType", "Switch2960")
        switch.set("hostname", f"S{s+1}")
        switch.set("x", str(200 + s * 250))
        switch.set("y", str(switch_y))
        switch.set("icon", "switch.png")
        
        # Porte switch
        ports_node_s = ET.SubElement(switch, "PORTS")
        for i in range(1, 25):  # FastEthernet 0/1-24
            port = ET.SubElement(ports_node_s, "PORT")
            port.set("type", "FastEthernet")
            port.set("number", f"0/{i}")
        for i in range(1, 3):  # GigabitEthernet uplink
            port_g = ET.SubElement(ports_node_s, "PORT")
            port_g.set("type", "GigabitEthernet")
            port_g.set("number", f"0/{i}")
        
        # Configurazione IOS switch
        s_config_node = ET.SubElement(switch, "CONFIG")
        s_ios_config = ET.SubElement(s_config_node, "IOS_CONFIG")
        s_ios_config.text = generate_switch_config(f"S{s+1}")
    
    # 3. Collega Router a Switch
    if router_ids and switch_ids:
        for i, r_id in enumerate(router_ids):
            if i < len(switch_ids):
                cable = ET.SubElement(cables_node, "CABLE")
                cable.set("id", f"cable_{cable_id}")
                cable.set("fromDevice", r_id)
                cable.set("fromPort", "FastEthernet0/0")
                cable.set("toDevice", switch_ids[i])
                cable.set("toPort", "FastEthernet0/1")
                cable.set("type", "Copper Straight-Through")
                cable_id += 1
    
    # 4. Aggiungi PC
    pc_port_idx = 2  # Inizia da FastEthernet0/2 sullo switch
    for p in range(config.devices.pcs):
        pc_id = f"dev_{device_id}"
        device_id += 1
        
        pc = ET.SubElement(devices_node, "DEVICE")
        pc.set("id", pc_id)
        pc.set("deviceType", "PC-PT")
        pc.set("hostname", f"PC{p+1}")
        pc.set("x", str(100 + (p % 6) * 120))  # 6 PC per riga
        pc.set("y", str(pc_y + (p // 6) * 80))
        pc.set("icon", "pc.png")
        
        # Porta PC
        ports_node_pc = ET.SubElement(pc, "PORTS")
        port_pc = ET.SubElement(ports_node_pc, "PORT")
        port_pc.set("type", "FastEthernet")
        port_pc.set("number", "0")
        
        # Configurazione IP PC
        config_node_pc = ET.SubElement(pc, "CONFIG")
        pc_config = ET.SubElement(config_node_pc, "PC_CONFIG")
        
        if subnets:
            # Assegna PC alle subnet round-robin
            subnet_idx = p % len(subnets)
            subnet = subnets[subnet_idx]
            
            # Calcola IP
            network_parts = subnet.network.split('/')[0].split('.')
            pc_ip = f"{network_parts[0]}.{network_parts[1]}.{network_parts[2]}.{10 + (p // len(subnets))}"
            
            ip_elem = ET.SubElement(pc_config, "IP")
            ip_elem.text = pc_ip
            
            mask_elem = ET.SubElement(pc_config, "MASK")
            mask_elem.text = subnet.mask
            
            gateway_elem = ET.SubElement(pc_config, "GATEWAY")
            gateway_elem.text = subnet.gateway
        
        # Collega PC allo switch (distribuisci tra switch disponibili)
        if switch_ids:
            switch_idx = p % len(switch_ids)
            switch_to_use = switch_ids[switch_idx]
            
            cable = ET.SubElement(cables_node, "CABLE")
            cable.set("id", f"cable_{cable_id}")
            cable.set("fromDevice", switch_to_use)
            cable.set("fromPort", f"FastEthernet0/{pc_port_idx + (p // len(switch_ids))}")
            cable.set("toDevice", pc_id)
            cable.set("toPort", "FastEthernet0")
            cable.set("type", "Copper Straight-Through")
            cable_id += 1
    
    # Serializza XML
    return ET.tostring(root, encoding="unicode", method="xml")


def save_pkt_file(xml_content: str, output_dir: str = "/tmp") -> Tuple[str, str]:
    """
    Salva XML come file .pkt (compresso GZIP) e .xml (debug)
    
    IMPORTANTE: Il file .pkt è BINARIO (XML compresso con GZIP)
    NON è un file di testo!
    
    Args:
        xml_content: Stringa XML della rete
        output_dir: Directory di output
        
    Returns:
        Tuple (path_pkt, path_xml)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pkt_path = os.path.join(output_dir, f"network_{timestamp}.pkt")
    xml_path = os.path.join(output_dir, f"network_{timestamp}.xml")
    
    # Aggiungi header XML
    if not xml_content.startswith('<?xml'):
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
    
    # Valida e formatta XML
    try:
        tree = ET.fromstring(xml_content.encode('utf-8'))
        ET.indent(tree, space="  ", level=0)
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(tree, encoding='unicode', method='xml')
    except Exception:
        pass  # Usa XML originale se validazione fallisce
    
    # Salva .pkt (GZIP binario)
    with gzip.open(pkt_path, 'wb') as f:
        f.write(xml_content.encode('utf-8'))
    
    # Salva .xml (testo per debug)
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    return pkt_path, xml_path


def verify_pkt_file(filepath: str) -> bool:
    """
    Verifica che un file .pkt sia correttamente compresso con GZIP
    
    Args:
        filepath: Path al file .pkt
        
    Returns:
        True se il file è un GZIP valido con contenuto XML
    """
    try:
        with gzip.open(filepath, 'rb') as f:
            content = f.read()
            return b'<PACKETTRACER5>' in content or b'<NETWORK>' in content
    except Exception:
        return False
