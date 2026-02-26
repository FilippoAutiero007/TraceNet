from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data
import xml.etree.ElementTree as ET
from collections import Counter

xml = decrypt_pkt_data(Path('kotest_final.pkt').read_bytes()).decode('utf-8')
root = ET.fromstring(xml)
print('VERSION', root.findtext('VERSION'))
print('devices', len(root.findall('./NETWORK/DEVICES/DEVICE')))
print('links', len(root.findall('./NETWORK/LINKS/LINK')))
macs=[el.text for el in root.findall('.//MACADDRESS') if el.text]
dup=[m for m,c in Counter(macs).items() if c>1]
print('mac dup', len(dup))
pw=root.find('PHYSICALWORKSPACE')
print('pw nodes', len(list(pw.iter('NODE'))) if pw is not None else 0)
uuid_in_nodes={ (n.findtext('UUID_STR') or '').strip('{}') for n in pw.iter('NODE') if n.find('UUID_STR') is not None }
for dev in root.findall('./NETWORK/DEVICES/DEVICE'):
    name=dev.findtext('ENGINE/NAME')
    phys=dev.findtext('WORKSPACE/PHYSICAL') or ''
    guids=[p.strip('{}') for p in phys.split(',') if p]
    missing=[g for g in guids if g not in uuid_in_nodes]
    if missing:
        print('phys missing', name, missing[:3])
saverefs={d.findtext('ENGINE/SAVE_REF_ID') for d in root.findall('./NETWORK/DEVICES/DEVICE')}
bad=[]
for link in root.findall('./NETWORK/LINKS/LINK'):
    cab=link.find('CABLE')
    frm=cab.findtext('FROM') if cab is not None else link.findtext('FROM')
    to=cab.findtext('TO') if cab is not None else link.findtext('TO')
    if frm not in saverefs or to not in saverefs:
        bad.append((frm,to))
if bad:
    print('bad links', bad[:3])
