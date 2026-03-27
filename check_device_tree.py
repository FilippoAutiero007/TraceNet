import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path
import xml.etree.ElementTree as ET

xml = decrypt_pkt_data(Path(r'C:\Users\pippo\OneDrive\Desktop\test_default_pools.pkt').read_bytes()).decode('utf-8')
root = ET.fromstring(xml)

# Stampa struttura completa primo DEVICE fino a depth 4
def print_tree(el, depth=0, max_depth=4):
    val = (el.text or '').strip()[:30]
    print('  ' * depth + '<' + el.tag + '>' + (' = ' + val if val else ''))
    if depth < max_depth:
        for child in el:
            print_tree(child, depth+1, max_depth)

for i, dev in enumerate(root.iter('DEVICE')):
    print('=== DEVICE', i, '===')
    print_tree(dev)
    if i >= 1:
        break
