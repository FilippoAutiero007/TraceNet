import os
import pytest
import xml.etree.ElementTree as ET
from app.services.pkt_generator.entrypoint import save_pkt_file
from app.services.pkt_crypto import decrypt_pkt_data


class MockSubnet:
    def __init__(self, usable_range, mask):
        self.usable_range = usable_range
        self.mask = mask
        self.name = "MockNet"


@pytest.fixture
def output_dir(tmp_path):
    d = tmp_path / "pkt_output_layout"
    d.mkdir()
    
    # Set template path env var for tests using the real template
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates", "simple_ref.pkt"))
    os.environ["PKT_TEMPLATE_PATH"] = template_path
    
    return str(d)


def extract_coords_from_xml(xml_path: str) -> dict[str, dict[str, int]]:
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    root = ET.fromstring(xml_content)
    devices = {}
    for device in root.findall(".//DEVICE"):
        name_node = device.find(".//ENGINE/NAME")
        if name_node is None or not name_node.text:
            continue
        name = name_node.text
        
        logical = device.find(".//WORKSPACE/LOGICAL")
        if logical is not None:
            x = int(logical.findtext("X", "0"))
            y = int(logical.findtext("Y", "0"))
            devices[name] = {"x": x, "y": y}
    return devices


def evaluate_levels(coords: dict[str, dict[str, int]]):
    routers = {k: v for k, v in coords.items() if "Router" in k}
    switches = {k: v for k, v in coords.items() if "Switch" in k}
    pcs = {k: v for k, v in coords.items() if "PC" in k}
    
    return routers, switches, pcs


def test_layout_1r_1s_3h(output_dir):
    subnets = [MockSubnet(["192.168.1.1", "192.168.1.100"], "255.255.255.0")]
    config = {
        "devices": {"routers": 1, "switches": 1, "pcs": 3}
    }
    
    try:
        result = save_pkt_file(subnets, config, output_dir)
    except FileNotFoundError:
        pytest.skip("Template not found")
        return

    coords = extract_coords_from_xml(result["xml_path"])
    routers, switches, pcs = evaluate_levels(coords)
    
    assert len(routers) == 1
    assert len(switches) == 1
    assert len(pcs) == 3
    
    # 1. Verify Y hierarchy
    r_y = list(routers.values())[0]["y"]
    s_y = list(switches.values())[0]["y"]
    pc_y_values = [p["y"] for p in pcs.values()]
    
    assert r_y < s_y, "Router must be above switch"
    assert s_y < min(pc_y_values), "Switch must be above PCs"
    
    # 2. Verify PCs are roughly centered under the switch
    s_x = list(switches.values())[0]["x"]
    pc_x_values = [p["x"] for p in pcs.values()]
    pc_center = sum(pc_x_values) / len(pc_x_values)
    
    assert abs(s_x - pc_center) < 10, "PCs should be horizontally centered under their switch"


def test_layout_1r_2s_3h(output_dir):
    subnets = [MockSubnet(["192.168.1.1", "192.168.1.100"], "255.255.255.0")]
    config = {
        "devices": {"routers": 1, "switches": 2, "pcs": 4} # Using 4 hosts for symmetry across 2 switches
    }
    
    try:
        result = save_pkt_file(subnets, config, output_dir)
    except FileNotFoundError:
        pytest.skip("Template not found")
        return

    coords = extract_coords_from_xml(result["xml_path"])
    routers, switches, pcs = evaluate_levels(coords)
    
    assert len(routers) == 1
    assert len(switches) == 2
    assert len(pcs) == 4
    
    # Verify Y hierarchy
    r_y = list(routers.values())[0]["y"]
    assert all(s["y"] > r_y for s in switches.values())
    assert all(p["y"] > max(s["y"] for s in switches.values()) for p in pcs.values())
    
    # Switches should have varying X coordinates, PCs should be distributed
    s_coords_x = sorted([s["x"] for s in switches.values()])
    assert s_coords_x[1] - s_coords_x[0] >= 200, "Switches should be horizontally spaced out"


def test_layout_2r_2s_3h(output_dir):
    subnets = [MockSubnet(["192.168.1.1", "192.168.1.100"], "255.255.255.0")]
    config = {
        "devices": {"routers": 2, "switches": 2, "pcs": 3}
    }
    
    try:
        result = save_pkt_file(subnets, config, output_dir)
    except FileNotFoundError:
        pytest.skip("Template not found")
        return

    coords = extract_coords_from_xml(result["xml_path"])
    routers, switches, pcs = evaluate_levels(coords)
    
    assert len(routers) == 2
    assert len(switches) == 2
    assert len(pcs) == 3
    
    # Verify strict Y levels
    router_y_max = max(r["y"] for r in routers.values())
    switch_y_min = min(s["y"] for s in switches.values())
    switch_y_max = max(s["y"] for s in switches.values())
    pc_y_min = min(p["y"] for p in pcs.values())
    
    assert router_y_max < switch_y_min
    assert switch_y_max < pc_y_min
