import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path
import xml.etree.ElementTree as ET

for label, pkt_path in [('FILE1 default', r'\tmp\tracenet\network_20260326_191012_435218.pkt'), ('FILE2 reteArancione', r'\tmp\tracenet\network_20260326_191015_278986.pkt')]:
    xml = decrypt_pkt_data(Path(pkt_path).read_bytes()).decode('utf-8')
    root = ET.fromstring(xml)
    pools = root.findall('.//POOL')
    print(label)
    for p in pools:
        print(' ', p.findtext('NAME'), '| NET:', p.findtext('NETWORK'), '| GW:', p.findtext('DEFAULT_ROUTER'))
    print()
