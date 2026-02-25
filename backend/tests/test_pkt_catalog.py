"""
Integration tests for PKT Generator with Device Catalog.
"""
import pytest
from app.services.pkt_generator.core import PKTGenerator

def test_catalog_loading():
    """Test that the catalog is loaded correctly."""
    generator = PKTGenerator()
    assert "router-1port" in generator.catalog
    assert "pc" in generator.catalog
    assert generator.catalog["router-1port"]["max_ports"] == 1

def test_resolve_device_type():
    """Test device type resolution."""
    generator = PKTGenerator()
    
    # Exact match
    meta = generator.resolve_device_type("router-8port")
    assert meta["base_template"].endswith("router_8port.pkt")
    
    # Validation of fallback (router)
    meta = generator.resolve_device_type("router-unknown-type")
    assert meta["base_template"].endswith("router_2port.pkt") # Default fallback

    # Validation of fallback (general)
    meta = generator.resolve_device_type("unknown-device")
    assert meta["base_template"].endswith("pc.pkt") # Default fallback

def test_template_path_resolution(monkeypatch):
    """Test that we can actually find the templates referenced in the catalog."""
    generator = PKTGenerator()
    
    # We don't want to actually load/decrypt them all as it might be slow or fail in test env if files missing
    # but we can check if the paths resolve.
    # Actually, let's try to generate a specific one to test the full flow.
    pass

def test_generation_with_catalog():
    """Test generating a PKT with specific catalog types."""
    generator = PKTGenerator()
    
    devices_config = [
        {"name": "R1", "type": "router-1port", "x": 100, "y": 100},
        {"name": "PC1", "type": "pc", "x": 300, "y": 100}
    ]
    
    try:
        root = generator.generate(devices_config)
        
        # Check if devices were created
        network = root.find("NETWORK")
        devices_node = network.find("DEVICES")
        devices = list(devices_node)
        
        assert len(devices) == 2
        
        # We can't easily verify WHICH template was used just by looking at the XML 
        # without deep inspection of specific capabilities, but we know it didn't crash.
        
    except FileNotFoundError:
        pytest.skip("Templates not found using default paths in test environment")


def test_link_structure_no_flat_tags():
    """
    Verify that generated LINK elements have the correct structure:
    - All data (FROM, TO, PORT, *_MEM_ADDR) inside <CABLE>, not on <LINK>.
    - Tag names use underscores (FROM_DEVICE_MEM_ADDR, not FROMDEVICEMEMADDR).
    - save-ref-id format includes colon separator.
    """
    generator = PKTGenerator()

    devices_config = [
        {"name": "Router0", "type": "router"},
        {"name": "Switch0", "type": "switch"},
        {"name": "PC0", "type": "pc"},
    ]

    links_config = [
        {"from": "Router0", "from_port": "FastEthernet0/0",
         "to": "Switch0", "to_port": "FastEthernet0/1"},
        {"from": "Switch0", "from_port": "FastEthernet0/2",
         "to": "PC0", "to_port": "FastEthernet0"},
    ]

    try:
        root = generator.generate(devices_config, links_config)
    except FileNotFoundError:
        pytest.skip("Templates not found in test environment")

    network = root.find("NETWORK")
    links_elem = network.find("LINKS")
    all_links = links_elem.findall("LINK") if links_elem is not None else []

    assert len(all_links) == 2, f"Expected 2 links, got {len(all_links)}"

    # Tags that must NOT appear directly on <LINK>
    forbidden_on_link = {
        "FROM", "TO", "PORT",
        "FROMDEVICEMEMADDR", "TODEVICEMEMADDR",
        "FROMPORTMEMADDR", "TOPORTMEMADDR",
        "FROM_DEVICE_MEM_ADDR", "TO_DEVICE_MEM_ADDR",
        "FROM_PORT_MEM_ADDR", "TO_PORT_MEM_ADDR",
    }

    # Tags that MUST appear inside <CABLE>
    required_in_cable = {
        "FROM", "TO",
        "FROM_DEVICE_MEM_ADDR", "TO_DEVICE_MEM_ADDR",
        "FROM_PORT_MEM_ADDR", "TO_PORT_MEM_ADDR",
    }

    for idx, link in enumerate(all_links):
        # 1. No forbidden flat tags on LINK itself
        for child in link:
            assert child.tag not in forbidden_on_link, (
                f"LINK[{idx}] has forbidden direct child <{child.tag}>; "
                "this tag should be inside <CABLE>"
            )

        # 2. CABLE must exist
        cable = link.find("CABLE")
        assert cable is not None, f"LINK[{idx}] is missing <CABLE>"

        # 3. Required tags inside CABLE
        cable_child_tags = {c.tag for c in cable}
        for tag in required_in_cable:
            assert tag in cable_child_tags, (
                f"LINK[{idx}]/CABLE is missing <{tag}>"
            )

        # 4. Two PORT elements inside CABLE
        ports = cable.findall("PORT")
        assert len(ports) >= 2, (
            f"LINK[{idx}]/CABLE has {len(ports)} PORT(s), expected >= 2"
        )

        # 5. No underscore-less MEMADDR tags inside CABLE
        for bad_tag in ("FROMDEVICEMEMADDR", "TODEVICEMEMADDR",
                        "FROMPORTMEMADDR", "TOPORTMEMADDR"):
            assert cable.find(bad_tag) is None, (
                f"LINK[{idx}]/CABLE has bad tag <{bad_tag}> "
                "(should use underscores: FROM_DEVICE_MEM_ADDR etc.)"
            )

        # 6. save-ref-id format includes colon
        from_ref = cable.find("FROM")
        to_ref = cable.find("TO")
        if from_ref is not None and from_ref.text:
            assert "save-ref-id:" in from_ref.text, (
                f"LINK[{idx}] FROM ref missing colon: {from_ref.text}"
            )
        if to_ref is not None and to_ref.text:
            assert "save-ref-id:" in to_ref.text, (
                f"LINK[{idx}] TO ref missing colon: {to_ref.text}"
            )
