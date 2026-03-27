import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.pkt_generator import save_pkt_file


class MockSubnet:
    def __init__(self, name: str, mask: str, usable_range: list[str], gateway: str):
        self.name = name
        self.mask = mask
        self.usable_range = usable_range
        self.gateway = gateway


def _find_device(root: ET.Element, name: str) -> ET.Element | None:
    for dev in root.findall(".//NETWORK/DEVICES/DEVICE"):
        if (dev.findtext("ENGINE/NAME") or "").strip() == name:
            return dev
    return None


def _primary_port(device: ET.Element) -> ET.Element | None:
    # Main wired NIC for PC/Server templates
    return device.find("ENGINE/MODULE/SLOT/MODULE/PORT")


def test_pc_dhcp_mode_when_dhcp_from_router(tmp_path, monkeypatch):
    # Ensure template path is deterministic inside tests
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    # Mimic subnet_calculator.calculate_vlsm behavior:
    # gateway is outside usable_range (first usable + 1 convention)
    subnets = [
        MockSubnet(
            "LAN",
            "255.255.255.192",
            ["192.168.1.2", "192.168.1.62"],
            gateway="192.168.1.1",
        )
    ]

    config = {
        "devices": {"routers": 1, "switches": 1, "pcs": 1, "servers": 0},
        "dhcp_from_router": True,
        "routing_protocol": "static",
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = ET.fromstring(Path(result["xml_path"]).read_text(encoding="utf-8", errors="strict"))

    pc0 = _find_device(root, "PC0")
    assert pc0 is not None
    port = _primary_port(pc0)
    assert port is not None
    assert (port.findtext("UP_METHOD") or "").strip() == "1"
    assert (port.findtext("PORT_DHCP_ENABLE") or "").strip().lower() == "true"

    # Optional sanity: router got DHCP pool config
    router0 = _find_device(root, "Router0")
    assert router0 is not None
    lines = [(ln.text or "").strip() for ln in router0.findall("ENGINE/RUNNINGCONFIG/LINE")]
    assert any("ip dhcp pool" in line.lower() for line in lines)


def test_pc_dhcp_mode_when_server_runs_dhcp(tmp_path, monkeypatch):
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    subnets = [
        MockSubnet(
            "LAN",
            "255.255.255.192",
            ["192.168.1.2", "192.168.1.62"],
            gateway="192.168.1.1",
        )
    ]

    config = {
        "devices": {"routers": 1, "switches": 1, "pcs": 1, "servers": 1},
        "dhcp_from_router": False,
        "server_services": ["dhcp"],
        "routing_protocol": "static",
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = ET.fromstring(Path(result["xml_path"]).read_text(encoding="utf-8", errors="strict"))

    server0 = _find_device(root, "Server0")
    assert server0 is not None
    server_port = _primary_port(server0)
    assert server_port is not None
    server_ip = (server_port.findtext("IP") or "").strip()
    assert server_ip, "Server0 should have a static IP to act as DHCP server"

    pc0 = _find_device(root, "PC0")
    assert pc0 is not None
    pc_port = _primary_port(pc0)
    assert pc_port is not None

    assert (pc_port.findtext("UP_METHOD") or "").strip() == "1"
    assert (pc_port.findtext("PORT_DHCP_ENABLE") or "").strip().lower() == "true"

    # If the generator knows the DHCP server IP, it should be mirrored into these tags.
    assert (pc_port.findtext("DHCP_SERVER_IP") or "").strip() == server_ip
    assert (pc_port.findtext("PORT_DNS") or "").strip() == server_ip
    assert (pc0.findtext("ENGINE/DNS_CLIENT/SERVER_IP") or "").strip() == server_ip

