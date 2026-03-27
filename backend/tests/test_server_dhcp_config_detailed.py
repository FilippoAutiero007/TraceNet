import xml.etree.ElementTree as ET

from app.services.pkt_generator.server_config import write_dhcp_config


def _engine_one_port(with_dhcp_server: bool = True) -> ET.Element:
    engine = ET.Element("ENGINE")
    dhcp_servers = ET.SubElement(engine, "DHCP_SERVERS")
    associated_ports = ET.SubElement(dhcp_servers, "ASSOCIATED_PORTS")
    ap = ET.SubElement(associated_ports, "ASSOCIATED_PORT")
    ET.SubElement(ap, "NAME").text = "FastEthernet0"
    if with_dhcp_server:
        ET.SubElement(ap, "DHCP_SERVER")
    return engine


def _engine_two_ports() -> ET.Element:
    engine = ET.Element("ENGINE")
    dhcp_servers = ET.SubElement(engine, "DHCP_SERVERS")
    associated_ports = ET.SubElement(dhcp_servers, "ASSOCIATED_PORTS")
    ap0 = ET.SubElement(associated_ports, "ASSOCIATED_PORT")
    ET.SubElement(ap0, "NAME").text = "FastEthernet0"
    ET.SubElement(ap0, "DHCP_SERVER")
    ap1 = ET.SubElement(associated_ports, "ASSOCIATED_PORT")
    ET.SubElement(ap1, "NAME").text = "FastEthernet1"
    return engine


def _engine_server_with_port(ip: str, mask: str, gateway: str = "") -> ET.Element:
    engine = ET.Element("ENGINE")
    module = ET.SubElement(engine, "MODULE")
    slot = ET.SubElement(module, "SLOT")
    slot_mod = ET.SubElement(slot, "MODULE")
    port = ET.SubElement(slot_mod, "PORT")
    ET.SubElement(port, "IP").text = ip
    ET.SubElement(port, "SUBNET").text = mask
    if gateway:
        ET.SubElement(engine, "GATEWAY").text = gateway

    dhcp_servers = ET.SubElement(engine, "DHCP_SERVERS")
    associated_ports = ET.SubElement(dhcp_servers, "ASSOCIATED_PORTS")
    ap = ET.SubElement(associated_ports, "ASSOCIATED_PORT")
    ET.SubElement(ap, "NAME").text = "FastEthernet0"
    ET.SubElement(ap, "DHCP_SERVER")
    return engine


def _pool(engine: ET.Element, if_name: str = "FastEthernet0") -> ET.Element:
    ap = engine.find(f"DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT[NAME='{if_name}']")
    assert ap is not None
    node = ap.find("DHCP_SERVER/POOLS/POOL")
    assert node is not None
    return node


def test_priority_network_over_mask_and_subnet():
    engine = _engine_one_port()
    cfg = {
        "network": "10.20.30.0/24",
        "mask": "255.255.255.128",
        "subnet": "255.255.255.192",
        "ip": "10.20.30.2",
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("NETWORK") == "10.20.30.0"
    assert p.findtext("MASK") == "255.255.255.0"
    assert p.findtext("START_IP") == "10.20.30.5"


def test_fallback_uses_server_ip_plus_mask_when_network_missing():
    engine = _engine_one_port()
    cfg = {"ip": "172.16.0.2", "subnet": "255.255.0.0", "gateway_ip": "172.16.0.1"}
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("NETWORK") == "172.16.0.0"
    assert p.findtext("MASK") == "255.255.0.0"
    assert p.findtext("START_IP") == "172.16.0.5"
    assert p.findtext("END_IP") == "172.16.255.254"


def test_network_without_cidr_uses_mask_for_subnet_derivation():
    engine = _engine_one_port()
    cfg = {
        "network": "192.168.1.0",
        "subnet": "255.255.255.0",
        "gateway_ip": "192.168.1.1",
        "ip": "192.168.1.2",
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("NETWORK") == "192.168.1.0"
    assert p.findtext("MASK") == "255.255.255.0"
    assert p.findtext("START_IP") == "192.168.1.5"


def test_gateway_explicit_has_priority_over_gateway_mode():
    engine = _engine_one_port()
    cfg = {
        "network": "192.168.10.0/24",
        "gateway_ip": "192.168.10.1",
        "gateway_mode": "last",
        "ip": "192.168.10.2",
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("DEFAULT_ROUTER") == "192.168.10.1"


def test_gateway_modes_all_variants():
    base = {"network": "192.168.1.0/28", "ip": "192.168.1.2", "dhcp_start_offset": 2}
    expected = {
        "first": "192.168.1.1",
        "last": "192.168.1.14",
        "penultimate": "192.168.1.13",
        "broadcast": "192.168.1.15",
    }
    for mode, gw in expected.items():
        engine = _engine_one_port()
        cfg = dict(base)
        cfg["gateway_mode"] = mode
        write_dhcp_config(engine, cfg)
        assert _pool(engine).findtext("DEFAULT_ROUTER") == gw


def test_start_offset_minimum_clamped_to_2():
    engine = _engine_one_port()
    cfg = {
        "network": "10.0.0.0/29",
        "gateway_ip": "10.0.0.1",
        "ip": "10.0.0.2",
        "dhcp_start_offset": 0,
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("START_IP") == "10.0.0.3"


def test_start_offset_skips_gateway_and_server_until_free_ip():
    engine = _engine_one_port()
    cfg = {
        "network": "10.0.0.0/29",
        "gateway_ip": "10.0.0.3",
        "ip": "10.0.0.4",
        "dhcp_start_offset": 2,
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("START_IP") == "10.0.0.2"
    assert p.findtext("END_IP") == "10.0.0.6"


def test_start_ip_falls_back_to_zero_when_no_candidate_after_offset():
    engine = _engine_one_port()
    cfg = {
        "network": "10.0.0.0/30",  # hosts: .1 .2
        "gateway_ip": "10.0.0.1",
        "ip": "10.0.0.2",
        "dhcp_start_offset": 2,
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("START_IP") == "0.0.0.0"
    assert p.findtext("END_IP") == "10.0.0.2"


def test_start_ip_falls_back_to_first_usable_when_offset_is_too_large():
    engine = _engine_one_port()
    cfg = {
        "network": "192.168.1.0/24",
        "gateway_ip": "192.168.1.1",
        "ip": "192.168.1.2",
        "dhcp_start_offset": 999,
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("START_IP") == "192.168.1.3"


def test_dns_rules_default_provide_dns_and_explicit_dns():
    engine = _engine_one_port()
    cfg_default = {"network": "192.168.0.0/24", "ip": "192.168.0.2"}
    write_dhcp_config(engine, cfg_default)
    assert _pool(engine).findtext("DNS_SERVER") == "0.0.0.0"

    cfg_provide_dns = {"network": "192.168.0.0/24", "ip": "192.168.0.2", "provide_dns": True}
    write_dhcp_config(engine, cfg_provide_dns)
    assert _pool(engine).findtext("DNS_SERVER") == "192.168.0.2"

    cfg_explicit_dns = {
        "network": "192.168.0.0/24",
        "ip": "192.168.0.2",
        "provide_dns": True,
        "dhcp_dns": "8.8.8.8",
    }
    write_dhcp_config(engine, cfg_explicit_dns)
    assert _pool(engine).findtext("DNS_SERVER") == "8.8.8.8"


def test_max_users_defaults_and_overrides():
    engine = _engine_one_port()
    write_dhcp_config(engine, {"network": "192.168.0.0/25"})
    assert _pool(engine).findtext("MAX_USERS") == "124"

    write_dhcp_config(engine, {"network": "172.16.0.0/16"})
    assert _pool(engine).findtext("MAX_USERS") == "512"

    write_dhcp_config(engine, {"network": "192.168.0.0/24", "dhcp_max_users": 42})
    assert _pool(engine).findtext("MAX_USERS") == "42"


def test_lease_domain_tftp_wlc_custom_values_are_written():
    engine = _engine_one_port()
    cfg = {
        "network": "192.168.0.0/24",
        "dhcp_lease_time": 123456,
        "domain_name": "lab.local",
        "tftp_address": "192.168.0.10",
        "wlc_address": "192.168.0.11",
    }
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("LEASE_TIME") == "123456"
    assert p.findtext("DOMAIN_NAME") == "lab.local"
    assert p.findtext("TFTP_ADDRESS") == "192.168.0.10"
    assert p.findtext("WLC_ADDRESS") == "192.168.0.11"


def test_required_empty_nodes_and_multi_port_iteration():
    engine = _engine_two_ports()
    cfg = {"network": "192.168.0.0/24", "ip": "192.168.0.2"}
    write_dhcp_config(engine, cfg)

    for if_name in ("FastEthernet0", "FastEthernet1"):
        p = _pool(engine, if_name)
        assert p.find("DHCP_POOL_LEASES") is not None
        ap = engine.find(f"DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT[NAME='{if_name}']")
        assert ap is not None
        srv = ap.find("DHCP_SERVER")
        assert srv is not None
        assert srv.find("DHCP_RESERVATIONS") is not None
        assert srv.find("AUTOCONFIG") is not None


def test_idempotent_rewrite_does_not_duplicate_core_nodes():
    engine = _engine_one_port(with_dhcp_server=False)
    cfg = {"network": "192.168.0.0/24", "ip": "192.168.0.2"}

    write_dhcp_config(engine, cfg)
    write_dhcp_config(engine, cfg)

    ap = engine.find("DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT")
    assert ap is not None
    assert len(ap.findall("DHCP_SERVER")) == 1

    srv = ap.find("DHCP_SERVER")
    assert srv is not None
    assert len(srv.findall("POOLS")) == 1
    pools = srv.find("POOLS")
    assert pools is not None
    assert len(pools.findall("POOL")) == 1
    pool = pools.find("POOL")
    assert pool is not None
    assert len(pool.findall("DHCP_POOL_LEASES")) == 1
    assert len(srv.findall("DHCP_RESERVATIONS")) == 1
    assert len(srv.findall("AUTOCONFIG")) == 1


def test_invalid_ip_input_triggers_zero_fallbacks():
    engine = _engine_one_port()
    cfg = {"network": "not-a-network", "gateway_ip": "bad", "ip": "also-bad"}
    write_dhcp_config(engine, cfg)
    p = _pool(engine)
    assert p.findtext("NETWORK") == "0.0.0.0"
    assert p.findtext("MASK") == "0.0.0.0"
    assert p.findtext("DEFAULT_ROUTER") == "0.0.0.0"
    assert p.findtext("START_IP") == "0.0.0.0"
    assert p.findtext("END_IP") == "0.0.0.0"


def test_derives_dhcp_network_from_engine_port_when_cfg_missing():
    engine = _engine_server_with_port("192.168.77.2", "255.255.255.0", gateway="192.168.77.1")
    write_dhcp_config(engine, {})
    p = _pool(engine)
    assert p.findtext("NETWORK") == "192.168.77.0"
    assert p.findtext("MASK") == "255.255.255.0"
    assert p.findtext("DEFAULT_ROUTER") == "192.168.77.1"
    assert p.findtext("START_IP") == "192.168.77.5"
