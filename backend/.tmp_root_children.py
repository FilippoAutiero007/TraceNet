from app.services.pkt_crypto import decrypt_pkt_data
import xml.etree.ElementTree as ET
from pathlib import Path

def show_keys(fname):
    xml=decrypt_pkt_data(Path(fname).read_bytes()).decode('utf-8')
    root=ET.fromstring(xml)
    keys=[child.tag for child in root]
    print('\n', fname)
    print(keys[:15])
show_keys('manual_1r2s3p_test.pkt')
show_keys('kotest_final.pkt')
