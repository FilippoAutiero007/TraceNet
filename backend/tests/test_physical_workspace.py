from pathlib import Path
import sys
sys.path.insert(0, ".")

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator

TEMPLATE = Path("app/services/pkt_generator/templates/simple_ref.pkt")

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

    # PHYSICALWORKSPACE identico
    assert gen_pw == tpl_pw

    # nessun WORKSPACE/PHYSICAL o PHYSICAL_CPUR nei device generati
    assert "<PHYSICAL_CPUR>" not in gen_xml
    assert "<WORKSPACE>" in gen_xml
    assert "<PHYSICAL>" not in gen_xml
