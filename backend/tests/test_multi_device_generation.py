from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.pkt_generator import save_pkt_file


class MockSubnet:
    def __init__(self, name: str, mask: str, usable_range: list[str], gateway: str):
        self.name = name
        self.mask = mask
        self.usable_range = usable_range
        self.gateway = gateway


def _load_root(xml_path: str) -> ET.Element:
    return ET.fromstring(Path(xml_path).read_text(encoding="utf-8", errors="strict"))


def _device_nodes(root: ET.Element) -> list[ET.Element]:
    return root.findall("NETWORK/DEVICES/DEVICE")


def _switch_to_pc_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        link
        for link in links
        if str(link.get("from", "")).startswith("Switch") and str(link.get("to", "")).startswith("PC")
    ]


def test_multi_device_id_uniqueness(tmp_path):
    """Generated devices must keep unique save-ref identifiers in the XML."""
    subnets = [
        MockSubnet(
            "Subnet1",
            "255.255.255.0",
            ["192.168.1.10", "192.168.1.200"],
            gateway="192.168.1.1",
        )
    ]
    config = {
        "devices": {
            "routers": 1,
            "switches": 1,
            "pcs": 5,
            "servers": 0,
        }
    }

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    root = _load_root(result["xml_path"])
    devices = _device_nodes(root)
    assert len(devices) == 7  # 1 router + 1 switch + 5 PCs

    save_refs = []
    for device in devices:
        ref = device.findtext("ENGINE/SAVE_REF_ID") or device.findtext("ENGINE/SAVEREFID")
        assert ref, f"Missing save-ref on device {(device.findtext('ENGINE/NAME') or '').strip()}"
        save_refs.append(ref)

    assert len(save_refs) == len(set(save_refs)), f"Duplicated save refs found: {save_refs}"


def test_topology_port_assignment_uses_distinct_switch_ports_for_each_pc(tmp_path):
    """Each PC connected to the same switch must receive a distinct access port."""
    subnets = [
        MockSubnet(
            "LAN",
            "255.255.255.0",
            ["10.0.0.2", "10.0.0.200"],
            gateway="10.0.0.1",
        )
    ]
    config = {"devices": {"routers": 1, "switches": 1, "pcs": 3, "servers": 0}}

    result = save_pkt_file(subnets, config, str(tmp_path))
    assert result["success"] is True

    switch_pc_links = _switch_to_pc_links(result["links"])
    assert len(switch_pc_links) == 3

    switch_ports = [link["from_port"] for link in switch_pc_links]
    assert switch_ports == ["FastEthernet0/2", "FastEthernet0/3", "FastEthernet0/4"]
    assert len(switch_ports) == len(set(switch_ports))

    root = _load_root(result["xml_path"])
    link_ports = [
        [port.text or "" for port in cable.findall("PORT")]
        for cable in root.findall("NETWORK/LINKS/LINK/CABLE")
    ]
    pc_port_pairs = [ports for ports in link_ports if "FastEthernet0" in ports and any("/" in port for port in ports)]
    assert any(["FastEthernet0/2", "FastEthernet0"] == ports for ports in pc_port_pairs)
    assert any(["FastEthernet0/3", "FastEthernet0"] == ports for ports in pc_port_pairs)
    assert any(["FastEthernet0/4", "FastEthernet0"] == ports for ports in pc_port_pairs)
