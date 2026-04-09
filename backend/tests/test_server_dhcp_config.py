import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.pkt_generator import save_pkt_file
from app.services.pkt_generator.server_config import write_dhcp_config, write_email_config


def _engine_with_two_ports() -> ET.Element:
    engine = ET.Element("ENGINE")
    dhcp_servers = ET.SubElement(engine, "DHCP_SERVERS")
    associated_ports = ET.SubElement(dhcp_servers, "ASSOCIATED_PORTS")

    ap0 = ET.SubElement(associated_ports, "ASSOCIATED_PORT")
    ET.SubElement(ap0, "NAME").text = "FastEthernet0"
    ET.SubElement(ap0, "DHCP_SERVER")

    ap1 = ET.SubElement(associated_ports, "ASSOCIATED_PORT")
    ET.SubElement(ap1, "NAME").text = "FastEthernet1"
    # intentionally missing DHCP_SERVER to validate auto-create path
    return engine


def _pool_for_port(engine: ET.Element, if_name: str) -> ET.Element:
    ap = engine.find(f"DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT[NAME='{if_name}']")
    assert ap is not None
    pool = ap.find("DHCP_SERVER/POOLS/POOL")
    assert pool is not None
    return pool


def test_write_dhcp_config_example_1_first_offset_5_no_dns():
    engine = _engine_with_two_ports()
    cfg = {
        "network": "192.168.0.0/24",
        "ip": "192.168.0.2",
        "dhcp_start_offset": 5,
        "provide_dns": False,
    }

    write_dhcp_config(engine, cfg)

    for if_name in ("FastEthernet0", "FastEthernet1"):
        pool = _pool_for_port(engine, if_name)
        assert pool.findtext("NAME") == "serverPool"
        assert pool.findtext("NETWORK") == "192.168.0.0"
        assert pool.findtext("MASK") == "255.255.255.0"
        assert pool.findtext("DEFAULT_ROUTER") == "192.168.0.1"
        # default offset=5 => network + 5 -> .5
        assert pool.findtext("START_IP") == "192.168.0.5"
        assert pool.findtext("END_IP") == "192.168.0.254"
        assert pool.findtext("DNS_SERVER") == "0.0.0.0"
        assert pool.findtext("MAX_USERS") == "252"
        assert pool.find("DHCP_POOL_LEASES") is not None

        ap = engine.find(f"DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT[NAME='{if_name}']")
        assert ap is not None
        srv = ap.find("DHCP_SERVER")
        assert srv is not None
        assert srv.findtext("ENABLED") == "1"
        assert srv.find("DHCP_RESERVATIONS") is not None
        assert srv.find("AUTOCONFIG") is not None


def test_write_dhcp_config_example_2_gateway_explicit_offset_2_provide_dns():
    engine = _engine_with_two_ports()
    cfg = {
        "network": "172.16.0.0/16",
        "gateway_ip": "172.16.0.1",
        "ip": "172.16.0.2",
        "provide_dns": True,
        "dhcp_start_offset": 2,
    }

    write_dhcp_config(engine, cfg)
    pool = _pool_for_port(engine, "FastEthernet0")

    assert pool.findtext("NETWORK") == "172.16.0.0"
    assert pool.findtext("MASK") == "255.255.0.0"
    assert pool.findtext("DEFAULT_ROUTER") == "172.16.0.1"
    assert pool.findtext("START_IP") == "172.16.0.3"
    assert pool.findtext("END_IP") == "172.16.255.254"
    assert pool.findtext("DNS_SERVER") == "172.16.0.2"


def test_write_dhcp_config_example_3_gateway_last_offset_2_external_dns():
    engine = _engine_with_two_ports()
    cfg = {
        "network": "192.168.1.0/28",
        "gateway_mode": "last",
        "ip": "192.168.1.2",
        "dhcp_dns": "8.8.8.8",
        "dhcp_start_offset": 2,
    }

    write_dhcp_config(engine, cfg)
    pool = _pool_for_port(engine, "FastEthernet0")

    assert pool.findtext("NETWORK") == "192.168.1.0"
    assert pool.findtext("MASK") == "255.255.255.240"
    assert pool.findtext("DEFAULT_ROUTER") == "192.168.1.14"
    assert pool.findtext("START_IP") == "192.168.1.3"
    assert pool.findtext("END_IP") == "192.168.1.14"
    assert pool.findtext("DNS_SERVER") == "8.8.8.8"


def test_write_dhcp_config_offset_skips_gateway_and_server_ip():
    engine = _engine_with_two_ports()
    cfg = {
        "network": "10.0.0.0/29",
        "gateway_ip": "10.0.0.3",
        "ip": "10.0.0.4",
        "dhcp_start_offset": 2,  # hosts[2] = .3 (gateway), then .4 (server), then .5
    }

    write_dhcp_config(engine, cfg)
    pool = _pool_for_port(engine, "FastEthernet0")

    assert pool.findtext("START_IP") == "10.0.0.2"
    assert pool.findtext("END_IP") == "10.0.0.6"


def test_write_dhcp_config_derives_network_from_server_ip_and_subnet_when_network_missing():
    engine = _engine_with_two_ports()
    cfg = {
        "ip": "192.168.50.2",
        "subnet": "255.255.255.0",
        "gateway_ip": "192.168.50.1",
        "dhcp_start_offset": 5,
    }

    write_dhcp_config(engine, cfg)
    pool = _pool_for_port(engine, "FastEthernet0")

    assert pool.findtext("NETWORK") == "192.168.50.0"
    assert pool.findtext("MASK") == "255.255.255.0"
    assert pool.findtext("DEFAULT_ROUTER") == "192.168.50.1"
    assert pool.findtext("START_IP") == "192.168.50.5"
    assert pool.findtext("END_IP") == "192.168.50.254"

def test_write_dhcp_config_large_subnet_avoids_memory_error():
    engine = _engine_with_two_ports()
    cfg = {
        "network": "0.0.0.0/0",
        "ip": "0.0.0.2",
    }
    
    # This would crash with MemoryError previously as list(net.hosts()) tried creating 4B elements
    write_dhcp_config(engine, cfg)
    pool = _pool_for_port(engine, "FastEthernet0")
    
    # Network is 0.0.0.0/0
    # First host: 0.0.0.1 (used for gateway by default mode="first")
    # Server IP is 0.0.0.2
    # Default DHCP start offset is 5 => 0.0.0.5
    assert pool.findtext("START_IP") == "0.0.0.5"
    assert pool.findtext("END_IP") == "255.255.255.254"
    assert pool.findtext("NETWORK") == "0.0.0.0"
    assert pool.findtext("MASK") == "0.0.0.0"
    assert pool.findtext("DEFAULT_ROUTER") == "0.0.0.1"


def _engine_with_mail_nodes() -> ET.Element:
    engine = ET.Element("ENGINE")
    ET.SubElement(engine, "SMTP_SERVER")
    ET.SubElement(engine, "POP3_SERVER")
    return engine


def test_write_email_config_default_users_and_domain():
    engine = _engine_with_mail_nodes()
    cfg = {"server_services": ["smtp"]}

    write_email_config(engine, cfg)

    smtp = engine.find("SMTP_SERVER")
    pop3 = engine.find("POP3_SERVER")
    assert smtp is not None
    assert pop3 is not None

    assert smtp.findtext("ENABLED") == "1"
    assert pop3.findtext("ENABLED") == "1"
    assert smtp.findtext("DOMAIN") == "mail.local"
    assert pop3.findtext("DOMAIN") == "mail.local"

    smtp_accounts = smtp.findall("USER_ACCOUNT_MNGR/ACCOUNT")
    assert len(smtp_accounts) == 2
    assert smtp_accounts[0].findtext("USERNAME") == "user1"
    assert smtp_accounts[0].findtext("PASSWORD") == "1234"
    assert smtp_accounts[1].findtext("USERNAME") == "user2"
    assert smtp_accounts[1].findtext("PASSWORD") == "1234"


def test_write_email_config_uses_explicit_users_and_domain():
    engine = _engine_with_mail_nodes()
    cfg = {
        "server_services": ["email"],
        "mail_domain": "azienda.local",
        "mail_users": [
            {"username": "alice", "password": "pwdA"},
            {"username": "bob", "password": "pwdB"},
        ],
    }

    write_email_config(engine, cfg)

    smtp = engine.find("SMTP_SERVER")
    assert smtp is not None
    assert smtp.findtext("DOMAIN") == "azienda.local"
    accounts = smtp.findall("USER_ACCOUNT_MNGR/ACCOUNT")
    assert len(accounts) == 2
    assert accounts[0].findtext("USERNAME") == "alice"
    assert accounts[0].findtext("PASSWORD") == "pwdA"
    assert accounts[1].findtext("USERNAME") == "bob"
    assert accounts[1].findtext("PASSWORD") == "pwdB"


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
    return device.find("ENGINE/MODULE/SLOT/MODULE/PORT")


def test_pc_email_client_uses_mail_server_ip(tmp_path, monkeypatch):
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
        "devices": {"routers": 1, "switches": 1, "pcs": 2, "servers": 1},
        "server_services": ["email"],
        "servers_config": [
            {
                "services": ["email"],
                "mail_domain": "mail.local",
                "mail_users": [
                    {"username": "user1", "password": "1234"},
                    {"username": "user2", "password": "1234"},
                ],
            }
        ],
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
    assert server_ip

    pc0 = _find_device(root, "PC0")
    assert pc0 is not None
    email = pc0.find("ENGINE/EMAIL_CLIENT")
    assert email is not None
    assert (email.findtext("ENABLED") or "").strip() == "1"
    assert (email.findtext("INCOMING_MAIL_SERVER") or "").strip() == server_ip
    assert (email.findtext("OUTGOING_MAIL_SERVER") or "").strip() == server_ip
    assert (email.findtext("USERNAME") or "").strip() == "user1"


def test_pc_email_client_uses_mail_server_from_same_vlan(tmp_path, monkeypatch):
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    subnets = [
        MockSubnet(
            "Admin",
            "255.255.255.0",
            ["192.168.10.2", "192.168.10.126"],
            gateway="192.168.10.1",
        ),
        MockSubnet(
            "Guest",
            "255.255.255.0",
            ["192.168.20.2", "192.168.20.126"],
            gateway="192.168.20.1",
        ),
    ]
    config = {
        "devices": {"routers": 1, "switches": 1, "pcs": 2, "servers": 2},
        "routing_protocol": "static",
        "vlans": [
            {"id": 10, "name": "ADMIN"},
            {"id": 20, "name": "GUEST"},
        ],
        "servers_config": [
            {
                "services": ["email"],
                "vlan_id": 10,
                "mail_domain": "admin.local",
                "mail_users": [{"username": "admin1", "password": "pw-admin"}],
            },
            {
                "services": ["email"],
                "vlan_id": 20,
                "mail_domain": "guest.local",
                "mail_users": [{"username": "guest1", "password": "pw-guest"}],
            },
        ],
        "pcs_config": [
            {"vlan_id": 10},
            {"vlan_id": 20},
        ],
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    devices = {device["name"]: device for device in result["devices"]}
    server0 = devices["Server0"]
    server1 = devices["Server1"]
    pc0 = devices["PC0"]
    pc1 = devices["PC1"]

    assert server0["vlan_id"] == 10
    assert server1["vlan_id"] == 20
    assert pc0["mail_server_ip"] == server0["ip"]
    assert pc1["mail_server_ip"] == server1["ip"]
    assert pc0["mail_username"] == "admin1"
    assert pc1["mail_username"] == "guest1"
    assert pc0["mail_domain"] == "admin.local"
    assert pc1["mail_domain"] == "guest.local"
