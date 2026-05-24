import xml.etree.ElementTree as ET

from app.services.pkt_analyzer import analyze_pkt_xml


def _make_port(parent, ip="", subnet="", dhcp="false", up_method="3", gateway=""):
    port = ET.SubElement(parent, "PORT")
    ET.SubElement(port, "TYPE").text = "eCopperFastEthernet"
    ET.SubElement(port, "IP").text = ip
    ET.SubElement(port, "SUBNET").text = subnet
    ET.SubElement(port, "PORT_GATEWAY").text = gateway
    ET.SubElement(port, "PORT_DHCP_ENABLE").text = dhcp
    ET.SubElement(port, "UP_METHOD").text = up_method
    return port


def _make_device(devices, *, name, dev_type, save_ref, ip="", subnet="", gateway="", dhcp="false", up_method="3", running_lines=None, has_server_dhcp=False):
    device = ET.SubElement(devices, "DEVICE")
    engine = ET.SubElement(device, "ENGINE")
    ET.SubElement(engine, "TYPE").text = dev_type
    ET.SubElement(engine, "NAME").text = name
    ET.SubElement(engine, "SAVE_REF_ID").text = save_ref
    if gateway:
        ET.SubElement(engine, "GATEWAY").text = gateway

    if has_server_dhcp:
        dhcp_servers = ET.SubElement(engine, "DHCP_SERVERS")
        assoc_ports = ET.SubElement(dhcp_servers, "ASSOCIATED_PORTS")
        assoc_port = ET.SubElement(assoc_ports, "ASSOCIATED_PORT")
        dhcp_srv = ET.SubElement(assoc_port, "DHCP_SERVER")
        ET.SubElement(dhcp_srv, "ENABLED").text = "1"

    module = ET.SubElement(engine, "MODULE")
    slot = ET.SubElement(module, "SLOT")
    slot_module = ET.SubElement(slot, "MODULE")
    _make_port(slot_module, ip=ip, subnet=subnet, dhcp=dhcp, up_method=up_method, gateway=gateway)

    if running_lines is not None:
        running = ET.SubElement(engine, "RUNNINGCONFIG")
        for line in running_lines:
            ET.SubElement(running, "LINE").text = line

    workspace = ET.SubElement(device, "WORKSPACE")
    logical = ET.SubElement(workspace, "LOGICAL")
    ET.SubElement(logical, "DEV_ADDR").text = f"dev-{name}"
    ET.SubElement(logical, "MEM_ADDR").text = f"mem-{name}"
    return device


def _make_link(links, from_ref, from_port, to_ref, to_port):
    link = ET.SubElement(links, "LINK")
    cable = ET.SubElement(link, "CABLE")
    ET.SubElement(cable, "FROM").text = from_ref
    ET.SubElement(cable, "PORT").text = from_port
    ET.SubElement(cable, "TO").text = to_ref
    ET.SubElement(cable, "PORT").text = to_port


def _build_sample_root():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(
        devices,
        name="Router0",
        dev_type="Router",
        save_ref="save-ref-id:r0",
        ip="192.168.1.1",
        subnet="255.255.255.0",
        running_lines=[
            "interface FastEthernet0/0",
            " ip address 192.168.1.1 255.255.255.0",
            "!",
        ],
    )
    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")
    _make_device(
        devices,
        name="PC0",
        dev_type="Pc",
        save_ref="save-ref-id:pc0",
        ip="192.168.1.10",
        subnet="255.255.255.0",
    )
    _make_device(
        devices,
        name="PC1",
        dev_type="Pc",
        save_ref="save-ref-id:pc1",
        ip="192.168.1.10",
        subnet="255.255.255.0",
        gateway="10.0.0.1",
    )

    _make_link(links, "save-ref-id:r0", "FastEthernet0/0", "save-ref-id:s0", "FastEthernet0/1")
    _make_link(links, "save-ref-id:pc0", "FastEthernet0", "save-ref-id:s0", "FastEthernet1/1")
    _make_link(links, "save-ref-id:pc1", "FastEthernet0", "save-ref-id:s0", "FastEthernet2/1")

    return root


def test_pkt_analyzer_reports_gateway_and_duplicate_ip_errors():
    result = analyze_pkt_xml(_build_sample_root(), filename="broken.pkt")

    assert result.success is True
    codes = {issue.code for issue in result.issues}
    assert "MISSING_DEFAULT_GATEWAY" in codes
    assert "DUPLICATE_IP_ADDRESS" in codes
    assert "GATEWAY_OUTSIDE_SUBNET" in codes


def test_pkt_analyzer_reports_possible_vlsm_segment_mismatch():
    root = _build_sample_root()
    devices = root.find("./NETWORK/DEVICES")
    assert devices is not None
    _make_device(
        devices,
        name="PC2",
        dev_type="Pc",
        save_ref="save-ref-id:pc2",
        ip="192.168.2.10",
        subnet="255.255.255.0",
        gateway="192.168.2.1",
    )
    links = root.find("./NETWORK/LINKS")
    assert links is not None
    _make_link(links, "save-ref-id:pc2", "FastEthernet0", "save-ref-id:s0", "FastEthernet3/1")

    result = analyze_pkt_xml(root, filename="vlsm.pkt")

    codes = {issue.code for issue in result.issues}
    assert "LAN_SUBNET_MISMATCH" in codes


def test_dhcp_server_disconnected():
    root = _build_root_with_disconnected_server()
    result = analyze_pkt_xml(root, filename="dhcp_disconnected.pkt")
    codes = {issue.code for issue in result.issues}
    assert "DHCP_SERVER_DISCONNECTED" in codes


def test_device_disconnected():
    root = _build_root_with_disconnected_pc()
    result = analyze_pkt_xml(root, filename="pc_disconnected.pkt")
    codes = {issue.code for issue in result.issues}
    assert "DEVICE_DISCONNECTED" in codes


def test_router_disconnected():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    ET.SubElement(network, "LINKS")
    _make_device(devices, name="Router0", dev_type="Router", save_ref="save-ref-id:r0", ip="192.168.1.1", subnet="255.255.255.0")
    result = analyze_pkt_xml(root, filename="router_disconnected.pkt")
    codes = {issue.code for issue in result.issues}
    assert "ROUTER_DISCONNECTED" in codes


def test_router_interface_no_ip():
    root = _build_root_with_router_no_ip()
    result = analyze_pkt_xml(root, filename="router_no_ip.pkt")
    codes = {issue.code for issue in result.issues}
    assert "ROUTER_INTERFACE_NO_IP" in codes


def test_router_all_interfaces_shutdown():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(
        devices, name="Router0", dev_type="Router", save_ref="save-ref-id:r0",
        ip="192.168.1.1", subnet="255.255.255.0",
        running_lines=[
            "interface FastEthernet0/0",
            " ip address 192.168.1.1 255.255.255.0",
            " shutdown",
            "!",
        ],
    )
    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")
    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="192.168.1.10", subnet="255.255.255.0")

    _make_link(links, "save-ref-id:r0", "FastEthernet0/0", "save-ref-id:s0", "FastEthernet0/1")
    _make_link(links, "save-ref-id:pc0", "FastEthernet0", "save-ref-id:s0", "FastEthernet1/1")

    result = analyze_pkt_xml(root, filename="shutdown.pkt")
    codes = {issue.code for issue in result.issues}
    assert "ALL_INTERFACES_SHUTDOWN" in codes


def test_router_no_config():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(devices, name="Router0", dev_type="Router", save_ref="save-ref-id:r0", running_lines=[])
    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")

    _make_link(links, "save-ref-id:r0", "FastEthernet0/0", "save-ref-id:s0", "FastEthernet0/1")

    result = analyze_pkt_xml(root, filename="no_config.pkt")
    codes = {issue.code for issue in result.issues}
    assert "ROUTER_NO_CONFIG" in codes


def test_switch_no_uplink():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")
    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="192.168.1.10", subnet="255.255.255.0")

    _make_link(links, "save-ref-id:pc0", "FastEthernet0", "save-ref-id:s0", "FastEthernet0/1")

    result = analyze_pkt_xml(root, filename="no_uplink.pkt")
    codes = {issue.code for issue in result.issues}
    assert "SWITCH_NO_UPLINK" in codes


def test_switch_no_uplink_not_reported_if_router_exists():
    root = _build_sample_root()
    result = analyze_pkt_xml(root, filename="with_uplink.pkt")
    codes = {issue.code for issue in result.issues}
    assert "SWITCH_NO_UPLINK" not in codes


def test_vlan_no_router():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(
        devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0",
        running_lines=["interface FastEthernet0/1", " switchport access vlan 10", "!"],
    )
    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="192.168.1.10", subnet="255.255.255.0")

    _make_link(links, "save-ref-id:pc0", "FastEthernet0", "save-ref-id:s0", "FastEthernet0/1")

    result = analyze_pkt_xml(root, filename="vlan_no_router.pkt")
    codes = {issue.code for issue in result.issues}
    assert "VLAN_NO_ROUTER" in codes


def test_subiface_no_encapsulation():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(
        devices, name="Router0", dev_type="Router", save_ref="save-ref-id:r0",
        ip="192.168.1.1", subnet="255.255.255.0",
        running_lines=[
            "interface FastEthernet0/0.10",
            " ip address 192.168.10.1 255.255.255.0",
            "!",
        ],
    )
    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")
    _make_link(links, "save-ref-id:r0", "FastEthernet0/0", "save-ref-id:s0", "FastEthernet0/1")

    result = analyze_pkt_xml(root, filename="no_encap.pkt")
    codes = {issue.code for issue in result.issues}
    assert "SUBFACE_NO_ENCAPSULATION" in codes


def test_acls_referenced_not_defined():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(
        devices, name="Router0", dev_type="Router", save_ref="save-ref-id:r0",
        ip="192.168.1.1", subnet="255.255.255.0",
        running_lines=[
            "interface FastEthernet0/0",
            " ip address 192.168.1.1 255.255.255.0",
            " ip access-group 100 in",
            "!",
        ],
    )
    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")
    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="192.168.1.10", subnet="255.255.255.0")

    _make_link(links, "save-ref-id:r0", "FastEthernet0/0", "save-ref-id:s0", "FastEthernet0/1")
    _make_link(links, "save-ref-id:pc0", "FastEthernet0", "save-ref-id:s0", "FastEthernet1/1")

    result = analyze_pkt_xml(root, filename="acl_missing.pkt")
    codes = {issue.code for issue in result.issues}
    assert "ACL_REFERENCE_NOT_FOUND" in codes


def test_multiple_dhcp_servers():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(
        devices, name="Server0", dev_type="Server", save_ref="save-ref-id:sv0",
        ip="192.168.1.10", subnet="255.255.255.0", has_server_dhcp=True,
    )
    _make_device(
        devices, name="Server1", dev_type="Server", save_ref="save-ref-id:sv1",
        ip="192.168.1.20", subnet="255.255.255.0", has_server_dhcp=True,
    )
    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")

    _make_link(links, "save-ref-id:sv0", "FastEthernet0", "save-ref-id:s0", "FastEthernet0/1")
    _make_link(links, "save-ref-id:sv1", "FastEthernet0", "save-ref-id:s0", "FastEthernet1/1")

    result = analyze_pkt_xml(root, filename="multi_dhcp.pkt")
    codes = {issue.code for issue in result.issues}
    assert "MULTIPLE_DHCP_SERVERS" in codes


def test_device_unnamed():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    ET.SubElement(network, "LINKS")

    device = ET.SubElement(devices, "DEVICE")
    engine = ET.SubElement(device, "ENGINE")
    ET.SubElement(engine, "TYPE").text = "Pc"
    ET.SubElement(engine, "SAVE_REF_ID").text = "save-ref-id:unknown"

    module = ET.SubElement(engine, "MODULE")
    slot = ET.SubElement(module, "SLOT")
    slot_module = ET.SubElement(slot, "MODULE")
    _make_port(slot_module, ip="192.168.1.10", subnet="255.255.255.0")

    result = analyze_pkt_xml(root, filename="unnamed.pkt")
    codes = {issue.code for issue in result.issues}
    assert "DEVICE_UNNAMED" in codes


def test_invalid_ip_or_mask():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    ET.SubElement(network, "LINKS")

    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="999.999.999.999", subnet="255.255.255.0")

    result = analyze_pkt_xml(root, filename="bad_ip.pkt")
    codes = {issue.code for issue in result.issues}
    assert "INVALID_IP_OR_MASK" in codes


def test_device_no_ports():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    ET.SubElement(network, "LINKS")

    device = ET.SubElement(devices, "DEVICE")
    engine = ET.SubElement(device, "ENGINE")
    ET.SubElement(engine, "TYPE").text = "Switch"
    ET.SubElement(engine, "NAME").text = "Switch0"
    ET.SubElement(engine, "SAVE_REF_ID").text = "save-ref-id:s0"

    result = analyze_pkt_xml(root, filename="no_ports.pkt")
    codes = {issue.code for issue in result.issues}
    assert "DEVICE_NO_PORTS" in codes


def test_reserved_host_address():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    ET.SubElement(network, "LINKS")

    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="192.168.1.0", subnet="255.255.255.0")

    result = analyze_pkt_xml(root, filename="reserved.pkt")
    codes = {issue.code for issue in result.issues}
    assert "RESERVED_HOST_ADDRESS" in codes


def _build_root_with_disconnected_server():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    ET.SubElement(network, "LINKS")

    _make_device(
        devices, name="Server0", dev_type="Server", save_ref="save-ref-id:sv0",
        ip="192.168.1.10", subnet="255.255.255.0", has_server_dhcp=True,
    )
    return root


def _build_root_with_disconnected_pc():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    ET.SubElement(network, "LINKS")

    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="192.168.1.10", subnet="255.255.255.0")
    return root


def _build_root_with_router_no_ip():
    root = ET.Element("PACKETTRACER5")
    ET.SubElement(root, "VERSION").text = "8.2.2.0400"
    network = ET.SubElement(root, "NETWORK")
    devices = ET.SubElement(network, "DEVICES")
    links = ET.SubElement(network, "LINKS")

    _make_device(
        devices, name="Router0", dev_type="Router", save_ref="save-ref-id:r0",
        ip="", subnet="",
        running_lines=[
            "interface FastEthernet0/0",
            "!",
        ],
    )
    _make_device(devices, name="Switch0", dev_type="Switch", save_ref="save-ref-id:s0")
    _make_device(devices, name="PC0", dev_type="Pc", save_ref="save-ref-id:pc0", ip="192.168.1.10", subnet="255.255.255.0")

    _make_link(links, "save-ref-id:r0", "FastEthernet0/0", "save-ref-id:s0", "FastEthernet0/1")
    _make_link(links, "save-ref-id:pc0", "FastEthernet0", "save-ref-id:s0", "FastEthernet1/1")

    return root
