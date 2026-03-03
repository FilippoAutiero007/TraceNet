from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data
import xml.etree.ElementTree as ET

# File test funzionante
test_working = Path("tmp_step1/test_full_link.pkt")
if test_working.exists():
    xml1 = decrypt_pkt_data(test_working.read_bytes()).decode('utf-8')
    root1 = ET.fromstring(xml1)
    link1 = root1.find('.//LINKS/LINK/CABLE')
    print("=== TEST FUNZIONANTE (test_full_link.pkt) ===")
    if link1 is not None:
        for child in link1:
            print(f"{child.tag}: {child.text}")
    else:
        print("NO LINK")

# File API
test_api = Path("test_final.pkt")
if test_api.exists():
    xml2 = decrypt_pkt_data(test_api.read_bytes()).decode('utf-8')
    root2 = ET.fromstring(xml2)
    link2 = root2.find('.//LINKS/LINK/CABLE')
    print("\n=== API (test_final.pkt) ===")
    if link2 is not None:
        for child in link2:
            print(f"{child.tag}: {child.text}")
    else:
        print("NO LINK")
else:
    print("\ntest_final.pkt NON ESISTE!")

# Conta i link totali
test_api2 = Path("test_final.pkt")
if test_api2.exists():
    xml3 = decrypt_pkt_data(test_api2.read_bytes()).decode('utf-8')
    root3 = ET.fromstring(xml3)
    links = root3.findall('.//LINKS/LINK')
    print(f"\nTotale LINK nel file API: {len(links)}")
