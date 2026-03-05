from __future__ import annotations

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator


def _decrypt_root(pkt_path) -> ET.Element:
    xml = decrypt_pkt_data(pkt_path.read_bytes()).decode("utf-8", errors="strict")
    return ET.fromstring(xml)


def _assert_pw_integrity(root: ET.Element) -> None:
    devices = root.findall("NETWORK/DEVICES/DEVICE")
    pw = root.find("PHYSICALWORKSPACE")
    assert pw is not None

    uuid_to_node: dict[str, ET.Element] = {}
    for node in pw.iter("NODE"):
        node_uuid = (node.findtext("UUID_STR") or "").strip("{} ")
        if node_uuid:
            assert node_uuid not in uuid_to_node
            uuid_to_node[node_uuid] = node

    missing_devices = 0
    device_leaf_uuids: list[str] = []
    for dev in devices:
        name = dev.findtext("ENGINE/NAME") or ""
        phys = (dev.findtext("WORKSPACE/PHYSICAL") or "").strip()
        assert phys, f"missing WORKSPACE/PHYSICAL for {name}"
        path_parts = [part.strip("{} ") for part in phys.split(",") if part.strip()]
        missing_parts = [part for part in path_parts if part not in uuid_to_node]
        if missing_parts:
            missing_devices += 1
        assert not missing_parts, f"{name} has missing UUIDs in physical path: {missing_parts}"

        leaf_uuid = path_parts[-1]
        device_leaf_uuids.append(leaf_uuid)
        leaf_node = uuid_to_node[leaf_uuid]
        assert (leaf_node.findtext("TYPE") or "").strip() == "6"
        assert (leaf_node.findtext("NAME") or "").strip() == name

    assert missing_devices == 0
    assert len(device_leaf_uuids) == len(set(device_leaf_uuids))


def test_api_like_router8_2switch_4pc_pw_integrity(tmp_path) -> None:
    out = tmp_path / "api_like_router8_2sw_4pc.pkt"
    generator = PKTGenerator()
    devices_config = [
        {"name": "Router0", "type": "router-8port"},
        {"name": "Switch0", "type": "switch-24port"},
        {"name": "Switch1", "type": "switch-24port"},
        {"name": "PC0", "type": "pc"},
        {"name": "PC1", "type": "pc"},
        {"name": "PC2", "type": "pc"},
        {"name": "PC3", "type": "pc"},
    ]
    generator.generate(devices_config, links_config=[], output_path=str(out))
    _assert_pw_integrity(_decrypt_root(out))


def test_api_like_multi_router_switch_pc_pw_integrity(tmp_path) -> None:
    out = tmp_path / "api_like_multi_router_switch_pc.pkt"
    generator = PKTGenerator()
    devices_config = [
        {"name": "Router0", "type": "router-8port"},
        {"name": "Router1", "type": "router-2port"},
        {"name": "Switch0", "type": "switch-24port"},
        {"name": "Switch1", "type": "switch-24port"},
        {"name": "PC0", "type": "pc"},
        {"name": "PC1", "type": "pc"},
        {"name": "PC2", "type": "pc"},
        {"name": "PC3", "type": "pc"},
    ]
    generator.generate(devices_config, links_config=[], output_path=str(out))
    _assert_pw_integrity(_decrypt_root(out))
