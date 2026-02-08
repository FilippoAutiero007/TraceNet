"""
PKT XML Builder Service - Generates Cisco Packet Tracer 8.x compatible XML

This module builds the complete XML structure required for Cisco Packet Tracer 8.x files.
The XML structure follows the PACKETTRACER5 schema used by PT 8.x versions.

References:
- pka2xml (mircodz): https://github.com/mircodz/pka2xml
  XML structure analysis and version compatibility
- Unpacket (Punkcake21): https://github.com/Punkcake21/Unpacket
  Understanding of PT file internals

XML Structure for PT 8.x:
```xml
<PACKETTRACER5 VERSION="8.2.2.0400">
    <WORKSPACE>
        <DEVICES>
            <!-- Router, Switch, PC devices with coordinates and configs -->
        </DEVICES>
        <LINKS>
            <!-- Connections between devices -->
        </LINKS>
    </WORKSPACE>
</PACKETTRACER5>
```

Each device must have:
- Unique ID (numeric)
- Type (Router2911, Switch2960, PC, etc.)
- X, Y coordinates for visual placement
- Configuration (IOS commands for routers/switches, IP config for PCs)
"""

from typing import List, Dict, Any, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom
from app.models.schemas import SubnetResult, NetworkConfig, RoutingProtocol
import logging

logger = logging.getLogger(__name__)

# PT 8.x device type identifiers
DEVICE_TYPES = {
    "router": "Router2911",
    "switch": "Switch2960",
    "pc": "PC",
    "server": "Server"
}

# Device visual spacing (in PT canvas units)
DEVICE_SPACING = {
    "router_x": 200,
    "switch_x": 150,
    "pc_x": 100,
    "pc_y": 150,
    "subnet_y_spacing": 300
}


def calculate_device_position(device_type: str, index: int, subnet_index: int = 0) -> Tuple[int, int]:
    """
    Calculate device position on the PT canvas.
    
    Layout strategy:
    - Routers: Centered top row
    - Switches: Below routers, one per subnet
    - PCs: Below switches, distributed per subnet
    
    Args:
        device_type: Type of device (router, switch, pc)
        index: Device index (0-based)
        subnet_index: Subnet index for proper vertical spacing
        
    Returns:
        Tuple of (x, y) coordinates
    """
    if device_type == "router":
        x = 400 + (index * DEVICE_SPACING["router_x"])
        y = 100
    elif device_type == "switch":
        x = 400 + (subnet_index * DEVICE_SPACING["switch_x"])
        y = 250
    else:  # pc
        row = index // 4  # 4 PCs per row
        col = index % 4
        x = 300 + (col * DEVICE_SPACING["pc_x"]) + (subnet_index * 400)
        y = 400 + (row * DEVICE_SPACING["pc_y"]) + (subnet_index * DEVICE_SPACING["subnet_y_spacing"])
    
    return x, y


def generate_router_config(router_name: str, subnets: List[SubnetResult], routing_protocol: RoutingProtocol) -> str:
    """
    Generate Cisco IOS configuration for a router.
    
    Configuration includes:
    - Hostname
    - Interface configurations (one per subnet)
    - Routing protocol setup
    
    Args:
        router_name: Router hostname (e.g., "R1")
        subnets: List of subnets to configure
        routing_protocol: Routing protocol to use
        
    Returns:
        Cisco IOS configuration as string
        
    Reference: app/services/pkt_generator.py - generate_cisco_config()
    """
    config_lines = []
    
    # Basic config
    config_lines.append(f"hostname {router_name}")
    config_lines.append("!")
    config_lines.append("service password-encryption")
    config_lines.append("!")
    
    # Configure interfaces
    for i, subnet in enumerate(subnets):
        iface = f"GigabitEthernet0/{i}"
        config_lines.append(f"interface {iface}")
        config_lines.append(f" description {subnet.name}")
        config_lines.append(f" ip address {subnet.gateway} {subnet.mask}")
        config_lines.append(" no shutdown")
        config_lines.append("!")
    
    # Routing protocol
    if routing_protocol == RoutingProtocol.RIP:
        config_lines.append("router rip")
        config_lines.append(" version 2")
        for subnet in subnets:
            network_addr = subnet.network.split("/")[0]
            config_lines.append(f" network {network_addr}")
        config_lines.append(" no auto-summary")
        config_lines.append("!")
    elif routing_protocol == RoutingProtocol.OSPF:
        config_lines.append("router ospf 1")
        for subnet in subnets:
            network_addr = subnet.network.split("/")[0]
            # Calculate wildcard mask
            octets = subnet.mask.split(".")
            wildcard = ".".join([str(255 - int(o)) for o in octets])
            config_lines.append(f" network {network_addr} {wildcard} area 0")
        config_lines.append("!")
    elif routing_protocol == RoutingProtocol.EIGRP:
        config_lines.append("router eigrp 100")
        for subnet in subnets:
            network_addr = subnet.network.split("/")[0]
            config_lines.append(f" network {network_addr}")
        config_lines.append(" no auto-summary")
        config_lines.append("!")
    
    return "\n".join(config_lines)


def generate_switch_config(switch_name: str, subnet: SubnetResult) -> str:
    """
    Generate Cisco IOS configuration for a switch.
    
    Args:
        switch_name: Switch hostname (e.g., "S1")
        subnet: Subnet this switch belongs to
        
    Returns:
        Cisco IOS configuration as string
    """
    # Calculate management IP (use first usable IP + switch offset)
    usable_start = subnet.usable_range[0]
    parts = usable_start.split(".")
    mgmt_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.{int(parts[3]) + 1}"
    
    config_lines = [
        f"hostname {switch_name}",
        "!",
        "interface vlan 1",
        f" ip address {mgmt_ip} {subnet.mask}",
        " no shutdown",
        "!",
        f"ip default-gateway {subnet.gateway}",
        "!"
    ]
    
    return "\n".join(config_lines)


def build_pkt_xml(subnets: List[SubnetResult], config: Dict[str, Any]) -> str:
    """
    Builds the complete XML structure for a Cisco Packet Tracer 8.x file.
    
    This function creates the entire network topology including:
    - Routers with proper interface configurations
    - Switches connected to routers
    - PCs connected to switches with IP configurations
    - Physical links between all devices
    
    Args:
        subnets: List of calculated subnets
        config: Network configuration dict with keys:
            - routing_protocol: RoutingProtocol enum value
            - routers: int (number of routers)
            - switches: int (number of switches)
            - pcs: int (number of PCs)
            
    Returns:
        Complete XML string compatible with PT 8.x
        
    References:
    - pka2xml structure analysis
    - TraceNet existing pkt_generator.py logic
    """
    # Create root element with PT 8.x version
    root = ET.Element("PACKETTRACER5")
    root.set("VERSION", "8.2.2.0400")  # PT 8.x version
    
    # Create workspace
    workspace = ET.SubElement(root, "WORKSPACE")
    devices = ET.SubElement(workspace, "DEVICES")
    links = ET.SubElement(workspace, "LINKS")
    
    # Track device IDs and connections
    device_id = 0
    device_map = {}  # name -> (id, type)
    link_id = 0
    
    # Get configuration
    num_routers = config.get("routers", 1)
    num_switches = config.get("switches", len(subnets))
    num_pcs = config.get("pcs", 0)
    routing_protocol = config.get("routing_protocol", RoutingProtocol.STATIC)
    
    # === CREATE ROUTERS ===
    for router_idx in range(num_routers):
        router_name = f"R{router_idx + 1}"
        x, y = calculate_device_position("router", router_idx)
        
        device = ET.SubElement(devices, "DEVICE")
        device.set("id", str(device_id))
        device.set("name", router_name)
        device.set("type", DEVICE_TYPES["router"])
        device.set("x", str(x))
        device.set("y", str(y))
        
        # Router configuration
        router_config = generate_router_config(router_name, subnets, routing_protocol)
        config_elem = ET.SubElement(device, "CONFIG")
        config_elem.text = router_config
        
        # Add interfaces
        for iface_idx, subnet in enumerate(subnets):
            interface = ET.SubElement(device, "INTERFACE")
            interface.set("name", f"GigabitEthernet0/{iface_idx}")
            interface.set("ip", subnet.gateway)
            interface.set("mask", subnet.mask)
        
        device_map[router_name] = (device_id, "router")
        device_id += 1
    
    # === CREATE SWITCHES (one per subnet) ===
    for switch_idx, subnet in enumerate(subnets):
        switch_name = f"S{switch_idx + 1}"
        x, y = calculate_device_position("switch", switch_idx, switch_idx)
        
        device = ET.SubElement(devices, "DEVICE")
        device.set("id", str(device_id))
        device.set("name", switch_name)
        device.set("type", DEVICE_TYPES["switch"])
        device.set("x", str(x))
        device.set("y", str(y))
        
        # Switch configuration
        switch_config = generate_switch_config(switch_name, subnet)
        config_elem = ET.SubElement(device, "CONFIG")
        config_elem.text = switch_config
        
        # Add ports (24-port switch)
        for port in range(24):
            interface = ET.SubElement(device, "INTERFACE")
            interface.set("name", f"FastEthernet0/{port + 1}")
        
        device_map[switch_name] = (device_id, "switch")
        device_id += 1
        
        # CREATE LINK: Router to Switch
        router_name = "R1"  # Connect to first router
        link = ET.SubElement(links, "LINK")
        link.set("id", str(link_id))
        link.set("from", router_name)
        link.set("from_port", f"GigabitEthernet0/{switch_idx}")
        link.set("to", switch_name)
        link.set("to_port", "FastEthernet0/1")
        link.set("type", "copper")
        link_id += 1
    
    # === CREATE PCs ===
    pcs_per_subnet = max(1, num_pcs // len(subnets)) if num_pcs > 0 else 0
    pc_num = 1
    
    for subnet_idx, subnet in enumerate(subnets):
        switch_name = f"S{subnet_idx + 1}"
        
        # Calculate IPs for PCs (starting after gateway and switch management)
        usable_start = subnet.usable_range[0]
        parts = usable_start.split(".")
        base_ip = f"{parts[0]}.{parts[1]}.{parts[2]}"
        
        for pc_idx in range(pcs_per_subnet):
            if pc_num > num_pcs:
                break
            
            pc_name = f"PC{pc_num}"
            x, y = calculate_device_position("pc", pc_idx, subnet_idx)
            
            device = ET.SubElement(devices, "DEVICE")
            device.set("id", str(device_id))
            device.set("name", pc_name)
            device.set("type", DEVICE_TYPES["pc"])
            device.set("x", str(x))
            device.set("y", str(y))
            
            # PC IP configuration
            pc_ip = f"{base_ip}.{int(parts[3]) + pc_idx + 10}"
            config_elem = ET.SubElement(device, "CONFIG")
            config_elem.set("ip", pc_ip)
            config_elem.set("mask", subnet.mask)
            config_elem.set("gateway", subnet.gateway)
            
            # PC interface
            interface = ET.SubElement(device, "INTERFACE")
            interface.set("name", "FastEthernet0")
            
            device_map[pc_name] = (device_id, "pc")
            device_id += 1
            
            # CREATE LINK: Switch to PC
            link = ET.SubElement(links, "LINK")
            link.set("id", str(link_id))
            link.set("from", switch_name)
            link.set("from_port", f"FastEthernet0/{pc_idx + 2}")  # Port 1 used for router
            link.set("to", pc_name)
            link.set("to_port", "FastEthernet0")
            link.set("type", "copper")
            link_id += 1
            
            pc_num += 1
    
    # Convert to pretty-printed XML string
    xml_str = ET.tostring(root, encoding='utf-8', method='xml')
    
    # Pretty print
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding="utf-8")
    
    # Decode bytes to string and remove extra blank lines
    xml_string = pretty_xml.decode('utf-8')
    lines = [line for line in xml_string.split('\n') if line.strip()]
    
    logger.info(f"✅ Built XML with {device_id} devices and {link_id} links")
    
    return '\n'.join(lines)
