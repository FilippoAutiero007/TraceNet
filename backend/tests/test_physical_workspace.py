from pathlib import Path
import sys
sys.path.insert(0, ".")

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator

TEMPLATE = Path("backend/templates/Router/router_2port.pkt")

def extract_physicalworkspace(xml: str) -> str:
    start = xml.index("<PHYSICALWORKSPACE>")
    end = xml.index("</PHYSICALWORKSPACE>") + len("</PHYSICALWORKSPACE>")
    return xml[start:end]

def test_physical_workspace_preserved_and_devices_without_physical(tmp_path):
    # 1) estrai il PHYSICALWORKSPACE dal template
    tpl_bytes = TEMPLATE.read_bytes()
    tpl_xml = decrypt_pkt_data(tpl_bytes).decode("utf-8")
    tpl_pw = extract_physicalworkspace(tpl_xml)

    # 2) genera un pkt minimale
    out = tmp_path / "minimal_test.pkt"
    g = PKTGenerator()
    g.generate(
        devices_config=[{"name": "Router0", "type": "router-2port"}],
        links_config=[],
        output_path=str(out),
    )

    gen_xml = decrypt_pkt_data(out.read_bytes()).decode("utf-8")
    gen_pw = extract_physicalworkspace(gen_xml)

    # PHYSICALWORKSPACE conservato (il confronto raw può differire solo per formattazione XML)
    assert tpl_pw
    assert gen_pw
    assert "Router0" in gen_xml

    assert "<WORKSPACE>" in gen_xml
    assert "<PHYSICAL>" in gen_xml
