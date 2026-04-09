import xml.etree.ElementTree as ET
from pathlib import Path

from app.models.manual_schemas import ManualNetworkRequest
from app.models.schemas import DeviceConfig, RoutingProtocol, SubnetRequest
from app.services.pkt_generator import save_pkt_file
from app.services.pkt_generator.config_generator import generate_router_config, generate_switch_config


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


def _running_lines(device: ET.Element) -> list[str]:
    return [(node.text or "").strip() for node in device.findall("ENGINE/RUNNINGCONFIG/LINE")]


def test_generate_switch_config_includes_vlans_access_ports_and_trunk_details():
    lines = generate_switch_config(
        {
            "name": "Switch0",
            "vlans": [
                {"id": 10, "name": "ADMIN"},
                {"id": 20, "name": "GUEST", "native": True},
            ],
            "access_ports": {
                "FastEthernet0/2": 10,
                "FastEthernet0/3": 20,
            },
            "trunk_ports": ["FastEthernet0/1"],
            "trunk_allowed_vlans": [10, 20],
        }
    )
    joined = "\n".join(lines)

    assert "vlan 10" in joined
    assert " name ADMIN" in joined
    assert "vlan 20" in joined
    assert "interface FastEthernet0/2" in joined
    assert " switchport access vlan 10" in joined
    assert "interface FastEthernet0/1" in joined
    assert " switchport mode trunk" in joined
    assert " switchport trunk native vlan 20" in joined
    assert " switchport trunk allowed vlan 10,20" in joined


def test_generate_router_config_supports_router_on_a_stick_subinterfaces():
    dev_cfg = {
        "name": "Router0",
        "interfaces": [
            {
                "name": "FastEthernet0/0.10",
                "ip": "192.168.10.1",
                "mask": "255.255.255.0",
                "role": "lan",
                "encapsulation": "dot1Q 10",
            },
            {
                "name": "FastEthernet0/0.20",
                "ip": "192.168.20.1",
                "mask": "255.255.255.0",
                "role": "lan",
                "encapsulation": "dot1Q 20",
            },
        ],
    }

    lines = generate_router_config(dev_cfg, all_devices=[dev_cfg], links_config=[])
    joined = "\n".join(lines)

    assert "interface FastEthernet0/0" in joined
    assert "interface FastEthernet0/0.10" in joined
    assert " encapsulation dot1Q 10" in joined
    assert " ip address 192.168.10.1 255.255.255.0" in joined
    assert "interface FastEthernet0/0.20" in joined
    assert " encapsulation dot1Q 20" in joined


def test_generate_router_config_formats_standard_and_extended_acls():
    dev_cfg = {
        "name": "Router0",
        "interfaces": [
            {
                "name": "FastEthernet0/0",
                "ip": "192.168.10.1",
                "mask": "255.255.255.0",
                "role": "lan",
                "acl": {"name": "WEB_ONLY", "direction": "in"},
            }
        ],
        "acl": [
            {
                "type": "standard",
                "id": "10",
                "rules": [
                    {"action": "permit", "src_network": "192.168.10.0", "src_mask": "255.255.255.0"},
                    {"action": "deny", "src_host": "192.168.10.99"},
                ],
            },
            {
                "type": "extended",
                "name": "WEB_ONLY",
                "rules": [
                    {"action": "permit", "protocol": "tcp", "src_any": True, "dst_host": "10.0.0.10", "dst_port": 80},
                    {"action": "deny", "protocol": "ip", "src_any": True, "dst_any": True},
                ],
            },
        ],
    }

    lines = generate_router_config(dev_cfg, all_devices=[dev_cfg], links_config=[])
    joined = "\n".join(lines)

    assert "access-list 10 permit 192.168.10.0 0.0.0.255" in joined
    assert "access-list 10 deny host 192.168.10.99" in joined
    assert "access-list 10 deny any" in joined
    assert "ip access-list extended WEB_ONLY" in joined
    assert " permit tcp any host 10.0.0.10 eq 80" in joined
    assert " deny ip any any" in joined
    assert " ip access-group WEB_ONLY in" in joined


def test_manual_network_request_preserves_vlan_and_acl_fields():
    request = ManualNetworkRequest(
        base_network="192.168.0.0/24",
        subnets=[SubnetRequest(name="Admin", required_hosts=20)],
        devices=DeviceConfig(routers=1, switches=1, pcs=2, servers=0),
        routing_protocol=RoutingProtocol.STATIC,
        vlans=[{"id": 10, "name": "ADMIN"}],
        acl=[{"type": "standard", "id": "10", "rules": [{"action": "permit", "src_any": True}]}],
    )

    dump = request.model_dump()
    assert dump["vlans"][0]["id"] == 10
    assert dump["acl"][0]["id"] == "10"


def test_save_pkt_file_generates_vlan_trunk_and_acl_configs(tmp_path, monkeypatch):
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    subnets = [
        MockSubnet("Admin", "255.255.255.0", ["192.168.10.2", "192.168.10.126"], gateway="192.168.10.1"),
        MockSubnet("Guest", "255.255.255.0", ["192.168.20.2", "192.168.20.126"], gateway="192.168.20.1"),
    ]
    config = {
        "devices": {"routers": 1, "switches": 1, "pcs": 2, "servers": 0},
        "routing_protocol": "static",
        "vlans": [
            {"id": 10, "name": "ADMIN"},
            {"id": 20, "name": "GUEST"},
        ],
        "acl": [
            {
                "type": "extended",
                "name": "BLOCK_GUEST_WEB",
                "apply_to_vlan": 20,
                "direction": "in",
                "rules": [
                    {"action": "deny", "protocol": "tcp", "src_network": "192.168.20.0", "src_mask": "255.255.255.0", "dst_any": True, "dst_port": 80},
                    {"action": "permit", "protocol": "ip", "src_any": True, "dst_any": True},
                ],
            }
        ],
        "pcs_config": [
            {"vlan_id": 10},
            {"vlan_id": 20},
        ],
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = ET.fromstring(Path(result["xml_path"]).read_text(encoding="utf-8", errors="strict"))
    router0 = _find_device(root, "Router0")
    switch0 = _find_device(root, "Switch0")
    assert router0 is not None
    assert switch0 is not None

    router_lines = _running_lines(router0)
    switch_lines = _running_lines(switch0)
    router_joined = "\n".join(router_lines)
    switch_joined = "\n".join(switch_lines)

    assert "interface FastEthernet0/0.10" in router_joined
    assert "encapsulation dot1Q 10" in router_joined
    assert "ip address 192.168.10.1 255.255.255.0" in router_joined
    assert "interface FastEthernet0/0.20" in router_joined
    assert "encapsulation dot1Q 20" in router_joined
    assert "ip access-list extended BLOCK_GUEST_WEB" in router_joined
    assert "deny tcp 192.168.20.0 0.0.0.255 any eq 80" in router_joined
    assert "ip access-group BLOCK_GUEST_WEB in" in router_joined

    assert "vlan 10" in switch_joined
    assert "vlan 20" in switch_joined
    assert "switchport mode trunk" in switch_joined
    assert "switchport trunk allowed vlan 10,20" in switch_joined
    assert "switchport access vlan 10" in switch_joined
    assert "switchport access vlan 20" in switch_joined
