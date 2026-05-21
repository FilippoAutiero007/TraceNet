import xml.etree.ElementTree as ET
from pathlib import Path

from app.models.manual_schemas import ManualNetworkRequest
from app.models.schemas import DeviceConfig, RoutingProtocol, SubnetRequest
from app.services.pkt_generator import save_pkt_file
from app.services.pkt_generator.config_generator import generate_router_config, generate_switch_config


class MockSubnet:
    def __init__(self, name: str, mask: str, usable_range: list[str], gateway: str, network: str = "", site: str = ""):
        self.name = name
        self.mask = mask
        self.usable_range = usable_range
        self.gateway = gateway
        self.network = network
        self.site = site


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


def test_generate_router_config_supports_acl_remarks_and_port_ranges():
    dev_cfg = {
        "name": "Router0",
        "interfaces": [
            {
                "name": "FastEthernet0/0",
                "ip": "192.168.10.1",
                "mask": "255.255.255.0",
                "role": "lan",
                "acl": {"name": "APP_FILTER", "direction": "out"},
            }
        ],
        "acl": [
            {
                "type": "standard",
                "id": "15",
                "rules": [
                    {"remark": "ALLOW_ADMIN"},
                    {"action": "permit", "src_host": "192.168.10.10"},
                ],
            },
            {
                "type": "extended",
                "name": "APP_FILTER",
                "rules": [
                    {"remark": "ALLOW_APP_RANGE"},
                    {
                        "action": "permit",
                        "protocol": "tcp",
                        "src_any": True,
                        "dst_network": "10.0.0.0",
                        "dst_mask": "255.255.255.0",
                        "dst_port_op": "range",
                        "dst_port": "1000 2000",
                    },
                ],
            },
        ],
    }

    lines = generate_router_config(dev_cfg, all_devices=[dev_cfg], links_config=[])
    joined = "\n".join(lines)

    assert "access-list 15 remark ALLOW_ADMIN" in joined
    assert "access-list 15 permit host 192.168.10.10" in joined
    assert " remark ALLOW_APP_RANGE" in joined
    assert " permit tcp any 10.0.0.0 0.0.0.255 range 1000 2000" in joined
    assert " ip access-group APP_FILTER out" in joined


def test_generate_switch_config_uses_vlan_definitions_for_trunk_fallback():
    lines = generate_switch_config(
        {
            "name": "Switch0",
            "vlans": [
                {"id": 10, "name": "ADMIN"},
                {"id": 30, "name": "VOICE", "native": True},
            ],
            "trunk_ports": ["FastEthernet0/1"],
        }
    )
    joined = "\n".join(lines)

    assert " switchport mode trunk" in joined
    assert " switchport trunk native vlan 30" in joined
    assert " switchport trunk allowed vlan 10,30" in joined


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


def test_save_pkt_file_applies_acl_to_explicit_interface_and_keeps_vlan_trunks(tmp_path, monkeypatch):
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    subnets = [
        MockSubnet("Office", "255.255.255.0", ["192.168.30.2", "192.168.30.126"], gateway="192.168.30.1"),
        MockSubnet("Servers", "255.255.255.0", ["192.168.40.2", "192.168.40.126"], gateway="192.168.40.1"),
    ]
    config = {
        "devices": {"routers": 1, "switches": 1, "pcs": 2, "servers": 0},
        "routing_protocol": "static",
        "vlans": [
            {"id": 30, "name": "OFFICE"},
            {"id": 40, "name": "SERVERS", "native": True},
        ],
        "acl": [
            {
                "type": "extended",
                "name": "LIMIT_OFFICE",
                "apply_to_interface": "FastEthernet0/0.30",
                "direction": "out",
                "rules": [
                    {"action": "permit", "protocol": "ip", "src_any": True, "dst_any": True},
                ],
            }
        ],
        "pcs_config": [
            {"vlan_id": 30},
            {"vlan_id": 40},
        ],
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = ET.fromstring(Path(result["xml_path"]).read_text(encoding="utf-8", errors="strict"))
    router0 = _find_device(root, "Router0")
    switch0 = _find_device(root, "Switch0")
    assert router0 is not None
    assert switch0 is not None

    router_joined = "\n".join(_running_lines(router0))
    switch_joined = "\n".join(_running_lines(switch0))

    assert "interface FastEthernet0/0.30" in router_joined
    assert "ip access-group LIMIT_OFFICE out" in router_joined
    assert "interface FastEthernet0/0.40" in router_joined
    assert "switchport trunk native vlan 40" in switch_joined
    assert "switchport trunk allowed vlan 30,40" in switch_joined


def test_save_pkt_file_generates_semantic_requirement_acls_and_nat(tmp_path, monkeypatch):
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    subnets = [
        MockSubnet("BOLOGNA_TECH_FLOOR1", "255.255.255.192", ["192.168.1.2", "192.168.1.62"], gateway="192.168.1.1", network="192.168.1.0/26", site="Bologna"),
        MockSubnet("BOLOGNA_TECH_FLOOR2", "255.255.255.192", ["192.168.1.66", "192.168.1.126"], gateway="192.168.1.65", network="192.168.1.64/26", site="Bologna"),
        MockSubnet("BOLOGNA_MARKETING", "255.255.255.192", ["192.168.1.130", "192.168.1.190"], gateway="192.168.1.129", network="192.168.1.128/26", site="Bologna"),
        MockSubnet("BOLOGNA_SERVERS", "255.255.255.192", ["192.168.1.194", "192.168.1.254"], gateway="192.168.1.193", network="192.168.1.192/26", site="Bologna"),
        MockSubnet("MONDRAGONE_REMOTE", "255.255.255.248", ["10.255.250.2", "10.255.250.6"], gateway="10.255.250.1", network="10.255.250.0/29", site="Mondragone"),
    ]
    config = {
        "devices": {"routers": 3, "switches": 5, "pcs": 8, "servers": 4},
        "routing_protocol": "static",
        "nat": {"type": "pat"},
        "requirements": [
            "Block Marketing to Technical office communication",
            "Allow Mondragone access only to the mail server",
            "Block Technical office access to the web server",
        ],
        "servers_config": [
            {"services": ["dhcp"], "hostname": "marketing-dhcp.local", "subnet_name": "BOLOGNA_MARKETING"},
            {"services": ["dns"], "hostname": "dns.horizon.local", "subnet_name": "BOLOGNA_SERVERS"},
            {"services": ["http"], "hostname": "web.horizon.local", "subnet_name": "BOLOGNA_SERVERS"},
            {"services": ["email"], "hostname": "mail.horizon.local", "subnet_name": "BOLOGNA_SERVERS"},
        ],
        "pcs_config": [
            {"subnet_name": "BOLOGNA_MARKETING"},
            {"subnet_name": "BOLOGNA_MARKETING"},
            {"subnet_name": "BOLOGNA_MARKETING"},
            {"subnet_name": "BOLOGNA_MARKETING"},
            {"subnet_name": "BOLOGNA_MARKETING"},
            {"subnet_name": "MONDRAGONE_REMOTE"},
            {"subnet_name": "MONDRAGONE_REMOTE"},
            {"subnet_name": "MONDRAGONE_REMOTE"},
        ],
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = ET.fromstring(Path(result["xml_path"]).read_text(encoding="utf-8", errors="strict"))
    router_lines = []
    for idx in range(3):
        router = _find_device(root, f"Router{idx}")
        assert router is not None
        router_lines.extend(_running_lines(router))
    joined = "\n".join(router_lines)

    assert "ip nat inside source list 10 interface" in joined
    assert "BLOCK_MARKETING_TO_TECH" in joined
    assert "MONDRAGONE_MAIL_ONLY" in joined
    assert "BLOCK_BOLOGNA_TECH_FLOOR1_WEB" in joined or "BLOCK_BOLOGNA_TECH_FLOOR2_WEB" in joined
