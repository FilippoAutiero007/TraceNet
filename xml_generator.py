import xml.etree.ElementTree as ET
import gzip
import os
from typing import List
from .schemas import NetworkConfig, SubnetResult
from .config_generator import generate_router_config, generate_switch_config

def add_cable(cables_node, cable_id: int, from_dev_id: str, from_port: str,
              to_dev_id: str, to_port: str):
    """Aggiunge un cavo tra due dispositivi"""
    cable = ET.SubElement(cables_node, "CABLE")
    cable.set("id", f"cable_{cable_id}")
    cable.set("fromDevice", from_dev_id)
    cable.set("fromPort", from_port)
    cable.set("toDevice", to_dev_id)
    cable.set("toPort", to_port)
    cable.set("type", "Copper Straight-Through")

def create_pkt_xml(config: NetworkConfig, subnets: List[SubnetResult]) -> str:
    """Crea XML completo per file .pkt di Packet Tracer"""
    root = ET.Element("PACKETTRACER5")
    
    # Network node con attributi obbligatori
    network = ET.SubElement(root, "NETWORK")
    network.set("version", "8.2.1")
    network.set("nodename", "localhost")  # CORRETTO: aggiunto
    network.set("locale", "en_US")        # CORRETTO: aggiunto
    
    devices_node = ET.SubElement(network, "DEVICES")
    cables_node = ET.SubElement(network, "CABLES")
    
    # 1. Add Router (R1) - Usa Router1841 con FastEthernet
    r1_id = "dev_0"
    r1 = ET.SubElement(devices_node, "DEVICE")
    r1.set("id", r1_id)
    r1.set("deviceType", "Router1841")  # CORRETTO: 1841 ha FastEthernet
    r1.set("hostname", "R1")
    r1.set("x", "100")
    r1.set("y", "100")
    r1.set("icon", "router.png")
    
    # CORRETTO: Aggiungi porte router (DEVONO essere nel tag DEVICE)
    ports_node = ET.SubElement(r1, "PORTS")
    for i in range(2):  # FastEthernet 0/0 e 0/1
        port = ET.SubElement(ports_node, "PORT")
        port.set("type", "FastEthernet")
        port.set("number", f"0/{i}")
    
    # Aggiungi configurazione router
    config_node = ET.SubElement(r1, "CONFIG")
    ios_config = ET.SubElement(config_node, "IOS_CONFIG")
    ios_config.text = generate_router_config("R1", subnets, config.routing_protocol)
    
    # 2. Add Switch (S1)
    s1_id = "dev_1"
    s1 = ET.SubElement(devices_node, "DEVICE")
    s1.set("id", s1_id)
    s1.set("deviceType", "Switch2960")  # Switch2960-24TT
    s1.set("hostname", "S1")
    s1.set("x", "100")
    s1.set("y", "250")
    s1.set("icon", "switch.png")
    
    # CORRETTO: Aggiungi porte switch
    ports_node_s = ET.SubElement(s1, "PORTS")
    for i in range(1, 25):  # FastEthernet 0/1 to 0/24
        port = ET.SubElement(ports_node_s, "PORT")
        port.set("type", "FastEthernet")
        port.set("number", f"0/{i}")
    
    # GigabitEthernet uplink
    for i in range(1, 3):  # GigabitEthernet 0/1 e 0/2
        port_g = ET.SubElement(ports_node_s, "PORT")
        port_g.set("type", "GigabitEthernet")
        port_g.set("number", f"0/{i}")
    
    # Configurazione switch
    s_config_node = ET.SubElement(s1, "CONFIG")
    s_ios_config = ET.SubElement(s_config_node, "IOS_CONFIG")
    s_ios_config.text = generate_switch_config("S1")
    
    # Connect R1 to S1
    add_cable(cables_node, 0, r1_id, "FastEthernet0/0", s1_id, "FastEthernet0/1")
    
    # 3. Add PCs
    for i in range(config.devices.pcs):
        pc_id = f"dev_{i+2}"
        pc = ET.SubElement(devices_node, "DEVICE")
        pc.set("id", pc_id)
        pc.set("deviceType", "PC-PT")
        pc.set("hostname", f"PC{i+1}")
        pc.set("x", str(250 + (i * 100)))
        pc.set("y", "250")
        pc.set("icon", "pc.png")
        
        # CORRETTO: Aggiungi porta PC
        ports_node_pc = ET.SubElement(pc, "PORTS")
        port_pc = ET.SubElement(ports_node_pc, "PORT")
        port_pc.set("type", "FastEthernet")
        port_pc.set("number", "0")
        
        # CORRETTO: Aggiungi configurazione IP completa
        config_node_pc = ET.SubElement(pc, "CONFIG")
        pc_config = ET.SubElement(config_node_pc, "PC_CONFIG")
        
        if subnets:
            subnet = subnets[0]
            # Calcola IP dinamicamente
            network_parts = str(subnet.network).split('/')
            base_ip = network_parts[0].split('.')
            pc_ip = f"{base_ip[0]}.{base_ip[1]}.{base_ip[2]}.{10 + i}"
            
            # CORRETTO: Tag IP, MASK, GATEWAY come testo
            ip_elem = ET.SubElement(pc_config, "IP")
            ip_elem.text = pc_ip
            
            mask_elem = ET.SubElement(pc_config, "MASK")
            mask_elem.text = str(subnet.mask)
            
            gateway_elem = ET.SubElement(pc_config, "GATEWAY")
            gateway_elem.text = str(subnet.gateway)
        
        # Connect PC to Switch
        add_cable(cables_node, i + 1, s1_id, f"FastEthernet0/{i+2}", pc_id, "FastEthernet0")
    
    # CORRETTO: Usa metodo 'xml' per serializzazione completa
    return ET.tostring(root, encoding="unicode", method="xml")

def save_as_pkt(xml_content: str, filepath: str):
    """Salva XML come file .pkt compresso con gzip"""
    # Aggiungi header XML se mancante
    if not xml_content.startswith('<?xml'):
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
    
    # CORRETTO: Valida e ri-serializza per garantire formato corretto
    try:
        tree = ET.fromstring(xml_content.encode('utf-8'))
        # Re-serialize con indentazione (opzionale, per debug)
        ET.indent(tree, space="  ", level=0)  # Python 3.9+
        xml_content = ET.tostring(tree, encoding='unicode', method='xml')
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
    except ET.ParseError as e:
        raise ValueError(f"XML non valido: {e}")
    except AttributeError:
        # Python < 3.9 non ha ET.indent
        pass
    
    # Comprimi con gzip
    with gzip.open(filepath, 'wb') as f:
        f.write(xml_content.encode('utf-8'))

def save_raw_xml(xml_content: str, filepath: str):
    """Salva XML non compresso per debug"""
    if not xml_content.startswith('<?xml'):
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(xml_content)
