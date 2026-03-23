import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.pkt_generator import save_pkt_file
from app.services.pkt_generator.config_generator import generate_router_config


class MockSubnet:
    def __init__(
        self,
        name: str,
        mask: str,
        usable_range: list[str],
        gateway: str,
        dns_server: str | None = None,
    ):
        self.name = name
        self.mask = mask
        self.usable_range = usable_range
        self.gateway = gateway
        self.dns_server = dns_server


def _find_device(root: ET.Element, name: str) -> ET.Element | None:
    for dev in root.findall(".//NETWORK/DEVICES/DEVICE"):
        if (dev.findtext("ENGINE/NAME") or "").strip() == name:
            return dev
    return None


def test_router_dhcp_pool_core_params_are_generated():
    dev_cfg = {
        "name": "Router0",
        "dhcp_from_router": True,
        "interfaces": [
            {"name": "FastEthernet0/0", "ip": "192.168.10.1", "mask": "255.255.255.0", "role": "lan"},
            {"name": "FastEthernet0/1", "ip": "11.0.0.1", "mask": "255.255.255.252", "role": "wan"},
        ],
        "dhcp_dns": "1.1.1.1",
    }

    lines = generate_router_config(dev_cfg, all_devices=[dev_cfg], links_config=[])
    joined = "\n".join(lines)

    assert "ip dhcp pool 192.168.10.0" in joined
    assert " network 192.168.10.0 255.255.255.0" in joined
    assert " default-router 192.168.10.1" in joined
    assert " dns-server 1.1.1.1" in joined
    assert "ip dhcp excluded-address 192.168.10.1 192.168.10.5" in joined


def test_router_dhcp_dns_invalid_network_value_omits_dns_line(caplog):
    dev_cfg = {
        "name": "Router0",
        "dhcp_from_router": True,
        "interfaces": [
            {
                "name": "FastEthernet0/0",
                "ip": "10.0.0.1",
                "mask": "255.255.255.0",
                "role": "lan",
                "dns_server": "1.1.1.1",
            },
        ],
        "dhcp_dns": "not-an-ip",
    }

    lines = generate_router_config(dev_cfg, all_devices=[dev_cfg], links_config=[])
    # Invalid network-level value falls back to subnet/interface DNS.
    assert " dns-server 1.1.1.1" in "\n".join(lines)
    assert "Invalid DHCP DNS 'not-an-ip'" in caplog.text


def test_router_dhcp_dns_is_omitted_when_missing_or_invalid():
    base = {
        "name": "Router0",
        "dhcp_from_router": True,
        "interfaces": [
            {"name": "FastEthernet0/0", "ip": "172.16.0.1", "mask": "255.255.0.0", "role": "lan"},
        ],
    }
    lines_missing = generate_router_config(dict(base), all_devices=[base], links_config=[])
    assert " dns-server " not in "\n".join(lines_missing)

    invalid = dict(base)
    invalid["dhcp_dns"] = "not-an-ip"
    lines_invalid = generate_router_config(invalid, all_devices=[invalid], links_config=[])
    assert " dns-server " not in "\n".join(lines_invalid)


def test_router_dhcp_dns_uses_subnet_dns_when_network_value_not_set():
    dev_cfg = {
        "name": "Router0",
        "dhcp_from_router": True,
        "interfaces": [
            {
                "name": "FastEthernet0/0",
                "ip": "10.10.10.1",
                "mask": "255.255.255.0",
                "role": "lan",
                "dns_server": "9.9.9.9",
            },
        ],
    }
    lines = generate_router_config(dev_cfg, all_devices=[dev_cfg], links_config=[])
    assert " dns-server 9.9.9.9" in "\n".join(lines)


def test_entrypoint_router_dhcp_prefers_request_dhcp_dns_over_subnet_dns(tmp_path, monkeypatch):
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    subnets = [
        MockSubnet(
            "LAN",
            "255.255.255.192",
            ["192.168.1.2", "192.168.1.62"],
            gateway="192.168.1.1",
            dns_server="9.9.9.9",
        )
    ]

    config = {
        "devices": {"routers": 1, "switches": 1, "pcs": 1, "servers": 1},
        "dhcp_from_router": True,
        "dhcp_dns": "192.168.2.3",
        "server_services": ["dns"],
        "routing_protocol": "static",
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = ET.fromstring(Path(result["xml_path"]).read_text(encoding="utf-8", errors="strict"))
    server0 = _find_device(root, "Server0")
    assert server0 is not None

    router0 = _find_device(root, "Router0")
    assert router0 is not None
    lines = [(ln.text or "").strip() for ln in router0.findall("ENGINE/RUNNINGCONFIG/LINE")]

    assert any(line.lower().startswith("ip dhcp pool ") for line in lines)
    assert "dns-server 192.168.2.3" in lines
