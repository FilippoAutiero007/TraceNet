"""
PKT XML Builder - Generates PT 8.2.2 compatible XML structure

This module builds the complete XML structure for Packet Tracer files,
following the EXACT format from real PT 8.2.2 files (simple_ref.pkt).

Key changes from original:
1. Added SAVEREFID to devices (required for links)
2. Complete PORT structure with all required fields
3. Fixed LINK structure using SAVEREFID instead of device names
4. Added memory addresses and proper XML nesting

References:
- simple_ref.pkt (decrypted) for exact XML structure
- PT 8.2.2.0400 format specification
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Any
import random
import logging
import re

logger = logging.getLogger(__name__)
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _sanitize_label(value: str, fallback: str) -> str:
    candidate = (value or "").strip()
    if _SAFE_LABEL.fullmatch(candidate):
        return candidate
    logger.warning("Unsafe label detected, using fallback", extra={"label": value, "fallback": fallback})
    return fallback


def build_pkt_xml(subnets: List[Any], config: Dict[str, Any]) -> str:
    """
    Build complete PT 8.2.2 compatible XML structure.
    
    Args:
        subnets: List of subnet objects from network generation
        config: Configuration dictionary
        
    Returns:
        Complete XML string ready for encryption
    """
    logger.info("🔨 Building PT 8.2.2 XML structure...")
    
    # Root element
    root = ET.Element("PACKETTRACER5")
    
    # Version
    version = ET.SubElement(root, "VERSION")
    version.text = "8.2.2.0400"
    
    # Empty sections (required by PT)
    _build_empty_sections(root)
    
    # Network section (devices + links)
    network = ET.SubElement(root, "NETWORK")
    devices_elem = ET.SubElement(network, "DEVICES")
    links_elem = ET.SubElement(network, "LINKS")
    
    # Track device SAVEREFIDs for links
    device_saverefs = {}
    
    # Build devices
    logger.info("  📦 Building devices...")
    for subnet in subnets:
        for device in subnet.devices:
            device_info = _extract_device_info(device, subnet)
            saverefid = _build_device_element(device_info, devices_elem)
            device_saverefs[device_info["name"]] = saverefid
    
    logger.info(f"  ✅ Built {len(device_saverefs)} devices")
    
    # Build links
    logger.info("  🔗 Building links...")
    link_count = 0
    for subnet in subnets:
        for device in subnet.devices:
            if hasattr(device, 'connections'):
                for conn in device.connections:
                    link_info = _extract_link_info(conn, subnet)
                    if link_info:
                        _build_link_element(link_info, links_elem, device_saverefs)
                        link_count += 1
    
    logger.info(f"  ✅ Built {link_count} links")
    
    # Empty trailing sections
    ET.SubElement(network, "SHAPETESTS")
    description = ET.SubElement(network, "DESCRIPTION")
    description.set("translate", "true")
    
    # Scenario set
    _build_scenario_set(root)
    
    # Options
    _build_options(root)
    
    # Convert to string
    xml_str = ET.tostring(root, encoding='unicode', method='xml')
    
    # Add XML declaration
    xml_str = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_str
    
    logger.info("✅ XML structure built successfully")
    return xml_str


def _build_empty_sections(root: ET.Element):
    """Build empty required sections (PIXMAPBANK, MOVIEBANK)."""
    pixmapbank = ET.SubElement(root, "PIXMAPBANK")
    image = ET.SubElement(pixmapbank, "IMAGE")
    ET.SubElement(image, "IMAGE_PATH")
    ET.SubElement(image, "IMAGE_CONTENT")
    
    ET.SubElement(root, "MOVIEBANK")


def _extract_device_info(device, subnet) -> Dict:
    """Extract device information for XML building."""
    return {
        "name": _sanitize_label(getattr(device, "name", ""), f"{device.device_type.capitalize()}_{random.randint(100,999)}"),
        "type": device.device_type,
        "model": _get_device_model(device.device_type),
        "interfaces": getattr(device, 'interfaces', []),
        "config": getattr(device, 'config', {}),
        "position": getattr(device, 'position', {"x": random.randint(100, 800), "y": random.randint(100, 600)})
    }


def _get_device_model(device_type: str) -> str:
    """Map device type to PT model name."""
    type_map = {
        "router": "Router-PT",
        "switch": "Switch-PT",
        "pc": "PC-PT",
        "server": "Server-PT"
    }
    return type_map.get(device_type.lower(), "Router-PT")


def _build_device_element(device_info: Dict, devices_elem: ET.Element) -> str:
    """
    Build complete DEVICE element with all required fields.
    
    Returns:
        SAVEREFID string for use in links
    """
    device = ET.SubElement(devices_elem, "DEVICE")
    engine = ET.SubElement(device, "ENGINE")
    
    # Type
    type_elem = ET.SubElement(engine, "TYPE")
    type_elem.set("customModel", "")
    type_elem.set("model", device_info["model"])
    type_elem.text = device_info["type"].capitalize()
    
    # Name
    name = ET.SubElement(engine, "NAME")
    name.set("translate", "true")
    name.text = device_info["name"]
    
    # Power
    ET.SubElement(engine, "POWER").text = "true"
    ET.SubElement(engine, "DESCRIPTION")
    
    # MODULE (ports/interfaces)
    module = ET.SubElement(engine, "MODULE")
    ET.SubElement(module, "TYPE").text = "eNonRemovableModule"
    ET.SubElement(module, "MODEL")
    
    # Build ports
    for interface in device_info["interfaces"]:
        _build_port_in_slot(module, interface, device_info["type"])
    
    # CUSTOMVARS
    ET.SubElement(engine, "CUSTOMVARS").text = "AAAAAA"
    ET.SubElement(engine, "CUSTOMINTERFACE")
    ET.SubElement(engine, "SYSCONTACT")
    ET.SubElement(engine, "SYSLOCATION")
    
    # Coordinates
    coords = ET.SubElement(engine, "COORDSETTINGS")
    pos = device_info["position"]
    ET.SubElement(coords, "XCOORD").text = str(pos["x"])
    ET.SubElement(coords, "YCOORD").text = str(pos["y"])
    ET.SubElement(coords, "ZCOORD").text = "0"
    
    # Serial number
    serial = f"PTT0810{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(100, 999)}-"
    ET.SubElement(engine, "SERIALNUMBER").text = serial
    
    # Extended attributes
    extattr = "MTBF=300000;cost=150;power source=0;rack units=2;wattage=35"
    ET.SubElement(engine, "EXTATTRIBUTES").text = extattr
    
    ET.SubElement(engine, "USBPORTCOUNT").text = "0"
    ET.SubElement(engine, "TEMPLATECREATIONTIME").text = "0"
    ET.SubElement(engine, "STARTTIME").text = "730940400000"
    ET.SubElement(engine, "STARTSIMTIME").text = str(random.randint(10000, 30000))
    
    # User apps
    userapps = ET.SubElement(engine, "USERAPPS")
    ET.SubElement(userapps, "RUNNINGAPPS")
    ET.SubElement(userapps, "DESKTOPAPPS")
    
    # SAVEREFID (CRITICAL for links!)
    saverefid = f"save-ref-id{random.randint(10**18, 10**19)}"
    ET.SubElement(engine, "SAVEREFID").text = saverefid
    
    # Additional device-specific sections
    if device_info["type"].lower() == "router":
        _build_router_sections(engine, device_info)
    elif device_info["type"].lower() == "switch":
        _build_switch_sections(engine, device_info)
    elif device_info["type"].lower() in ["pc", "server"]:
        _build_pc_sections(engine, device_info)
    
    # Workspace (GUI positioning)
    _build_workspace(engine, device_info)
    
    return saverefid


def _build_port_in_slot(module: ET.Element, interface: Dict, device_type: str):
    """Build SLOT > MODULE > PORT structure for an interface."""
    slot = ET.SubElement(module, "SLOT")
    
    # ✅ TYPE diverso per Router vs Switch
    if device_type.lower() == "switch":
        ET.SubElement(slot, "TYPE").text = "ePtSwitchModule"
    else:
        ET.SubElement(slot, "TYPE").text = "ePtRouterModule"
    
    slot_module = ET.SubElement(slot, "MODULE")
    
    # ✅ MODULE TYPE diverso per Router vs Switch
    if device_type.lower() == "switch":
        ET.SubElement(slot_module, "TYPE").text = "ePtSwitchModule"
    else:
        ET.SubElement(slot_module, "TYPE").text = "ePtRouterModule"
    
    # ✅ Module model based on interface type AND device type
    if "FastEthernet" in interface.get("name", ""):
        if device_type.lower() == "switch":
            ET.SubElement(slot_module, "MODEL").text = "PT-SWITCH-NM-1CFE"
        else:
            ET.SubElement(slot_module, "MODEL").text = "PT-ROUTER-NM-1CFE"
        port_type = "eCopperFastEthernet"
    elif "GigabitEthernet" in interface.get("name", ""):
        if device_type.lower() == "switch":
            ET.SubElement(slot_module, "MODEL").text = "PT-SWITCH-NM-1CGE"
        else:
            ET.SubElement(slot_module, "MODEL").text = "PT-ROUTER-NM-1CGE"
        port_type = "eCopperGigabitEthernet"
    elif "Serial" in interface.get("name", ""):
        # Serial ports only on routers
        ET.SubElement(slot_module, "MODEL").text = "PT-ROUTER-NM-1S"
        port_type = "eSerial"
    else:
        if device_type.lower() == "switch":
            ET.SubElement(slot_module, "MODEL").text = "PT-SWITCH-NM-1CFE"
        else:
            ET.SubElement(slot_module, "MODEL").text = "PT-ROUTER-NM-1CFE"
        port_type = "eCopperFastEthernet"
    
    # Build PORT with COMPLETE structure
    port = ET.SubElement(slot_module, "PORT")
    
    # Basic port properties
    ET.SubElement(port, "TYPE").text = port_type
    ET.SubElement(port, "POWER").text = "true" if interface.get("enabled", True) else "false"
    ET.SubElement(port, "MEDIATYPE").text = "0"
    ET.SubElement(port, "PINS").text = "false"
    
    # Bandwidth
    if "Gigabit" in port_type:
        ET.SubElement(port, "BANDWIDTH").text = "1000000"
    elif "Fast" in port_type:
        ET.SubElement(port, "BANDWIDTH").text = "100000"
    elif "Serial" in port_type:
        ET.SubElement(port, "BANDWIDTH").text = "1544"
    else:
        ET.SubElement(port, "BANDWIDTH").text = "10000"
    
    # Duplex settings
    ET.SubElement(port, "FULLDUPLEX").text = "true"
    ET.SubElement(port, "AUTONEGOTIATEBANDWIDTH").text = "true"
    ET.SubElement(port, "AUTONEGOTIATEDUPLEX").text = "true"
    
    # MAC address
    mac = interface.get("mac", _generate_mac())
    ET.SubElement(port, "MACADDRESS").text = mac
    ET.SubElement(port, "BIA").text = mac
    
    # Clock
    ET.SubElement(port, "CLOCKRATE").text = "2000000"
    ET.SubElement(port, "CLOCKRATEFLAG").text = "false"
    ET.SubElement(port, "DESCRIPTION")
    
    # Wireless channels (always 0 for wired)
    ET.SubElement(port, "CHANNEL").text = "0"
    ET.SubElement(port, "CHANNEL5GHZ").text = "0"
    ET.SubElement(port, "COVERAGERANGE").text = "0"
    
    # Saved settings
    ET.SubElement(port, "SAVEDFULLDUPLEX").text = "false"
    
    # UP method (3 = static IP configured, 5 = no IP)
    has_ip = bool(interface.get("ip"))
    ET.SubElement(port, "UPMETHOD").text = "3" if has_ip else "5"
    
    # IP configuration
    ET.SubElement(port, "IP").text = interface.get("ip", "")
    ET.SubElement(port, "SUBNET").text = interface.get("subnet", "")
    ET.SubElement(port, "PORTGATEWAY")
    ET.SubElement(port, "PORTDNS")
    ET.SubElement(port, "PORTDHCPENABLE").text = "false"
    
    # IPv6 configuration
    ET.SubElement(port, "NDSUPPRESSED").text = "false"
    ET.SubElement(port, "NDIPV6DNSADDRESSES")
    ET.SubElement(port, "TIMEOUT").text = "14400000"
    ET.SubElement(port, "PCFIREWALL").text = "false"
    ET.SubElement(port, "PCIPV6FIREWALL").text = "false"
    ET.SubElement(port, "IPV6ENABLED").text = "false"
    ET.SubElement(port, "IPV6ADDRESSAUTOCONFIG").text = "false"
    ET.SubElement(port, "IPV6PORTGATEWAY")
    ET.SubElement(port, "IPV6PORTDNS")
    ET.SubElement(port, "IPV6LINKLOCAL")
    
    # Generate IPv6 link-local from MAC
    mac_hex = mac.replace(".", "")
    ipv6_ll = f"FE80:{mac_hex[:4]}:FFFF:{mac_hex[4:8]}:{mac_hex[8:12]}"
    ET.SubElement(port, "IPV6DEFAULTLINKLOCAL").text = ipv6_ll
    
    ET.SubElement(port, "IPV6PORTDHCPENABLED").text = "false"
    ET.SubElement(port, "IPV6ADDRESSES")
    ET.SubElement(port, "IPUNNUMBERED")
    ET.SubElement(port, "DHCPSERVERIP").text = "0.0.0.0"
    ET.SubElement(port, "MANAGEMENTINTERFACE").text = "false"


def _generate_mac() -> str:
    """Generate random MAC address in Cisco format (XXXX.XXXX.XXXX)."""
    return f"{random.randint(0, 0xFFFF):04X}.{random.randint(0, 0xFFFF):04X}.{random.randint(0, 0xFFFF):04X}"


def _build_router_sections(engine: ET.Element, device_info: Dict):
    """Build router-specific sections (config, file manager, etc)."""
    ET.SubElement(engine, "SYSNAME").text = device_info["name"]
    
    # Running config
    runconfig = ET.SubElement(engine, "RUNNINGCONFIG")
    config_lines = device_info.get("config", {}).get("lines", [])
    if not config_lines:
        config_lines = [
            "!",
            "version 12.2",
            "no service timestamps log datetime msec",
            "no service timestamps debug datetime msec",
            "no service password-encryption",
            "!",
            f"hostname {device_info['name']}",
            "!",
            "!",
            "ip cef",
            "no ipv6 cef",
            "!",
            "!",
            "line con 0",
            "!",
            "line aux 0",
            "!",
            "line vty 0 4",
            " login",
            "!",
            "!",
            "end"
        ]
    
    for line in config_lines:
        line_elem = ET.SubElement(runconfig, "LINE")
        line_elem.text = line
    
    # Startup config
    ET.SubElement(engine, "STARTUPCONFIG")
    
    # Command set
    ET.SubElement(engine, "CURRENTCOMMANDSET").text = "pt12.2"
    
    # File manager (minimal)
    _build_file_manager(engine, "Router")


def _build_switch_sections(engine: ET.Element, device_info: Dict):
    """Build switch-specific sections."""
    ET.SubElement(engine, "SYSNAME").text = device_info["name"]
    
    # Running config
    runconfig = ET.SubElement(engine, "RUNNINGCONFIG")
    config_lines = [
        "!",
        "version 12.1",
        "no service timestamps log datetime msec",
        "no service timestamps debug datetime msec",
        "no service password-encryption",
        "!",
        f"hostname {device_info['name']}",
        "!",
        "spanning-tree mode pvst",
        "spanning-tree extend system-id",
        "!",
        "interface Vlan1",
        " no ip address",
        " shutdown",
        "!",
        "line con 0",
        "!",
        "line vty 0 4",
        " login",
        "line vty 5 15",
        " login",
        "!",
        "end"
    ]
    
    for line in config_lines:
        line_elem = ET.SubElement(runconfig, "LINE")
        line_elem.text = line
    
    ET.SubElement(engine, "STARTUPCONFIG")
    ET.SubElement(engine, "CURRENTCOMMANDSET").text = "pt12.1EA4"
    
    # VLANs
    vlans = ET.SubElement(engine, "VLANS")
    vlan = ET.SubElement(vlans, "VLAN")
    vlan.set("name", "default")
    vlan.set("number", "1")
    vlan.set("rspan", "0")
    
    # VTP
    vtp = ET.SubElement(engine, "VTP")
    ET.SubElement(vtp, "DOMAINNAME")
    ET.SubElement(vtp, "MODE").text = "0"
    ET.SubElement(vtp, "VERSION").text = "1"
    ET.SubElement(vtp, "PASSWORD")
    ET.SubElement(vtp, "CONFIGREVISION").text = "0"
    
    _build_file_manager(engine, "Switch")


def _build_pc_sections(engine: ET.Element, device_info: Dict):
    """Build PC/Server-specific sections."""
    ET.SubElement(engine, "SYSNAME").text = device_info["name"]
    
    # Gateway
    gateway = device_info.get("config", {}).get("gateway", "")
    ET.SubElement(engine, "GATEWAY").text = gateway
    
    # DNS client
    dns = ET.SubElement(engine, "DNSCLIENT")
    ET.SubElement(dns, "SERVERIP")
    ET.SubElement(dns, "SERVERIPV6")
    
    # DHCP client
    dhcp = ET.SubElement(engine, "DHCPCLIENT")
    ET.SubElement(dhcp, "PORTDATAMAP")


def _build_file_manager(engine: ET.Element, device_type: str):
    """Build file manager section."""
    fm = ET.SubElement(engine, "FILEMANAGER")
    
    # Root directory
    root_file = ET.SubElement(fm, "FILE")
    root_file.set("class", "CDirectory")
    ET.SubElement(root_file, "FILENUMBER").text = "0"
    ET.SubElement(root_file, "NAME")
    ET.SubElement(root_file, "DATETIME").text = "0"
    ET.SubElement(root_file, "PERMISSION").text = "6"
    ET.SubElement(root_file, "FILECONTENT")
    
    files = ET.SubElement(root_file, "FILES")
    
    # Flash filesystem
    flash = ET.SubElement(files, "FILE")
    flash.set("class", "CFileSystem")
    ET.SubElement(flash, "FILENUMBER").text = "0"
    ET.SubElement(flash, "NAME").text = "flash"
    ET.SubElement(flash, "DATETIME").text = "0"
    ET.SubElement(flash, "PERMISSION").text = "6"
    ET.SubElement(flash, "FILECONTENT")
    
    flash_files = ET.SubElement(flash, "FILES")
    
    # IOS file
    ios = ET.SubElement(flash_files, "FILE")
    ios.set("class", "CFile")
    ET.SubElement(ios, "FILENUMBER").text = "1"
    
    if device_type == "Router":
        ET.SubElement(ios, "NAME").text = "pt1000-i-mz.122-28.bin"
    else:
        ET.SubElement(ios, "NAME").text = "pt3000-i6q4l2-mz.121-22.EA4.bin"
    
    ET.SubElement(ios, "DATETIME").text = "0"
    ET.SubElement(ios, "PERMISSION").text = "6"
    
    ios_content = ET.SubElement(ios, "FILECONTENT")
    ios_content.set("class", "CIosFileContent")
    ET.SubElement(ios_content, "DEVICETYPE").text = device_type
    ET.SubElement(ios_content, "SETNAME").text = "pt12.2" if device_type == "Router" else "pt12.1EA4"
    
    ET.SubElement(flash_files, "FILECOUNTER").text = "1"
    ET.SubElement(flash_files, "CAPACITY").text = "64016384"
    
    ET.SubElement(files, "FILECOUNTER").text = "1"
    
    # Config register
    ET.SubElement(fm, "CONFIGREGISTER").text = "8450" if device_type == "Router" else "15"
    ET.SubElement(fm, "NEXTCONFIGREGISTER").text = "8450" if device_type == "Router" else "15"
    
    boot_file = f"flash:pt1000-i-mz.122-28.bin" if device_type == "Router" else "flash:pt3000-i6q4l2-mz.121-22.EA4.bin"
    ET.SubElement(fm, "CURRENTBOOTFILE").text = boot_file
    
    ET.SubElement(fm, "CONFIGBOOTFILES")
    
    # Built-in address
    builtin = _generate_mac()
    ET.SubElement(fm, "BUILDINADDR").text = builtin


def _build_workspace(engine: ET.Element, device_info: Dict):
    """Build WORKSPACE section for GUI positioning."""
    workspace = ET.SubElement(engine, "WORKSPACE")
    
    # Logical view
    logical = ET.SubElement(workspace, "LOGICAL")
    pos = device_info["position"]
    ET.SubElement(logical, "X").text = str(pos["x"])
    ET.SubElement(logical, "Y").text = str(pos["y"])
    ET.SubElement(logical, "DEVCLUSTERID").text = "1-1"
    ET.SubElement(logical, "CUSTOMIMAGELOGICAL")
    ET.SubElement(logical, "CUSTOMIMAGEPHYSICAL")
    ET.SubElement(logical, "MEMADDR").text = str(random.randint(10**12, 10**13))
    ET.SubElement(logical, "DEVADDR").text = str(random.randint(10**12, 10**13))
    
    # Physical view
    physical_id = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(100000000000, 999999999999):012x}"
    ET.SubElement(logical, "PHYSICAL").text = physical_id


def _extract_link_info(connection, subnet) -> Dict:
    """Extract link information from connection object."""
    # This depends on your connection data structure
    # Adjust according to your actual implementation
    return {
        "from_device": connection.get("from_device"),
        "from_port": connection.get("from_port"),
        "to_device": connection.get("to_device"),
        "to_port": connection.get("to_port"),
        "type": connection.get("type", "copper")
    }


def _build_link_element(link_info: Dict, links_elem: ET.Element, device_saverefs: Dict):
    """
    Build complete LINK element using SAVEREFID references.
    
    Args:
        link_info: Link connection information
        links_elem: Parent LINKS element
        device_saverefs: Dict mapping device names to SAVEREFIDs
    """
    link = ET.SubElement(links_elem, "LINK")
    
    # Type
    link_type = "eCopper" if "copper" in link_info.get("type", "").lower() else "eFiber"
    ET.SubElement(link, "TYPE").text = link_type
    
    # Cable
    cable = ET.SubElement(link, "CABLE")
    ET.SubElement(cable, "LENGTH").text = "1"
    ET.SubElement(cable, "FUNCTIONAL").text = "true"
    
    # FROM (use SAVEREFID!)
    from_device = link_info["from_device"]
    if from_device not in device_saverefs:
        logger.warning(f"⚠️  Device '{from_device}' not found in SAVEREFID map!")
        return
    
    ET.SubElement(link, "FROM").text = device_saverefs[from_device]
    port_from = ET.SubElement(link, "PORT")
    port_from.text = link_info["from_port"]
    
    # TO (use SAVEREFID!)
    to_device = link_info["to_device"]
    if to_device not in device_saverefs:
        logger.warning(f"⚠️  Device '{to_device}' not found in SAVEREFID map!")
        return
    
    ET.SubElement(link, "TO").text = device_saverefs[to_device]
    port_to = ET.SubElement(link, "PORT")
    port_to.text = link_info["to_port"]
    
    # Memory addresses (random but consistent)
    ET.SubElement(link, "FROMDEVICEMEMADDR").text = str(random.randint(10**12, 10**13))
    ET.SubElement(link, "TODEVICEMEMADDR").text = str(random.randint(10**12, 10**13))
    ET.SubElement(link, "FROMPORTMEMADDR").text = str(random.randint(10**12, 10**13))
    ET.SubElement(link, "TOPORTMEMADDR").text = str(random.randint(10**12, 10**13))
    
    # Visual settings
    ET.SubElement(link, "GEOVIEWCOLOR").text = "6ba72e"
    ET.SubElement(link, "ISMANAGEDRINRACKVIEW").text = "false"
    
    # Cable type (determines straight-through vs crossover)
    cable_type = ET.SubElement(link, "TYPE")
    cable_type.text = "eStraightThrough"


def _build_scenario_set(root: ET.Element):
    """Build SCENARIOSET section."""
    scenarioset = ET.SubElement(root, "SCENARIOSET")
    scenario = ET.SubElement(scenarioset, "SCENARIO")
    
    name = ET.SubElement(scenario, "NAME")
    name.set("translate", "true")
    name.text = "Scenario 0"
    
    desc = ET.SubElement(scenario, "DESCRIPTION")
    desc.set("translate", "true")
    desc.text = ""


def _build_options(root: ET.Element):
    """Build OPTIONS section with default PT settings."""
    options = ET.SubElement(root, "OPTIONS")
    
    ET.SubElement(options, "LANGUAGE").text = "default.ptl"
    ET.SubElement(options, "ANIMATION").text = "false"
    ET.SubElement(options, "DISABLETEXTTOSPEECH").text = "false"
    ET.SubElement(options, "LOGICALALIGN").text = "false"
    ET.SubElement(options, "PHYSICALALIGN").text = "false"
    ET.SubElement(options, "SOUND").text = "false"
    ET.SubElement(options, "TELEPHONESOUND").text = "false"
    ET.SubElement(options, "DOCK").text = "true"
    ET.SubElement(options, "LOGGING").text = "false"
    ET.SubElement(options, "PASS")
    ET.SubElement(options, "CONFIGPATH").text = "."
    ET.SubElement(options, "MODELSHOWN").text = "true"
    ET.SubElement(options, "LINKLIGHTSSHOWN").text = "true"
    ET.SubElement(options, "PORTSHOWN").text = "true"
    
    ET.SubElement(options, "BACKGROUNDS")
    
    # Hide settings
    ET.SubElement(options, "HIDEPHYSICAL").text = "false"
    ET.SubElement(options, "HIDEATTRIBUTES").text = "false"
    ET.SubElement(options, "HIDECONFIG").text = "false"
    ET.SubElement(options, "HIDECONFIGOFROUTERANDSWITCH").text = "false"
    ET.SubElement(options, "HIDECLIOFROUTERANDSWITCH").text = "false"
    ET.SubElement(options, "HIDESERVICES").text = "false"
    ET.SubElement(options, "HIDECLI").text = "false"
    ET.SubElement(options, "HIDEDESKTOP").text = "false"
    ET.SubElement(options, "HIDEGUI").text = "false"
    ET.SubElement(options, "HIDEDEVICELABEL").text = "false"
    ET.SubElement(options, "BUFFERFILTEREDEVENTSONLY").text = "false"
    ET.SubElement(options, "ACCESSIBLE").text = "false"
