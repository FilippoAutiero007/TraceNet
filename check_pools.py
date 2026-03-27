import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path
import xml.etree.ElementTree as ET
xml = decrypt_pkt_data(Path(r'C:\Users\pippo\OneDrive\Desktop\test_finale.pkt').read_bytes()).decode('utf-8')
root = ET.fromstring(xml)
pools = root.findall('.//POOL')
print('Totale POOL nel file:', len(pools))
for i, pool in enumerate(pools):
    n = pool.findtext('NAME')
    net = pool.findtext('NETWORK')
    gw = pool.findtext('DEFAULT_ROUTER')
    start = pool.findtext('START_IP')
    print('Pool', i, ':', n, '| NET:', net, '| GW:', gw, '| START:', start)
