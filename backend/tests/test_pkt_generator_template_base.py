from __future__ import annotations

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator


def _decrypt_xml(pkt_path) -> ET.Element:
    xml = decrypt_pkt_data(pkt_path.read_bytes()).decode("utf-8", errors="strict")
    return ET.fromstring(xml)


def _assert_topology(root: ET.Element, expected_devices: list[str], expected_link_count: int) -> None:
    devices = root.findall("NETWORK/DEVICES/DEVICE")
    names = [d.findtext("ENGINE/NAME") or "" for d in devices]
    assert set(names) == set(expected_devices)

    for d in devices:
        assert (d.findtext("WORKSPACE/PHYSICAL") or "").strip()

    links = root.findall("NETWORK/LINKS/LINK")
    assert len(links) == expected_link_count

    pw = root.find("PHYSICALWORKSPACE")
    assert pw is not None
    assert len(list(pw.iter("NODE"))) > 0


def test_generate_router2_switch_pc_base(tmp_path) -> None:
    out = tmp_path / "router2_switch_pc.pkt"
    generator = PKTGenerator()
    devices_config = [
        {"name": "Router0", "type": "router-2port"},
        {"name": "Switch0", "type": "switch-24port"},
        {"name": "PC0", "type": "pc"},
    ]
    links_config = [
        {"from": "Router0", "to": "Switch0", "from_port": "FastEthernet0/0", "to_port": "FastEthernet0/1"},
        {"from": "Switch0", "to": "PC0", "from_port": "FastEthernet0/2", "to_port": "FastEthernet0"},
    ]

    generator.generate(devices_config, links_config=links_config, output_path=str(out))
    root = _decrypt_xml(out)
    _assert_topology(root, ["Router0", "Switch0", "PC0"], expected_link_count=2)


def test_generate_router8_switch_pc_base(tmp_path) -> None:
    out = tmp_path / "router8_switch_pc.pkt"
    generator = PKTGenerator()
    devices_config = [
        {"name": "Router0", "type": "router-8port"},
        {"name": "Switch0", "type": "switch-24port"},
        {"name": "PC0", "type": "pc"},
    ]
    links_config = [
        {"from": "Router0", "to": "Switch0", "from_port": "FastEthernet0/0", "to_port": "FastEthernet0/1"},
        {"from": "Switch0", "to": "PC0", "from_port": "FastEthernet0/2", "to_port": "FastEthernet0"},
    ]

    generator.generate(devices_config, links_config=links_config, output_path=str(out))
    root = _decrypt_xml(out)
    _assert_topology(root, ["Router0", "Switch0", "PC0"], expected_link_count=2)


def test_generate_multi_router_switch_pc(tmp_path) -> None:
    out = tmp_path / "multi_topology.pkt"
    generator = PKTGenerator()
    devices_config = [
        {"name": "Router0", "type": "router-8port"},
        {"name": "Router1", "type": "router-2port"},
        {"name": "Switch0", "type": "switch-24port"},
        {"name": "Switch1", "type": "switch-24port"},
        {"name": "PC0", "type": "pc"},
        {"name": "PC1", "type": "pc"},
        {"name": "PC2", "type": "pc"},
    ]
    links_config = [
        {"from": "Router0", "to": "Router1", "from_port": "FastEthernet0/0", "to_port": "FastEthernet0/0"},
        {"from": "Router0", "to": "Switch0", "from_port": "FastEthernet0/1", "to_port": "FastEthernet0/1"},
        {"from": "Router1", "to": "Switch1", "from_port": "FastEthernet0/1", "to_port": "FastEthernet0/1"},
        {"from": "Switch0", "to": "PC0", "from_port": "FastEthernet0/2", "to_port": "FastEthernet0"},
        {"from": "Switch0", "to": "PC1", "from_port": "FastEthernet0/3", "to_port": "FastEthernet0"},
        {"from": "Switch1", "to": "PC2", "from_port": "FastEthernet0/2", "to_port": "FastEthernet0"},
    ]

    generator.generate(devices_config, links_config=links_config, output_path=str(out))
    root = _decrypt_xml(out)
    _assert_topology(
        root,
        ["Router0", "Router1", "Switch0", "Switch1", "PC0", "PC1", "PC2"],
        expected_link_count=6,
    )
