from pathlib import Path
import xml.etree.ElementTree as ET
from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator
from tests.validate_pkt import validate

xml = decrypt_pkt_data(Path('kotest_final.pkt').read_bytes()).decode('utf-8')
root = ET.fromstring(xml)
name_by_saveref = {}
config = []
for dev in root.findall('./NETWORK/DEVICES/DEVICE'):
    name = dev.findtext('ENGINE/NAME')
    saveref = dev.findtext('ENGINE/SAVE_REF_ID') or dev.findtext('ENGINE/SAVEREFID')
    if saveref:
        name_by_saveref[saveref] = name
    dtype = dev.findtext('ENGINE/TYPE') or ''
    lt = dtype.lower()
    if 'switch' in lt:
        key = 'switch-24port'
    elif 'router' in lt:
        key = 'router-2port'
    elif 'server' in lt:
        key = 'pc'
    else:
        key = 'pc'
    config.append({'name': name, 'type': key})

links = []
for link in root.findall('./NETWORK/LINKS/LINK'):
    cab = link.find('CABLE')
    if cab is not None:
        frm = cab.findtext('FROM')
        to = cab.findtext('TO')
        ports = cab.findall('PORT')
    else:
        frm = link.findtext('FROM')
        to = link.findtext('TO')
        ports = link.findall('PORT')
    fp = ports[0].text if len(ports) > 0 else 'FastEthernet0/0'
    tp = ports[1].text if len(ports) > 1 else 'FastEthernet0/1'
    links.append({
        'from': name_by_saveref.get(frm, frm),
        'to': name_by_saveref.get(to, to),
        'from_port': fp,
        'to_port': tp,
    })

out = 'kotest_regen.pkt'
gen = PKTGenerator()
gen.generate(config, links_config=links, output_path=out)
validate(Path(out))
print('Generated', out)
