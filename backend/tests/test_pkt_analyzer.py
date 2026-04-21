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


def _make_device(devices, *, name, dev_type, save_ref, ip="", subnet="", gateway="", dhcp="false", up_method="3", running_lines=None):
    device = ET.SubElement(devices, "DEVICE")
    engine = ET.SubElement(device, "ENGINE")
    ET.SubElement(engine, "TYPE").text = dev_type
    ET.SubElement(engine, "NAME").text = name
    ET.SubElement(engine, "SAVE_REF_ID").text = save_ref
    if gateway:
        ET.SubElement(engine, "GATEWAY").text = gateway

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
