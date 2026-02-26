from app.services.pkt_crypto import decrypt_pkt_data
import xml.etree.ElementTree as ET
from pathlib import Path

def show_link(fname, idx=0):
    xml=decrypt_pkt_data(Path(fname).read_bytes()).decode('utf-8')
    root=ET.fromstring(xml)
    links=root.findall('./NETWORK/LINKS/LINK')
    link=links[idx]
    print('\n', fname, 'link', idx)
    for child in link:
        print(' ', child.tag, child.text)
        for sub in child:
            print('    sub', sub.tag, sub.text)

show_link('manual_1r2s3p_test.pkt',0)
show_link('kotest_final.pkt',0)
