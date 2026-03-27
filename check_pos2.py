import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path
import xml.etree.ElementTree as ET

xml = decrypt_pkt_data(Path(r'C:\Users\pippo\OneDrive\Desktop\test_default_pools.pkt').read_bytes()).decode('utf-8')
root = ET.fromstring(xml)

for dev in root.iter('DEVICE'):
    eng = dev.find('ENGINE')
    ws = dev.find('WORKSPACE')
    if eng is None or ws is None:
        continue
    name = eng.findtext('NAME') or '?'
    dtype = eng.findtext('TYPE') or '?'
    x = ws.findtext('LOGICAL/X') or '?'
    y = ws.findtext('LOGICAL/Y') or '?'
    print(name + ' | ' + dtype + ' | x=' + x + ' | y=' + y)
