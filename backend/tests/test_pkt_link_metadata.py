from __future__ import annotations

import collections
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator
from app.services.pkt_generator.topology import build_links_config


def _generate_r1_s1_p3(pkt_path: Path) -> ET.Element:
    devices_config = [
        {"name": "Router0", "type": "router-2port"},
        {"name": "Switch0", "type": "switch-24port"},
        {"name": "PC0", "type": "pc"},
        {"name": "PC1", "type": "pc"},
        {"name": "PC2", "type": "pc"},
    ]
    links_config = build_links_config(1, 1, 3)
    PKTGenerator().generate(devices_config=devices_config, links_config=links_config, output_path=str(pkt_path))
    xml = decrypt_pkt_data(pkt_path.read_bytes()).decode("utf-8", errors="strict")
    return ET.fromstring(xml)


def _generate_r1_s2_p3(pkt_path: Path) -> ET.Element:
    devices_config = [
        {"name": "Router0", "type": "router-2port"},
        {"name": "Switch0", "type": "switch-24port"},
        {"name": "Switch1", "type": "switch-24port"},
        {"name": "PC0", "type": "pc"},
        {"name": "PC1", "type": "pc"},
        {"name": "PC2", "type": "pc"},
    ]
    links_config = build_links_config(1, 2, 3)
    PKTGenerator().generate(devices_config=devices_config, links_config=links_config, output_path=str(pkt_path))
    xml = decrypt_pkt_data(pkt_path.read_bytes()).decode("utf-8", errors="strict")
    return ET.fromstring(xml)


def test_r1_s1_p3_link_mem_addrs_not_constant(tmp_path) -> None:
    root = _generate_r1_s1_p3(tmp_path / "r1_s1_p3.pkt")

    saveref_to_name: dict[str, str] = {}
    dev_addr_by_name: dict[str, str] = {}
    for dev in root.findall("NETWORK/DEVICES/DEVICE"):
        name = dev.findtext("ENGINE/NAME") or ""
        saveref = dev.findtext("ENGINE/SAVE_REF_ID") or dev.findtext("ENGINE/SAVEREFID") or ""
        dev_addr = dev.findtext("WORKSPACE/LOGICAL/DEV_ADDR") or ""
        if saveref:
            saveref_to_name[saveref] = name
        if dev_addr:
            dev_addr_by_name[name] = dev_addr

    from_port_vals: list[str] = []
    to_port_vals: list[str] = []
    for link in root.findall("NETWORK/LINKS/LINK"):
        cable = link.find("CABLE")
        assert cable is not None
        from_ref = cable.findtext("FROM") or ""
        to_ref = cable.findtext("TO") or ""
        from_name = saveref_to_name[from_ref]
        to_name = saveref_to_name[to_ref]

        # Device mem addrs in links should match device DEV_ADDR.
        assert cable.findtext("FROM_DEVICE_MEM_ADDR") == dev_addr_by_name.get(from_name)
        assert cable.findtext("TO_DEVICE_MEM_ADDR") == dev_addr_by_name.get(to_name)

        from_port_vals.append(cable.findtext("FROM_PORT_MEM_ADDR") or "")
        to_port_vals.append(cable.findtext("TO_PORT_MEM_ADDR") or "")

    # Prevent the previous "all links share the same mem addr" pattern.
    assert len(set(from_port_vals + to_port_vals)) > 2


def test_r1_s1_p3_matches_pt_reference_major_structure(tmp_path) -> None:
    reference_pkt = Path("backend/tests/fixtures/pt_reference_r1_s1_p3.pkt")
    if not reference_pkt.exists():
        pytest.skip("Missing PT reference fixture: backend/tests/fixtures/pt_reference_r1_s1_p3.pkt")

    generated = _generate_r1_s1_p3(tmp_path / "r1_s1_p3.pkt")
    reference = ET.fromstring(decrypt_pkt_data(reference_pkt.read_bytes()).decode("utf-8", errors="strict"))

    assert generated.findtext("VERSION/MAJOR") == reference.findtext("VERSION/MAJOR")
    assert generated.findtext("VERSION/MINOR") == reference.findtext("VERSION/MINOR")

    gen_types = collections.Counter(
        (dev.findtext("ENGINE/TYPE") or "").strip().lower()
        for dev in generated.findall("NETWORK/DEVICES/DEVICE")
    )
    ref_types = collections.Counter(
        (dev.findtext("ENGINE/TYPE") or "").strip().lower()
        for dev in reference.findall("NETWORK/DEVICES/DEVICE")
    )
    assert gen_types == ref_types

    assert [child.tag for child in list(generated)] == [child.tag for child in list(reference)]


def test_r1_s2_p3_switch_links_and_reference_similarity(tmp_path) -> None:
    generated = _generate_r1_s2_p3(tmp_path / "r1_s2_p3.pkt")

    saveref_to_name: dict[str, str] = {}
    switch_refs: set[str] = set()
    endpoint_names = {"Switch0", "Switch1", "PC0", "PC1", "PC2"}
    linked_endpoints: collections.Counter[str] = collections.Counter()
    for dev in generated.findall("NETWORK/DEVICES/DEVICE"):
        name = dev.findtext("ENGINE/NAME") or ""
        saveref = dev.findtext("ENGINE/SAVE_REF_ID") or dev.findtext("ENGINE/SAVEREFID") or ""
        if saveref:
            saveref_to_name[saveref] = name
            if name.startswith("Switch"):
                switch_refs.add(saveref)

    used_switch_refs: set[str] = set()
    for link in generated.findall("NETWORK/LINKS/LINK"):
        cable = link.find("CABLE")
        assert cable is not None
        from_ref = cable.findtext("FROM") or ""
        to_ref = cable.findtext("TO") or ""
        from_name = saveref_to_name.get(from_ref, "")
        to_name = saveref_to_name.get(to_ref, "")
        if from_name.startswith("Switch"):
            used_switch_refs.add(from_ref)
        if to_name.startswith("Switch"):
            used_switch_refs.add(to_ref)
        if from_name in endpoint_names:
            linked_endpoints[from_name] += 1
        if to_name in endpoint_names:
            linked_endpoints[to_name] += 1

    for endpoint in endpoint_names:
        assert linked_endpoints[endpoint] >= 1, f"{endpoint} has no links"
    assert used_switch_refs == switch_refs

    reference_pkt = Path("backend/tests/fixtures/pt_reference_r1_s2_p3.pkt")
    if not reference_pkt.exists():
        pytest.skip("Missing PT reference fixture: backend/tests/fixtures/pt_reference_r1_s2_p3.pkt")

    reference = ET.fromstring(decrypt_pkt_data(reference_pkt.read_bytes()).decode("utf-8", errors="strict"))
    gen_types = collections.Counter(
        (dev.findtext("ENGINE/TYPE") or "").strip().lower()
        for dev in generated.findall("NETWORK/DEVICES/DEVICE")
    )
    ref_types = collections.Counter(
        (dev.findtext("ENGINE/TYPE") or "").strip().lower()
        for dev in reference.findall("NETWORK/DEVICES/DEVICE")
    )
    assert gen_types == ref_types

    # Similarity check: uplinks to switches should include FE0/0 and FE1/0 on Router0.
    uplink_ports = []
    for link in generated.findall("NETWORK/LINKS/LINK"):
        cable = link.find("CABLE")
        if cable is None:
            continue
        from_name = saveref_to_name.get(cable.findtext("FROM") or "", "")
        to_name = saveref_to_name.get(cable.findtext("TO") or "", "")
        ports = [p.text or "" for p in cable.findall("PORT")]
        if from_name == "Router0" and to_name.startswith("Switch") and ports:
            uplink_ports.append(ports[0])
    assert "FastEthernet0/0" in uplink_ports
    assert "FastEthernet1/0" in uplink_ports
