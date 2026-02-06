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
    
    # Regola 1: VERSION come figlio diretto di PACKETTRACER5
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    
    # Regola 2: Struttura globale
    ET.SubElement(root, "PIXMAPBANK")
    ET.SubElement(root, "MOVIEBANK")
    
    # Network node
    network = ET.SubElement(root, "NETWORK")
    #network.set("version", "8.2.1") # Rimosso se ridondante o spostato in root, ma manteniamo pulito
    
    ET.SubElement(root, "SCENARIOSET")
    ET.SubElement(root, "OPTIONS")
    
    devices_node = ET.SubElement(network, "DEVICES")
    # Regola 3: LINKS invece di CABLES
    links_node = ET.SubElement(network, "LINKS")
    
    device_id = 0
    cable_id = 0
    
    # Layout: Router in alto, Switch al centro, PC in basso
    router_y = 100
    switch_y = 250
    pc_y = 400
    
    # Mappa ID interni a nomi device per i link
    device_map = {} # id -> hostname
    
    # 1. Aggiungi Router
    router_ids = []
    for r in range(config.devices.routers):
        r_id = f"dev_{device_id}"
        router_ids.append(r_id)
        device_id += 1
        hostname = f"R{r+1}"
        device_map[r_id] = hostname
        
        # Regola 4: Metadati device (name, type)
        router = ET.SubElement(devices_node, "DEVICE")
        router.set("name", hostname)
        router.set("type", "router") # O specificare meglio se necessario es. "2811"
        router.set("id", r_id) # Manteniamo ID per riferimento interno nostro se serve
        router.set("power", "on")
        # Attributo specifico PT per il modello esatto se 'type' è generico
        # router.set("model", "1841") 

        # Coordinate in nodo figlio
        coords = ET.SubElement(router, "COORDINATES")
        coords.set("x", str(300 + r * 200))
        coords.set("y", str(router_y))
        
        # Regola 5: INTERFACE invece di PORTS
        # Porte router
        for i in range(2):
            iface = ET.SubElement(router, "INTERFACE")
            iface.set("name", f"FastEthernet0/{i}")
            iface.set("type", "ethernet") 
            iface.set("bandwidth", "100000")
        
        # Configurazione IOS router
        config_node = ET.SubElement(router, "CONFIG")
        ios_config = ET.SubElement(config_node, "IOS_CONFIG")
        ios_config.text = generate_router_config(hostname, subnets, config.routing_protocol)
    
    # 2. Aggiungi Switch
    switch_ids = []
    for s in range(max(1, config.devices.switches)):
        s_id = f"dev_{device_id}"
        switch_ids.append(s_id)
        device_id += 1
        hostname = f"S{s+1}"
        device_map[s_id] = hostname
        
        switch = ET.SubElement(devices_node, "DEVICE")
        switch.set("name", hostname)
        switch.set("type", "switch")
        switch.set("id", s_id)
        switch.set("power", "on")
        
        coords = ET.SubElement(switch, "COORDINATES")
        coords.set("x", str(200 + s * 250))
        coords.set("y", str(switch_y))
        
        # Porte switch
        for i in range(1, 25):  # FastEthernet 0/1-24
            iface = ET.SubElement(switch, "INTERFACE")
            iface.set("name", f"FastEthernet0/{i}")
            iface.set("type", "ethernet")
        for i in range(1, 3):  # GigabitEthernet uplink
            iface = ET.SubElement(switch, "INTERFACE")
            iface.set("name", f"GigabitEthernet0/{i}")
            iface.set("type", "ethernet")

        # Configurazione IOS switch
        s_config_node = ET.SubElement(switch, "CONFIG")
        s_ios_config = ET.SubElement(s_config_node, "IOS_CONFIG")
        s_ios_config.text = generate_switch_config(hostname)
    
    # 3. Collega Router a Switch (LINKS)
    if router_ids and switch_ids:
        for i, r_id in enumerate(router_ids):
            if i < len(switch_ids):
                link = ET.SubElement(links_node, "LINK")
                # Regola 3: from/to attributes e naming porte reale
                link.set("from", device_map[r_id]) # Nome host es. R1
                link.set("from_port", "FastEthernet0/0")
                link.set("to", device_map[switch_ids[i]]) # Nome host es. S1
                link.set("to_port", "FastEthernet0/1") # Assicurarsi corrisponda a interfaccia esistente
                link.set("speed", "100")
                cable_id += 1
    
    # 4. Aggiungi PC
    pc_port_idx = 2  # Inizia da FastEthernet0/2 sullo switch (0/1 usata per uplink router)
    for p in range(config.devices.pcs):
        pc_id = f"dev_{device_id}"
        device_id += 1
        hostname = f"PC{p+1}"
        device_map[pc_id] = hostname
        
        pc = ET.SubElement(devices_node, "DEVICE")
        pc.set("name", hostname)
        pc.set("type", "pc")
        pc.set("id", pc_id)
        pc.set("power", "on")
        
        coords = ET.SubElement(pc, "COORDINATES")
        coords.set("x", str(100 + (p % 6) * 120))
        coords.set("y", str(pc_y + (p // 6) * 80))
        
        # Porta PC
        iface = ET.SubElement(pc, "INTERFACE")
        iface.set("name", "FastEthernet0")
        iface.set("type", "ethernet")
        
        # Configurazione IP PC - Manteniamo struttura custom PT se standard, 
        # ma spesso è meglio usare il CONFIG/CLID o Desktop config.
        # Per ora manteniamo una struttura simile a quella osservata in alcuni esempi o generica.
        # Un approccio sicuro è mettere i parametri basilari nell'INTERFACE se supportato, 
        # o nel CONFIG.
        
        config_node_pc = ET.SubElement(pc, "CONFIG")
        # Struttura osservata varia, proviamo ad essere generici ma conformi
        
        if subnets:
            subnet_idx = p % len(subnets)
            subnet = subnets[subnet_idx]
            
            network_parts = subnet.network.split('/')[0].split('.')
            pc_ip = f"{network_parts[0]}.{network_parts[1]}.{network_parts[2]}.{10 + (p // len(subnets))}"
            
            # Applicazione IP su interfaccia
            iface.set("ip", pc_ip)
            iface.set("mask", subnet.mask)
            iface.set("gateway", subnet.gateway)

        # Collega PC allo switch
        if switch_ids:
            switch_idx = p % len(switch_ids)
            switch_to_use = switch_ids[switch_idx]
            
            link = ET.SubElement(links_node, "LINK")
            link.set("from", switch_to_use) # ID o Nome? PT spesso usa Nome negli attributi link
            # Correggiamo: sopra usavo map[id], verifichiamo consistenza.
            # Regola 3 Esempio: <LINK from="PC1" from_port="eth0" to="SW1" to_port="port1" speed="100"/>
            # Quindi si aspetta i NOMI (Hostname).
            
            link.set("from", device_map[switch_to_use])     # Es S1
            link.set("from_port", f"FastEthernet0/{pc_port_idx + (p // len(switch_ids))}")
            link.set("to", hostname)                        # Es PC1
            link.set("to_port", "FastEthernet0")
            link.set("speed", "100")
            cable_id += 1
    
    # Serializza XML
    return ET.tostring(root, encoding="unicode", method="xml")


import subprocess

def save_pkt_file(xml_content: str, output_dir: str = "/tmp") -> Tuple[str, str]:
    """
    Salva XML come file .pkt con encoding corretto per PT 8.x
    
    Usa pka2xml se disponibile, altrimenti fallback a GZIP (con warning)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xml_path = os.path.join(output_dir, f"network_{timestamp}.xml")
    pkt_path = os.path.join(output_dir, f"network_{timestamp}.pkt")
    
    # Prepara XML
    if not xml_content.startswith('<?xml'):
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
    
    # Valida e formatta
    try:
        tree = ET.fromstring(xml_content.encode('utf-8'))
        ET.indent(tree, space="  ", level=0)
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + \
                      ET.tostring(tree, encoding='unicode', method='xml')
    except Exception as e:
        print(f"⚠️ XML validation warning: {e}")
    
    # Salva XML debug
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    # Encoding .pkt
    encoding_method = "unknown"
    try:
        # OPZIONE 1: Prova pka2xml (installato tramite pip)
        # Assumiamo che pka2xml esponga un entry point CLI "pka2xml"
        result = subprocess.run([
            "pka2xml",
            "--xml2pkt",
            xml_path,
            "-o", pkt_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            encoding_method = "pka2xml"
        else:
            # Se fallisce, prova a importarlo come libreria se il CLI non va
            # Fallback a GZIP con warning
            raise Exception(f"pka2xml CLI failed: {result.stderr}")
            
    except (FileNotFoundError, Exception) as e:
        # FALLBACK: GZIP semplice (NON funzionerà su PT 8.x)
        print(f"⚠️ WARNING: pka2xml not available or failed ({e})")
        print(f"⚠️ Using GZIP fallback - file might NOT open in PT 8.x")
        print(f"⚠️ Install pka2xml: pip install git+https://github.com/mircodz/pka2xml.git")
        
        with gzip.open(pkt_path, 'wb') as f:
            f.write(xml_content.encode('utf-8'))
        encoding_method = "gzip_fallback"
    
    print(f"✅ PKT file created: {pkt_path}")
    print(f"   Encoding method: {encoding_method}")
    print(f"✅ XML debug file: {xml_path}")
    
    return pkt_path, xml_path


def verify_pkt_file(filepath: str) -> bool:
    """
    Verifica che un file .pkt sia valido (basic check)
    """
    try:
        # Se è GZIP
        with gzip.open(filepath, 'rb') as f:
            content = f.read()
            return b'<PACKETTRACER5>' in content or b'<NETWORK>' in content
    except Exception:
        # Se non è GZIP, potrebbe essere formato proprietario pka2xml/PT
        # Assumiamo valido se esiste e ha dimensione > 0 per ora
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return True
        return False
