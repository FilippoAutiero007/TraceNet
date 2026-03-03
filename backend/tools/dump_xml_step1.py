from pathlib import Path
import sys
sys.path.insert(0,".")
from app.services.pkt_crypto import decrypt_pkt_data

pkt = Path(r"tmp_step1\minimal_step1.pkt").read_bytes()
xml = decrypt_pkt_data(pkt)

Path(r"tmp_step1\minimal_step1.xml").write_bytes(xml)
print("wrote tmp_step1/minimal_step1.xml", len(xml))
