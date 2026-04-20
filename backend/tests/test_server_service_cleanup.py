import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.pkt_generator import save_pkt_file
from app.services.pkt_generator.generator_components.device_build import _configure_server_services


def _engine_with_all_services() -> ET.Element:
    engine = ET.Element("ENGINE")

    dns = ET.SubElement(engine, "DNS_SERVER")
    ET.SubElement(dns, "ENABLED").text = "1"
    dns_db = ET.SubElement(dns, "NAMESERVER-DATABASE")
    record = ET.SubElement(dns_db, "RESOURCE-RECORD")
    ET.SubElement(record, "NAME").text = "old.local"
    ET.SubElement(record, "IPADDRESS").text = "192.168.1.50"

    dhcp_servers = ET.SubElement(engine, "DHCP_SERVERS")
    associated_ports = ET.SubElement(dhcp_servers, "ASSOCIATED_PORTS")
    ap = ET.SubElement(associated_ports, "ASSOCIATED_PORT")
    ET.SubElement(ap, "NAME").text = "FastEthernet0"
    dhcp_server = ET.SubElement(ap, "DHCP_SERVER")
    ET.SubElement(dhcp_server, "ENABLED").text = "1"
    pools = ET.SubElement(dhcp_server, "POOLS")
    pool = ET.SubElement(pools, "POOL")
    ET.SubElement(pool, "START_IP").text = "192.168.1.10"
    ET.SubElement(pool, "END_IP").text = "192.168.1.100"
    reservations = ET.SubElement(dhcp_server, "DHCP_RESERVATIONS")
    ET.SubElement(reservations, "RESERVATION")
    ET.SubElement(dhcp_server, "AUTOCONFIG")

    ftp = ET.SubElement(engine, "FTP_SERVER")
    ET.SubElement(ftp, "ENABLED").text = "1"
    users = ET.SubElement(ftp, "USERS")
    ftp_user = ET.SubElement(users, "USER")
    ET.SubElement(ftp_user, "USERNAME").text = "legacy"
    acct_mgr = ET.SubElement(ftp, "USER_ACCOUNT_MNGR")
    acct = ET.SubElement(acct_mgr, "ACCOUNT")
    ET.SubElement(acct, "USERNAME").text = "legacy"

    smtp = ET.SubElement(engine, "SMTP_SERVER")
    ET.SubElement(smtp, "ENABLED").text = "1"
    ET.SubElement(smtp, "DOMAIN").text = "legacy.local"
    smtp_mgr = ET.SubElement(smtp, "USER_ACCOUNT_MNGR")
    smtp_acct = ET.SubElement(smtp_mgr, "ACCOUNT")
    ET.SubElement(smtp_acct, "USERNAME").text = "legacy"

    pop3 = ET.SubElement(engine, "POP3_SERVER")
    ET.SubElement(pop3, "ENABLED").text = "1"
    ET.SubElement(pop3, "DOMAIN").text = "legacy.local"
    pop3_mgr = ET.SubElement(pop3, "USER_ACCOUNT_MNGR")
    pop3_acct = ET.SubElement(pop3_mgr, "ACCOUNT")
    ET.SubElement(pop3_acct, "USERNAME").text = "legacy"

    return engine


def test_disabled_dhcp_removes_stale_pool_values():
    engine = _engine_with_all_services()

    _configure_server_services(engine, {"server_services": []})

    dhcp_server = engine.find("DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER")
    assert dhcp_server is not None
    assert dhcp_server.findtext("ENABLED") == "0"
    pools = dhcp_server.find("POOLS")
    assert pools is not None
    assert pools.findall("POOL") == []
    reservations = dhcp_server.find("DHCP_RESERVATIONS")
    assert reservations is not None
    assert list(reservations) == []


def test_disabled_dns_clears_stale_records():
    engine = _engine_with_all_services()

    _configure_server_services(engine, {"server_services": []})

    dns = engine.find("DNS_SERVER")
    assert dns is not None
    assert dns.findtext("ENABLED") == "0"
    db = dns.find("NAMESERVER-DATABASE")
    assert db is not None
    assert list(db) == []


def test_disabled_mail_services_clear_accounts_and_domain():
    engine = _engine_with_all_services()

    _configure_server_services(engine, {"server_services": []})

    for tag in ("SMTP_SERVER", "POP3_SERVER"):
        node = engine.find(tag)
        assert node is not None
        assert node.findtext("ENABLED") == "0"
        assert node.findtext("DOMAIN") == ""
        mgr = node.find("USER_ACCOUNT_MNGR")
        assert mgr is not None
        assert list(mgr) == []


def test_disabled_ftp_clears_users_and_accounts():
    engine = _engine_with_all_services()

    _configure_server_services(engine, {"server_services": []})

    ftp = engine.find("FTP_SERVER")
    assert ftp is not None
    assert ftp.findtext("ENABLED") == "0"
    users = ftp.find("USERS")
    assert users is not None
    assert list(users) == []
    acct_mgr = ftp.find("USER_ACCOUNT_MNGR")
    assert acct_mgr is not None
    assert list(acct_mgr) == []


def test_enabled_services_rewrite_fresh_data_without_legacy_residue():
    engine = _engine_with_all_services()

    _configure_server_services(
        engine,
        {
            "server_services": ["dns", "dhcp", "ftp", "email"],
            "ip": "192.168.1.2",
            "subnet": "255.255.255.0",
            "gateway_ip": "192.168.1.1",
            "dns_records": [{"hostname": "web1.local", "ip": "192.168.1.20"}],
            "ftp_users": [{"username": "alice", "password": "pw", "permissions": "rw"}],
            "mail_domain": "lab.local",
            "mail_users": [{"username": "bob", "password": "pw2"}],
        },
    )

    dns = engine.find("DNS_SERVER")
    assert dns is not None
    assert dns.findtext("ENABLED") == "1"
    assert dns.find("NAMESERVER-DATABASE/RESOURCE-RECORD/NAME").text == "web1.local"

    dhcp_server = engine.find("DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER")
    assert dhcp_server is not None
    assert dhcp_server.findtext("ENABLED") == "1"
    pools = dhcp_server.find("POOLS")
    assert pools is not None
    assert len(pools.findall("POOL")) == 1
    assert pools.find("POOL/START_IP").text == "192.168.1.5"

    ftp = engine.find("FTP_SERVER")
    assert ftp is not None
    assert ftp.findtext("ENABLED") == "1"
    ftp_users = ftp.findall("USERS/USER/USERNAME")
    assert [node.text for node in ftp_users] == ["cisco", "alice"]

    smtp = engine.find("SMTP_SERVER")
    pop3 = engine.find("POP3_SERVER")
    assert smtp is not None
    assert pop3 is not None
    assert smtp.findtext("DOMAIN") == "lab.local"
    assert pop3.findtext("DOMAIN") == "lab.local"
    assert smtp.find("USER_ACCOUNT_MNGR/ACCOUNT/USERNAME").text == "bob"


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


def _service_enabled(node: ET.Element | None, path: str) -> str:
    if node is None:
        return ""
    return (node.findtext(path) or "").strip()


def test_generated_server_service_flags_match_enabled_and_disabled_services(tmp_path, monkeypatch):
    template_path = Path(__file__).resolve().parent.parent / "templates" / "simple_ref.pkt"
    monkeypatch.setenv("PKT_TEMPLATE_PATH", str(template_path))

    subnets = [
        MockSubnet("LAN_A", "255.255.255.0", ["192.168.10.2", "192.168.10.126"], gateway="192.168.10.1"),
        MockSubnet("LAN_B", "255.255.255.0", ["192.168.20.2", "192.168.20.126"], gateway="192.168.20.1"),
    ]
    config = {
        "devices": {"routers": 1, "switches": 2, "pcs": 0, "servers": 2},
        "routing_protocol": "static",
        "servers_config": [
            {
                "services": ["dns", "dhcp", "ftp", "http", "https"],
                "dns_records": [{"hostname": "core.local", "ip": "192.168.10.2"}],
                "ftp_users": [{"username": "alice", "password": "pw"}],
            },
            {
                "services": [],
            },
        ],
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = ET.fromstring(Path(result["xml_path"]).read_text(encoding="utf-8", errors="strict"))
    server0 = _find_device(root, "Server0")
    server1 = _find_device(root, "Server1")
    assert server0 is not None
    assert server1 is not None

    assert _service_enabled(server0, "ENGINE/DNS_SERVER/ENABLED") == "1"
    assert _service_enabled(server0, "ENGINE/DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED") == "1"
    assert _service_enabled(server0, "ENGINE/FTP_SERVER/ENABLED") == "1"
    assert _service_enabled(server0, "ENGINE/HTTP_SERVER/ENABLED") == "1"
    assert _service_enabled(server0, "ENGINE/HTTPS_SERVER/HTTPSENABLED") == "1"

    assert _service_enabled(server1, "ENGINE/DNS_SERVER/ENABLED") == "0"
    assert _service_enabled(server1, "ENGINE/DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED") == "0"
    assert _service_enabled(server1, "ENGINE/FTP_SERVER/ENABLED") == "0"
    assert _service_enabled(server1, "ENGINE/HTTP_SERVER/ENABLED") == "0"
    assert _service_enabled(server1, "ENGINE/HTTPS_SERVER/HTTPSENABLED") == "0"
