from app.services.pkt_crypto import decrypt_pkt_data
import xml.etree.ElementTree as ET
from pathlib import Path

def list_types(fname):
    xml=decrypt_pkt_data(Path(fname).read_bytes()).decode('utf-8')
    root=ET.fromstring(xml)
    print('\n', fname)
    for dev in root.findall('./NETWORK/DEVICES/DEVICE'):
        print(' ', dev.findtext('ENGINE/NAME'), dev.findtext('ENGINE/TYPE'))
list_types('manual_1r2s3p_test.pkt')
list_types('kotest_final.pkt')
