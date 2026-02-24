import os
import xml.etree.ElementTree as ET

import pytest

from app.services.pkt_generator.core import PKTGenerator, resolve_template_path


def _generate_minimal_root():
    template = resolve_template_path()
    generator = PKTGenerator(str(template))
    devices_config = [
        {"name": "Router0", "type": "router"},
        {"name": "Switch0", "type": "switch"},
        {"name": "PC0", "type": "pc"},
    ]
    return generator.generate(devices_config, links_config=[])


def _structure_only(elem: ET.Element):
    """Return a tuple tree of tag names only (order preserved)."""
    return (elem.tag, [_structure_only(c) for c in list(elem)])


def test_physical_workspace_guid_alignment():
    """Each device PHYSICAL path should end with the UUID in PHYSICALWORKSPACE."""
    try:
        root = _generate_minimal_root()
    except FileNotFoundError:
        pytest.skip("Base template not found for physical workspace sync test")
        return

    pw = root.find("PHYSICALWORKSPACE")
    assert pw is not None, "Missing PHYSICALWORKSPACE in generated XML"

    pw_uuid_by_name = {}
    for node in pw.iter("NODE"):
        name = node.find("NAME")
        uuid = node.find("UUID_STR")
        if name is not None and uuid is not None and name.text:
            pw_uuid_by_name[name.text] = uuid.text.strip("{}")

    devices_node = root.find("NETWORK/DEVICES")
    assert devices_node is not None

    for dev in devices_node:
        name = dev.findtext("ENGINE/NAME")
        phys_text = dev.findtext("WORKSPACE/PHYSICAL", default="")
        last_guid = phys_text.split(",")[-1].strip("{} ") if phys_text else ""
        assert pw_uuid_by_name.get(name) == last_guid, f"{name} PHYSICAL GUID not in sync with workspace"


def test_physical_workspace_structure_matches_reference():
    """PHYSICALWORKSPACE structure (tags/ordering) stays aligned with simple_ref template."""
    try:
        root = _generate_minimal_root()
        ref_root = ET.parse(os.path.join("templates", "simple_ref.xml")).getroot()
    except FileNotFoundError:
        pytest.skip("Reference template not available")
        return

    gen_pw = root.find("PHYSICALWORKSPACE")
    ref_pw = ref_root.find("PHYSICALWORKSPACE")
    assert gen_pw is not None and ref_pw is not None

    assert _structure_only(gen_pw) == _structure_only(ref_pw)


def test_physical_workspace_multi_device():
    """GUID alignment holds when adding extra switches and PCs."""
    try:
        template = resolve_template_path()
    except FileNotFoundError:
        pytest.skip("Reference template not available")
        return

    gen = PKTGenerator(str(template))
    devices_config = [
        {"name": "Router0", "type": "router"},
        {"name": "Switch0", "type": "switch"},
        {"name": "Switch1", "type": "switch"},
        {"name": "PC0", "type": "pc"},
        {"name": "PC1", "type": "pc"},
        {"name": "PC2", "type": "pc"},
    ]
    root = gen.generate(devices_config, links_config=[])

    pw = root.find("PHYSICALWORKSPACE")
    assert pw is not None

    pw_uuid = {}
    for node in pw.iter("NODE"):
        name = node.find("NAME")
        uuid = node.find("UUID_STR")
        if name is not None and uuid is not None and name.text:
            pw_uuid[name.text] = uuid.text.strip("{}")

    devices_node = root.find("NETWORK/DEVICES")
    assert devices_node is not None

    for dev in devices_node:
        name = dev.findtext("ENGINE/NAME")
        phys_chain = dev.findtext("WORKSPACE/PHYSICAL", default="")
        last = phys_chain.split(",")[-1].strip("{} ") if phys_chain else ""
        assert name in pw_uuid, f"{name} missing in PHYSICALWORKSPACE"
        assert last == pw_uuid[name], f"{name} PHYSICAL GUID mismatch"
