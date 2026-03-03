from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data
import xml.etree.ElementTree as ET

test_api = Path("test_final.pkt")
if test_api.exists():
    xml = decrypt_pkt_data(test_api.read_bytes()).decode("utf-8")
    root = ET.fromstring(xml)
    links = root.findall(".//LINKS/LINK")
    
    print(f"Totale LINK: {len(links)}\n")
    
    for idx, link in enumerate(links):
        cable = link.find("CABLE")
        if cable is None:
            print(f"LINK {idx}: NO CABLE!")
            continue
        
        print(f"=== LINK {idx} ===")
        for child in cable:
            text = (child.text or "")[:50]  # Primi 50 char
            print(f"  {child.tag}: {text}")
        print()
