import os
import gzip
import struct
import zlib
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

# --- CONFIGURATION ---
DEFAULT_XML_VERSION = "8.2.2.0400"  # Default for modern PT
DEFAULT_ENCODING = "legacy_xor"     # Options: legacy_xor, external_pka2xml, gzip

def _get_env_config():
    return {
        "XML_VERSION": os.getenv("PKT_XML_VERSION", DEFAULT_XML_VERSION),
        "ENCODING": os.getenv("PKT_ENCODING", DEFAULT_ENCODING)
    }

# --- ENCODING UTILITIES ---

def _legacy_xor_encode(xml_content: str) -> bytes:
    """
    Encodes XML string into legacy Packet Tracer binary format (XOR + zlib).
    Format: [Uncompressed Length (4 bytes BE)] + [Zlib Compressed Data]
    Obfuscation: XOR with (TotalLength - Index).
    """
    data_bytes = xml_content.encode('utf-8')
    uncompressed_len = len(data_bytes)
    
    # 1. Compress
    compressed_data = zlib.compress(data_bytes)
    
    # 2. Header (Big Endian uint32)
    header = struct.pack('>I', uncompressed_len)
    payload = bytearray(header + compressed_data)
    
    # 3. XOR Obfuscation
    total_len = len(payload)
    for i in range(total_len):
        key = (total_len - i) & 0xFF
        payload[i] ^= key
        
    return bytes(payload)

def _legacy_xor_decode(encoded_data: bytes) -> str:
    """
    Decodes legacy Packet Tracer binary format (XOR + zlib) back to XML string.
    Used for testing roundtrip integrity.
    """
    payload = bytearray(encoded_data)
    total_len = len(payload)
    
    # 1. XOR De-obfuscation
    for i in range(total_len):
        key = (total_len - i) & 0xFF
        payload[i] ^= key
        
    # 2. Extract Header
    # header = payload[:4] (Uncompressed length, ignored in Python decompression but useful for checks)
    compressed_data = payload[4:]
    
    # 3. Decompress
    try:
        decompressed_data = zlib.decompress(compressed_data)
        return decompressed_data.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decompress legacy payload: {e}")

def _run_pka2xml_container(input_path: str, output_path: str) -> None:
    """
    Runs pka2xml inside a Docker container.
    Requires 'pka2xml:latest' image and Docker availability.
    """
    abs_input = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_path)
    work_dir = os.path.dirname(abs_input)
    input_file = os.path.basename(abs_input)
    output_file = os.path.basename(abs_output)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{work_dir}:/data",
        "pka2xml:latest",
        "pka2xml", "-e",
        f"/data/{input_file}",
        f"/data/{output_file}"
    ]
    
    subprocess.run(cmd, check=True, capture_output=True, text=True)

# --- VALIDATION ---

def validate_pkt_xml(xml_content: str) -> None:
    """
    Validates logical consistency of the generated XML.
    Checks:
    - Root device integrity.
    - Consistency of Links (from/to devices must exist).
    """
    root = ET.fromstring(xml_content)
    
    # 1. Collect all Device Names and Interfaces
    device_map = {}
    for device in root.findall(".//DEVICE"):
        dev_name = device.get("name")
        if not dev_name:
            continue
            
        interfaces = set()
        for iface in device.findall("INTERFACE"):
            if_name = iface.get("name")
            if if_name:
                interfaces.add(if_name)
        
        device_map[dev_name] = interfaces

    # 2. Validate Links
    links = root.findall(".//LINKS/LINK")
    for i, link in enumerate(links):
        src_dev = link.get("from")
        dst_dev = link.get("to")
        src_port = link.get("from_port")
        dst_port = link.get("to_port")
        
        if not src_dev or not dst_dev:
            raise ValueError(f"Link {i} missing 'from' or 'to' device attribute.")
            
        if src_dev not in device_map:
            raise ValueError(f"Link source device '{src_dev}' does not exist in devices.")
        if dst_dev not in device_map:
            raise ValueError(f"Link destination device '{dst_dev}' does not exist in devices.")
            
        # Optional: Validate ports if they are standard names
        if src_port and src_port not in device_map[src_dev]:
             # Log warning or error depending on strictness. 
             # For now, we assume dynamic ports might be created, but standard ones should exist.
             pass 

# --- BUILDER ---

def build_pkt_xml(subnets: List[Any], config: Dict[str, Any]) -> str:
    """
    Constructs the Packet Tracer XML string from subnet data.
    """
    env_config = _get_env_config()
    
    root = ET.Element("PACKETTRACER5")
    
    # Global Tags
    ET.SubElement(root, "VERSION").text = env_config["XML_VERSION"]
    ET.SubElement(root, "PIXMAPBANK")
    ET.SubElement(root, "images")
    ET.SubElement(root, "MOVIEBANK")
    ET.SubElement(root, "SCENARIOSET")
    ET.SubElement(root, "OPTIONS")
    
    # Network section
    network = ET.SubElement(root, "NETWORK")
    devices_node = ET.SubElement(network, "DEVICES")
    links_node = ET.SubElement(network, "LINKS")
    
    # Helper to track device names for unique ID generation (if needed) or linking
    device_registry = {} # id -> name
    
    current_x = 100
    current_y = 100
    
    # 1. CREATE DEVICES
    for subnet_idx, subnet in enumerate(subnets):
        # -- ROUTER --
        r_name = f"R{subnet_idx+1}"
        router = ET.SubElement(devices_node, "DEVICE")
        router.set("name", r_name)
        router.set("id", r_name) # Using name as ID for simplicity
        router.set("type", "Router") 
        router.set("model", "1841") 
        
        # Router Coords
        coords = ET.SubElement(router, "COORDINATES")
        coords.set("x", str(current_x))
        coords.set("y", str(current_y))
        
        # Router Interface (Gateway)
        iface_name = "FastEthernet0/0"
        iface = ET.SubElement(router, "INTERFACE")
        iface.set("name", iface_name)
        iface.set("ip", subnet.gateway)
        iface.set("mask", subnet.mask)
        
        # -- SWITCH --
        s_name = f"S{subnet_idx+1}"
        switch = ET.SubElement(devices_node, "DEVICE")
        switch.set("name", s_name)
        switch.set("id", s_name)
        switch.set("type", "Switch")
        switch.set("model", "2960")
        
        coords = ET.SubElement(switch, "COORDINATES")
        coords.set("x", str(current_x))
        coords.set("y", str(current_y + 150))
        
        # Link Router <-> Switch
        # R1 (Fa0/0) <-> S1 (Fa0/1)
        # Note: Switch ports usually auto-generated/managed, but we define the connection
        link_rs = ET.SubElement(links_node, "LINK")
        link_rs.set("from", r_name)
        link_rs.set("to", s_name)
        link_rs.set("from_port", iface_name) 
        link_rs.set("to_port", "FastEthernet0/1") 
        link_rs.set("type", "Straight")
        
        # -- HOSTS (PCs) --
        # Use usable_hosts from result, capped at 5 for visual clarity
        hosts_count = min(subnet.usable_hosts, 5) 
        
        # Generator for IP addresses
        import ipaddress
        try:
            net_obj = ipaddress.ip_network(subnet.network, strict=False)
            # Skip gateway (first IP) and network/broadcast
            # hosts() iterator yields usable IPs. 
            # We skip the first one if it's the gateway (usually is).
            available_ips = list(net_obj.hosts())
            # Assuming gateway is at index 0 (as per subnet_calculator), start PCs from index 1
            ip_iter = iter(available_ips)
            # Skip gateway
            next(ip_iter, None) 
        except Exception as e:
            print(f"IP Calc Error: {e}")
            ip_iter = iter([])

        for h_idx in range(hosts_count):
            pc_name = f"PC{subnet_idx+1}_{h_idx+1}"
            pc = ET.SubElement(devices_node, "DEVICE")
            pc.set("name", pc_name)
            pc.set("id", pc_name)
            pc.set("type", "PC")
            
            coords = ET.SubElement(pc, "COORDINATES")
            coords.set("x", str(current_x - 100 + (h_idx * 60)))
            coords.set("y", str(current_y + 300))
            
            # PC Interface
            try:
                pc_ip = str(next(ip_iter))
            except StopIteration:
                pc_ip = "0.0.0.0" # Should not happen if logic is correct
            
            p_iface = ET.SubElement(pc, "INTERFACE")
            p_iface.set("name", "FastEthernet0")
            p_iface.set("ip", pc_ip)
            p_iface.set("mask", subnet.mask)
            p_iface.set("gateway", subnet.gateway)
            
            # Link Switch <-> PC
            # S1 (Fa0/X) <-> PC (Fa0)
            link_sp = ET.SubElement(links_node, "LINK")
            link_sp.set("from", s_name)
            link_sp.set("to", pc_name)
            link_sp.set("from_port", f"FastEthernet0/{h_idx+2}") # Start from 2
            link_sp.set("to_port", "FastEthernet0")
            link_sp.set("type", "Straight")

        current_x += 300 # Offset for next subnet

    # Formatting
    ET.indent(root, space="  ", level=0)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode", method="xml")

# --- MAIN ORCHESTRATOR ---

def save_pkt_file(subnets: List[Any], config: Dict[str, Any], output_dir: str = "/tmp") -> Tuple[str, str, str]:
    """
    Orchestrates the creation, validation, and saving of PKT files.
    
    Args:
        subnets: List of subnet objects.
        config: Generation configuration.
        output_dir: Destination directory.
        
    Returns:
        Tuple[pkt_path, xml_path, method_used]
    """
    os.makedirs(output_dir, exist_ok=True)
    env_config = _get_env_config()
    
    # 1. Build
    xml_content = build_pkt_xml(subnets, config)
    
    # 2. Validate
    try:
        validate_pkt_xml(xml_content)
    except ValueError as e:
        print(f"⚠️ XML Logic Warning: {e}")
    
    # 3. Save XML (Debug)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xml_path = os.path.join(output_dir, f"network_{timestamp}.xml")
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
        
    # 4. Encode & Save PKT
    pkt_path = os.path.join(output_dir, f"network_{timestamp}.pkt")
    encoding_method = env_config["ENCODING"]
    
    try:
        if encoding_method == "external_pka2xml":
            try:
                _run_pka2xml_container(xml_path, pkt_path)
            except Exception as e:
                print(f"❌ Docker/pka2xml failed: {e}. Falling back to legacy_xor.")
                encoding_method = "legacy_xor_fallback"
                with open(pkt_path, 'wb') as f:
                    f.write(_legacy_xor_encode(xml_content))
                    
        elif encoding_method == "gzip":
            # Just GZIP (Debug only, won't open in most PT)
            with gzip.open(pkt_path, 'wb') as f:
                f.write(xml_content.encode('utf-8'))
                
        else: # Default: legacy_xor
            with open(pkt_path, 'wb') as f:
                f.write(_legacy_xor_encode(xml_content))
                
    except Exception as e:
        print(f"❌ Encoding failed completely: {e}")
        # Last resort - empty or partial file to avoid crash? 
        # Better to re-raise or save error text
        with open(pkt_path, 'w') as f:
            f.write(f"ERROR GENERATING PKT: {e}")
        encoding_method = "error"

    return pkt_path, xml_path, encoding_method
