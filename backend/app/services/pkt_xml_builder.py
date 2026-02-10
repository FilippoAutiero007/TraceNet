"""
PKT XML Builder - Generates PT 8.2.2 compatible XML structure

This module creates the complete XML structure required by Cisco Packet Tracer 8.2.2.
The structure is based on reverse-engineering real PT 8.2.2 files.

Key differences from PT 5.x:
- <ENGINE> wrapper for device logic
- <MODULE><SLOT><PORT> hierarchy for interfaces
- <RUNNINGCONFIG><LINE> for CLI commands
- <PIXMAPBANK>, <MOVIEBANK>, <SCENARIOSET>, <OPTIONS> sections
- Complex device metadata (serial numbers, MAC addresses, etc.)

References:
- Real PT 8.2.2 file structure (decrypted)
- PT XML schema documentation
"""

import uuid
import random
from typing import List, Dict, Any
from datetime import datetime


def generate_mac_address() -> str:
    """Generate a random Cisco-style MAC address."""
    return "{:04X}.{:04X}.{:04X}".format(
        random.randint(0, 0xFFFF),
        random.randint(0, 0xFFFF),
        random.randint(0, 0xFFFF)
    )


def generate_serial_number(prefix: str = "PTT0810") -> str:
    """Generate a PT-style serial number."""
    suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=5))
    return f"{prefix}{suffix}-"


def generate_save_ref_id() -> str:
    """Generate PT save-ref-id."""
    return f"save-ref-id:{random.randint(1000000000000000000, 9999999999999999999)}"


def build_pkt_xml(subnets: List[Any], config: Dict[str, Any]) -> str:
    """
    Build complete PT 8.2.2 XML structure.
    
    Args:
        subnets: List of SubnetResult objects with network configuration
        config: Dict with routing_protocol, routers, switches, pcs counts
        
    Returns:
        Complete XML string ready for encryption
    """
    
    # Extract config
    num_routers = config.get('routers', 1)
    num_switches = config.get('switches', 2)
    num_pcs = config.get('pcs', 4)
    routing_protocol = config.get('routing_protocol', 'STATIC')
    
    # Start building XML
    xml_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<PACKETTRACER5>',
        '  <VERSION>8.2.2.0400</VERSION>',
        '',
        '  <!-- Image and Movie Banks (required but can be empty) -->',
        '  <PIXMAPBANK>',
        '    <IMAGE>',
        '      <IMAGE_PATH></IMAGE_PATH>',
        '      <IMAGE_CONTENT></IMAGE_CONTENT>',
        '    </IMAGE>',
        '  </PIXMAPBANK>',
        '  <MOVIEBANK/>',
        '',
        '  <!-- Main Network Structure -->',
        '  <NETWORK>',
        '    <DEVICES>',
    ]
    
    devices = []
    device_positions = {}
    
    # Generate Routers
    for i in range(num_routers):
        router_name = f"R{i+1}"
        x_pos = 400 + (i * 200)
        y_pos = 100
        device_positions[router_name] = (x_pos, y_pos)
        
        # Get router interfaces from subnets
        router_interfaces = []
        for subnet in subnets:
            router_interfaces.append({
                'name': f'GigabitEthernet0/{len(router_interfaces)}',
                'ip': subnet.gateway,
                'mask': subnet.mask,
                'description': subnet.name
            })
        
        devices.append(build_router_device(router_name, x_pos, y_pos, router_interfaces, routing_protocol))
    
    # Generate Switches
    for i in range(num_switches):
        switch_name = f"S{i+1}"
        x_pos = 400 + (i * 150)
        y_pos = 250
        device_positions[switch_name] = (x_pos, y_pos)
        
        # Get switch IP from corresponding subnet
        if i < len(subnets):
            subnet = subnets[i]
            switch_ip = f"{'.'.join(subnet.network.split('.')[:-1])}.{i+3}"
            gateway = subnet.gateway
        else:
            switch_ip = None
            gateway = None
        
        devices.append(build_switch_device(switch_name, x_pos, y_pos, switch_ip, gateway))
    
    # Generate PCs
    pc_per_subnet = num_pcs // len(subnets)
    pc_index = 0
    
    for subnet_idx, subnet in enumerate(subnets):
        for j in range(pc_per_subnet):
            pc_index += 1
            pc_name = f"PC{pc_index}"
            x_pos = 300 + (pc_index * 100)
            y_pos = 400 + (subnet_idx * 300)
            device_positions[pc_name] = (x_pos, y_pos)
            
            # Calculate PC IP
            pc_ip = f"{'.'.join(subnet.network.split('.')[:-1])}.{10+j+pc_index}"
            
            devices.append(build_pc_device(pc_name, x_pos, y_pos, pc_ip, subnet.mask, subnet.gateway))
    
    # Add all devices to XML
    for device_xml in devices:
        xml_lines.append(device_xml)
    
    xml_lines.extend([
        '    </DEVICES>',
        '',
        '    <!-- Network Links -->',
        '    <LINKS>',
    ])
    
    # Generate Links (simplified topology)
    link_id = 0
    
    # Connect routers to switches
    for i in range(min(num_routers, num_switches)):
        router_name = f"R{i+1}"
        switch_name = f"S{i+1}"
        xml_lines.append(build_link(link_id, router_name, f"GigabitEthernet0/{i}", switch_name, "FastEthernet0/1"))
        link_id += 1
    
    # Connect PCs to switches
    pc_index = 0
    for switch_idx in range(num_switches):
        switch_name = f"S{switch_idx+1}"
        pcs_for_this_switch = pc_per_subnet
        
        for port_idx in range(pcs_for_this_switch):
            pc_index += 1
            if pc_index > num_pcs:
                break
            pc_name = f"PC{pc_index}"
            xml_lines.append(build_link(link_id, switch_name, f"FastEthernet0/{port_idx+2}", pc_name, "FastEthernet0"))
            link_id += 1
    
    xml_lines.extend([
        '    </LINKS>',
        '  </NETWORK>',
        '',
        '  <!-- Scenario and Options (required sections) -->',
        '  <SCENARIOSET>',
        '    <SCENARIO>',
        '      <NAME>Default</NAME>',
        '    </SCENARIO>',
        '  </SCENARIOSET>',
        '',
        '  <OPTIONS>',
        '    <SHOW_DEVICE_MODEL>true</SHOW_DEVICE_MODEL>',
        '    <SHOW_DEVICE_NAME>true</SHOW_DEVICE_NAME>',
        '    <SHOW_PORT_LABELS>true</SHOW_PORT_LABELS>',
        '    <GRID_ENABLED>false</GRID_ENABLED>',
        '  </OPTIONS>',
        '',
        '</PACKETTRACER5>',
    ])
    
    return '\n'.join(xml_lines)


def build_router_device(name: str, x: int, y: int, interfaces: List[Dict], routing_protocol: str) -> str:
    """Build Router device XML (PT 8.2.2 structure)."""
    
    mac_base = generate_mac_address()
    serial = generate_serial_number()
    save_ref = generate_save_ref_id()
    
    # Build running config
    config_lines = [
        '!',
        'version 12.2',
        'no service timestamps log datetime msec',
        'no service timestamps debug datetime msec',
        'no service password-encryption',
        '!',
        f'hostname {name}',
        '!',
        'ip cef',
        'no ipv6 cef',
        '!',
    ]
    
    # Add interface configs
    for iface in interfaces:
        config_lines.extend([
            '!',
            f'interface {iface["name"]}',
            f' description {iface["description"]}',
            f' ip address {iface["ip"]} {iface["mask"]}',
            ' duplex auto',
            ' speed auto',
            ' no shutdown',
        ])
    
    config_lines.extend([
        '!',
        'ip classless',
        '!',
        'line con 0',
        '!',
        'line vty 0 4',
        ' login',
        '!',
        'end',
    ])
    
    running_config_xml = '\n'.join([f'          <LINE>{line}</LINE>' for line in config_lines])
    
    # Build interface ports XML
    ports_xml = []
    for idx, iface in enumerate(interfaces):
        port_mac = generate_mac_address()
        ports_xml.append(f'''
        <SLOT>
          <TYPE>ePtRouterModule</TYPE>
          <MODULE>
            <TYPE>ePtRouterModule</TYPE>
            <MODEL>PT-ROUTER-NM-1CGE</MODEL>
            <PORT>
              <TYPE>eCopperGigabitEthernet</TYPE>
              <POWER>true</POWER>
              <MEDIATYPE>0</MEDIATYPE>
              <BANDWIDTH>1000000</BANDWIDTH>
              <FULLDUPLEX>true</FULLDUPLEX>
              <MACADDRESS>{port_mac}</MACADDRESS>
              <BIA>{port_mac}</BIA>
              <UP_METHOD>3</UP_METHOD>
              <IP>{iface["ip"]}</IP>
              <SUBNET>{iface["mask"]}</SUBNET>
            </PORT>
          </MODULE>
        </SLOT>''')
    
    # Add empty slots
    for _ in range(10 - len(interfaces)):
        ports_xml.append('        <SLOT><TYPE>ePtRouterModule</TYPE></SLOT>')
    
    xml = f'''
      <DEVICE>
        <ENGINE>
          <TYPE customModel="" model="Router-PT">Router</TYPE>
          <NAME translate="true">{name}</NAME>
          <POWER>true</POWER>
          <DESCRIPTION></DESCRIPTION>
          <MODULE>
            <TYPE>eNonRemovableModule</TYPE>
            <MODEL/>
{''.join(ports_xml)}
          </MODULE>
          <COORD_SETTINGS>
            <X_COORD>{x}</X_COORD>
            <Y_COORD>{y}</Y_COORD>
            <Z_COORD>0</Z_COORD>
          </COORD_SETTINGS>
          <SERIALNUMBER>{serial}</SERIALNUMBER>
          <STARTTIME>730940400000</STARTTIME>
          <SAVE_REF_ID>{save_ref}</SAVE_REF_ID>
          <SYS_NAME>{name}</SYS_NAME>
          <RUNNINGCONFIG>
{running_config_xml}
          </RUNNINGCONFIG>
          <STARTUPCONFIG/>
          <BUILD_IN_ADDR>{mac_base}</BUILD_IN_ADDR>
        </ENGINE>
        <WORKSPACE>
          <LOGICAL>
            <X>{x}</X>
            <Y>{y}</Y>
          </LOGICAL>
        </WORKSPACE>
      </DEVICE>'''
    
    return xml


def build_switch_device(name: str, x: int, y: int, ip: str = None, gateway: str = None) -> str:
    """Build Switch device XML (PT 8.2.2 structure)."""
    
    mac_base = generate_mac_address()
    serial = generate_serial_number()
    save_ref = generate_save_ref_id()
    
    # Build running config
    config_lines = [
        '!',
        'version 12.1',
        'no service timestamps log datetime msec',
        'no service timestamps debug datetime msec',
        'no service password-encryption',
        '!',
        f'hostname {name}',
        '!',
        'spanning-tree mode pvst',
        '!',
    ]
    
    # Add 24 FastEthernet ports
    for i in range(1, 25):
        config_lines.extend([
            f'interface FastEthernet0/{i}',
            '!',
        ])
    
    # Add VLAN 1 config
    if ip and gateway:
        config_lines.extend([
            'interface Vlan1',
            f' ip address {ip} 255.255.255.0',
            ' no shutdown',
            '!',
            f'ip default-gateway {gateway}',
        ])
    else:
        config_lines.extend([
            'interface Vlan1',
            ' no ip address',
            ' shutdown',
        ])
    
    config_lines.extend([
        '!',
        'line con 0',
        '!',
        'line vty 0 15',
        ' login',
        '!',
        'end',
    ])
    
    running_config_xml = '\n'.join([f'          <LINE>{line}</LINE>' for line in config_lines])
    
    # Build 24 switch ports
    ports_xml = []
    for i in range(24):
        port_mac = generate_mac_address()
        ports_xml.append(f'''
        <SLOT>
          <TYPE>ePtSwitchModule</TYPE>
          <MODULE>
            <TYPE>ePtSwitchModule</TYPE>
            <MODEL>PT-SWITCH-NM-1CFE</MODEL>
            <PORT>
              <TYPE>eCopperFastEthernet</TYPE>
              <POWER>true</POWER>
              <BANDWIDTH>100000</BANDWIDTH>
              <FULLDUPLEX>true</FULLDUPLEX>
              <MACADDRESS>{port_mac}</MACADDRESS>
              <BIA>{port_mac}</BIA>
            </PORT>
          </MODULE>
        </SLOT>''')
    
    xml = f'''
      <DEVICE>
        <ENGINE>
          <TYPE customModel="" model="Switch-PT">Switch</TYPE>
          <NAME translate="true">{name}</NAME>
          <POWER>true</POWER>
          <DESCRIPTION></DESCRIPTION>
          <MODULE>
            <TYPE>eNonRemovableModule</TYPE>
            <MODEL/>
{''.join(ports_xml)}
          </MODULE>
          <COORD_SETTINGS>
            <X_COORD>{x}</X_COORD>
            <Y_COORD>{y}</Y_COORD>
            <Z_COORD>0</Z_COORD>
          </COORD_SETTINGS>
          <SERIALNUMBER>{serial}</SERIALNUMBER>
          <STARTTIME>730940400000</STARTTIME>
          <SAVE_REF_ID>{save_ref}</SAVE_REF_ID>
          <SYS_NAME>{name}</SYS_NAME>
          <RUNNINGCONFIG>
{running_config_xml}
          </RUNNINGCONFIG>
          <STARTUPCONFIG/>
          <BUILD_IN_ADDR>{mac_base}</BUILD_IN_ADDR>
        </ENGINE>
        <WORKSPACE>
          <LOGICAL>
            <X>{x}</X>
            <Y>{y}</Y>
          </LOGICAL>
        </WORKSPACE>
      </DEVICE>'''
    
    return xml


def build_pc_device(name: str, x: int, y: int, ip: str, mask: str, gateway: str) -> str:
    """Build PC device XML (PT 8.2.2 structure)."""
    
    mac = generate_mac_address()
    serial = generate_serial_number()
    save_ref = generate_save_ref_id()
    
    xml = f'''
      <DEVICE>
        <ENGINE>
          <TYPE customModel="" model="PC-PT">Pc</TYPE>
          <NAME translate="true">{name}</NAME>
          <POWER>true</POWER>
          <DESCRIPTION></DESCRIPTION>
          <MODULE>
            <TYPE>eNonRemovableModule</TYPE>
            <MODEL/>
            <SLOT>
              <TYPE>ePtHostModule</TYPE>
              <MODULE>
                <TYPE>ePtHostModule</TYPE>
                <MODEL>PT-HOST-NM-1CFE</MODEL>
                <PORT>
                  <TYPE>eCopperFastEthernet</TYPE>
                  <POWER>true</POWER>
                  <BANDWIDTH>100000</BANDWIDTH>
                  <FULLDUPLEX>true</FULLDUPLEX>
                  <MACADDRESS>{mac}</MACADDRESS>
                  <BIA>{mac}</BIA>
                  <IP>{ip}</IP>
                  <SUBNET>{mask}</SUBNET>
                  <PORT_GATEWAY>{gateway}</PORT_GATEWAY>
                </PORT>
              </MODULE>
            </SLOT>
          </MODULE>
          <COORD_SETTINGS>
            <X_COORD>{x}</X_COORD>
            <Y_COORD>{y}</Y_COORD>
            <Z_COORD>0</Z_COORD>
          </COORD_SETTINGS>
          <SERIALNUMBER>{serial}</SERIALNUMBER>
          <STARTTIME>730940400000</STARTTIME>
          <SAVE_REF_ID>{save_ref}</SAVE_REF_ID>
          <SYS_NAME>{name}</SYS_NAME>
          <GATEWAY>{gateway}</GATEWAY>
        </ENGINE>
        <WORKSPACE>
          <LOGICAL>
            <X>{x}</X>
            <Y>{y}</Y>
          </LOGICAL>
        </WORKSPACE>
      </DEVICE>'''
    
    return xml


def build_link(link_id: int, from_dev: str, from_port: str, to_dev: str, to_port: str) -> str:
    """Build Link XML (simplified PT 8.2.2 structure)."""
    
    xml = f'''      <LINK>
        <ID>{link_id}</ID>
        <TYPE>eCopper</TYPE>
        <FROM_DEVICE>{from_dev}</FROM_DEVICE>
        <FROM_PORT>{from_port}</FROM_PORT>
        <TO_DEVICE>{to_dev}</TO_DEVICE>
        <TO_PORT>{to_port}</TO_PORT>
      </LINK>'''
    
    return xml
