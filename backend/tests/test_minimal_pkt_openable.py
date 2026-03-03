"""
Minimal PKT generation test.

Generates a PKT with just 1 router (no links) and verifies:
  - The file decrypts to valid XML
  - XML has correct VERSION, NETWORK, DEVICES structure
  - PHYSICALWORKSPACE nodes are consistent with DEVICES
  - validate_pkt.py validator passes (structural integrity)
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / "templates" / "simple_ref.pkt"


@pytest.fixture
def generator():
    """Return a PKTGenerator pre-loaded with the template (skip if template absent)."""
    if not TEMPLATE.exists():
        pytest.skip(f"Template not found: {TEMPLATE}")
    from app.services.pkt_generator.generator import PKTGenerator
    return PKTGenerator(template_path=str(TEMPLATE))


def _decrypt(pkt_path: Path) -> bytes:
    from app.services.pkt_crypto import decrypt_pkt_data
    return decrypt_pkt_data(pkt_path.read_bytes())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_minimal_pkt_1_router(generator, tmp_path):
    """1 router, 0 links: file should decrypt to valid XML."""
    out = tmp_path / "min_router.pkt"
    generator.generate(
        devices_config=[{"name": "Router0", "type": "router-1port"}],
        links_config=[],
        output_path=str(out),
    )

    assert out.exists(), "PKT file was not created"
    xml_bytes = _decrypt(out)
    root = ET.fromstring(xml_bytes)

    assert root.findtext("VERSION"), "Missing <VERSION> tag"
    devices = root.findall("NETWORK/DEVICES/DEVICE")
    device_names = {d.findtext("ENGINE/NAME") for d in devices}
    assert "Router0" in device_names, f"Router0 not found in devices: {device_names}"


def test_minimal_pkt_unique_saverefs(generator, tmp_path):
    """Generated SAVE_REF_IDs must be unique across all devices."""
    out = tmp_path / "multi.pkt"
    generator.generate(
        devices_config=[
            {"name": "Router0", "type": "router-1port"},
            {"name": "Switch0", "type": "switch-24port"},
            {"name": "PC0", "type": "pc"},
        ],
        links_config=[],
        output_path=str(out),
    )

    xml_bytes = _decrypt(out)
    root = ET.fromstring(xml_bytes)
    devices = root.findall("NETWORK/DEVICES/DEVICE")
    saverefs = [d.findtext("ENGINE/SAVE_REF_ID") for d in devices]
    non_null = [s for s in saverefs if s]
    assert len(non_null) == len(set(non_null)), f"Duplicate SAVE_REF_IDs: {saverefs}"


def test_minimal_pkt_physicalworkspace_consistent(generator, tmp_path):
    """Every device must appear as a node in PHYSICALWORKSPACE."""
    out = tmp_path / "pw_check.pkt"
    generator.generate(
        devices_config=[
            {"name": "Router0", "type": "router-1port"},
            {"name": "Switch0", "type": "switch-24port"},
        ],
        links_config=[],
        output_path=str(out),
    )

    xml_bytes = _decrypt(out)
    root = ET.fromstring(xml_bytes)
    devices = root.findall("NETWORK/DEVICES/DEVICE")
    device_names = {d.findtext("ENGINE/NAME") for d in devices}

    pw_names = {
        n.findtext("NAME")
        for n in root.findall(".//PHYSICALWORKSPACE//NODE")
        if n.findtext("NAME")
    }

    missing = device_names - pw_names
    assert not missing, f"Devices missing from PHYSICALWORKSPACE: {missing}"


def test_minimal_pkt_no_saverefid_corruption(generator, tmp_path):
    """SAVE_REF_ID values must start with 'save-ref-id:' (not be corrupted numerics)."""
    out = tmp_path / "saveref.pkt"
    generator.generate(
        devices_config=[{"name": "Router0", "type": "router-1port"}],
        links_config=[],
        output_path=str(out),
    )

    xml_bytes = _decrypt(out)
    root = ET.fromstring(xml_bytes)
    for dev in root.findall("NETWORK/DEVICES/DEVICE"):
        ref = dev.findtext("ENGINE/SAVE_REF_ID")
        if ref:
            assert ref.startswith("save-ref-id:"), (
                f"SAVE_REF_ID corrupted for {dev.findtext('ENGINE/NAME')!r}: {ref!r}"
            )


def test_validate_pkt_script_passes(generator, tmp_path):
    """The full validate_pkt.py structural checker must pass."""
    out = tmp_path / "validated.pkt"
    generator.generate(
        devices_config=[
            {"name": "Router0", "type": "router-1port"},
            {"name": "Switch0", "type": "switch-24port"},
            {"name": "PC0", "type": "pc"},
        ],
        links_config=[
            {
                "from": "Router0", "from_port": "FastEthernet0/0",
                "to": "Switch0", "to_port": "FastEthernet0/1",
            },
            {
                "from": "Switch0", "from_port": "FastEthernet0/2",
                "to": "PC0", "to_port": "FastEthernet0",
            },
        ],
        output_path=str(out),
    )

    # Import validate_pkt from the tests directory
    import importlib.util, sys as _sys
    spec = importlib.util.spec_from_file_location(
        "validate_pkt",
        Path(__file__).parent / "validate_pkt.py",
    )
    vmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vmod)

    # validate() raises AssertionError on failure
    vmod.validate(out)
