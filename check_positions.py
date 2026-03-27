import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path
import xml.etree.ElementTree as ET

xml = decrypt_pkt_data(Path(r'C:\Users\pippo\OneDrive\Desktop\test_default_pools.pkt').read_bytes()).decode('utf-8')
root = ET.fromstring(xml)

for dev in root.iter('DEVICE'):
    ws = dev.find('WORKSPACE')
    if ws is None:
        continue
    name = ws.findtext('NAME') or '?'
    x = ws.findtext('X') or '?'
    y = ws.findtext('Y') or '?'
    # Cerca tipo nel ENGINE
    eng = dev.find('ENGINE')
    dtype = eng.findtext('DEVICE_TYPE') if eng is not None else '?'
    print(name + ' | type=' + str(dtype) + ' | x=' + x + ' | y=' + y)
