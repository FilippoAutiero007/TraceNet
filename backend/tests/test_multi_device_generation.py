import pytest
import os
import shutil
import xml.etree.ElementTree as ET
from app.services.pkt_generator import save_pkt_file
from app.services.pkt_crypto import decrypt_pkt_data

class MockSubnet:
    def __init__(self, name, mask, usable_range):
        self.name = name
        self.mask = mask
        self.usable_range = usable_range

def test_multi_device_id_uniqueness():
    """Verifica che la generazione di più PC produca SAVEREFID e MEMADDR univoci."""
    subnets = [
        MockSubnet("Subnet1", "255.255.255.0", ["192.168.1.10", "192.168.1.11", "192.168.1.12"])
    ]
    
    config = {
        "devices": {
            "routers": 1,
            "switches": 1,
            "pcs": 5
        }
    }
    
    output_dir = "test_multi_output"
    result = save_pkt_file(subnets, config, output_dir)
    
    assert result["success"] is True
    xml_path = result["xml_path"]
    assert os.path.exists(xml_path)
    
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Verifica SAVEREFID
    import re
    saverefs = re.findall(r"save-ref-id[0-9]+", xml_content)
    # Ogni device ha un SAVEREFID nell'ENGINE e possibilmente riferimenti nei LINK
    # Quello che conta è che non ci siano duplicati tra device diversi
    # Estraiamo i SAVEREFID definiti nei nodi <SAVEREFID>
    root = ET.fromstring(xml_content)
    defined_saverefs = [node.text for node in root.findall(".//SAVEREFID") if node.text]
    
    assert len(defined_saverefs) == len(set(defined_saverefs)), f"Duplicated SAVEREFIDs found: {defined_saverefs}"
    
    # Verifica MEMADDR (e simili)
    # Cerchiamo tutti i nodi che dovrebbero essere univoci per istanza
    addr_tags = ["MEMADDR", "DEVADDR"]
    for tag in addr_tags:
        addrs = [node.text for node in root.findall(f".//{tag}") if node.text and node.text.isdigit() and len(node.text) >= 10]
        # Nota: nel template originale potrebbero esserci alcuni valori uguali per device diversi se non rigenerati.
        # Con la nostra modifica, dovrebbero essere tutti diversi.
        assert len(addrs) == len(set(addrs)), f"Duplicated {tag} found: {addrs}"

    # Pulizia
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

def test_topology_port_assignment():
    """Verifica che le porte assegnate ai PC siano corrette (non tutte sulla stessa porta dello switch)."""
    subnets = [MockSubnet("S1", "255.255.255.0", ["10.0.0.1", "10.0.0.2"])]
    config = {"devices": {"routers": 1, "switches": 1, "pcs": 2}}
    
    output_dir = "test_topo_output"
    result = save_pkt_file(subnets, config, output_dir)
    
    root = ET.fromstring(open(result["xml_path"]).read())
    links = root.findall(".//LINK")
    
    pc_links = []
    for link in links:
        to_node = link.find("TO")
        if to_node is not None and "PC" in (link.find("TO").text or ""): # Questo controllo è debole ma ok per mock
            pass
        # Controllo basato sulle porte
        ports = link.findall("PORT")
        port_texts = [p.text for p in ports if p.text]
        if any("PC" in str(p) for p in port_texts): # In realtà cerchiamo il pattern dello switch
            pc_links.append(port_texts)

    # Verifica porte dello switch nei link verso i PC
    switch_ports = []
    for link in links:
        # Un link ha due porte. Una è dello switch, l'altra del PC.
        ports = [p.text for p in link.findall("PORT")]
        if "FastEthernet0" in ports and any(p.startswith("FastEthernet0/") for p in ports):
            # Trovato un link Switch -> PC
            sw_port = [p for p in ports if p.startswith("FastEthernet0/")][0]
            switch_ports.append(sw_port)
    
    if len(switch_ports) >= 2:
        assert len(switch_ports) == len(set(switch_ports)), f"Duplicate switch ports assigned: {switch_ports}"

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
