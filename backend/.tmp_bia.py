from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter
xml=decrypt_pkt_data(Path('kotest_final.pkt').read_bytes()).decode('utf-8')
root=ET.fromstring(xml)
bias=[el.text for el in root.findall('.//BIA') if el.text]
print('BIA count', len(bias))
dup=[m for m,c in Counter(bias).items() if c>1]
print('BIA dup', len(dup), dup[:5])
