#!/usr/bin/env python3
"""Script di test per generare file .pkt di esempio"""

import sys
import os

# Aggiungi la directory nettrace al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nettrace.schemas import NetworkConfig, SubnetRequest, DeviceCount, RoutingProtocol
from nettrace.vlsm import calculate_vlsm
from nettrace.xml_generator import create_pkt_xml, save_as_pkt, save_raw_xml

def test_simple_network():
    """Test: Rete semplice con 1 router, 1 switch, 1 PC"""
    print("⚡ Test 1: Rete semplice (R1 + S1 + PC1)")
    
    # Configurazione
    config = NetworkConfig(
        base_network="192.168.1.0/24",
        subnets=[
            SubnetRequest(name="LAN1", required_hosts=50)
        ],
        devices=DeviceCount(routers=1, switches=1, pcs=1),
        routing_protocol=RoutingProtocol.STATIC
    )
    
    # Calcola subnet
    subnets = calculate_vlsm(config.base_network, config.subnets)
    print(f"✅ Subnet calcolata: {subnets[0].network}")
    print(f"   Gateway: {subnets[0].gateway}")
    print(f"   Mask: {subnets[0].mask}")
    
    # Genera XML
    xml_content = create_pkt_xml(config, subnets)
    print(f"✅ XML generato ({len(xml_content)} caratteri)")
    
    # Salva file
    save_raw_xml(xml_content, "example_network.xml")
    print("✅ Salvato: example_network.xml")
    
    save_as_pkt(xml_content, "example_network.pkt")
    print("✅ Salvato: example_network.pkt")
    
    print("\n✓ Test completato! Apri example_network.pkt in Packet Tracer.\n")

def test_multi_pc():
    """Test: Rete con 3 PC"""
    print("⚡ Test 2: Rete con 3 PC")
    
    config = NetworkConfig(
        base_network="192.168.0.0/22",
        subnets=[
            SubnetRequest(name="VLAN10", required_hosts=100)
        ],
        devices=DeviceCount(routers=1, switches=1, pcs=3),
        routing_protocol=RoutingProtocol.RIP
    )
    
    subnets = calculate_vlsm(config.base_network, config.subnets)
    xml_content = create_pkt_xml(config, subnets)
    
    save_as_pkt(xml_content, "multi_pc_network.pkt")
    print("✅ Salvato: multi_pc_network.pkt")
    print("\n✓ Test completato!\n")

if __name__ == "__main__":
    print("📦 NetTrace - Test Generatore PKT\n")
    print("="*50)
    
    try:
        test_simple_network()
        test_multi_pc()
        print("✅ Tutti i test completati con successo!")
        print("\n📂 File generati:")
        print("  - example_network.xml (XML non compresso per debug)")
        print("  - example_network.pkt (File Packet Tracer)")
        print("  - multi_pc_network.pkt (File Packet Tracer con 3 PC)")
        print("\n🚀 Apri i file .pkt in Cisco Packet Tracer 8.x")
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
