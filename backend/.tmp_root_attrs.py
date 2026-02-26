from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data
import xml.etree.ElementTree as ET
for fname in ['manual_1r2s3p_test.pkt','manual_1r2s4p.pkt','kotest_final.pkt']:
    xml=decrypt_pkt_data(Path(fname).read_bytes()).decode('utf-8')
    root=ET.fromstring(xml)
    print('\n', fname)
    print('root attrs', root.attrib)
    print('VERSION node', root.findtext('VERSION'))
