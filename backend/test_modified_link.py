from pathlib import Path
import copy
import xml.etree.ElementTree as ET
from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator

# Genera file con 2 router (senza link)
gen = PKTGenerator()
devices_config = [
    {"name": "Router0", "type": "router-2port"},
    {"name": "Router1", "type": "router-2port"},
]
gen.generate(devices_config=devices_config, links_config=[], output_path="tmp_step1/test_with_routers.pkt")

# Carica il file generato
data = Path("tmp_step1/test_with_routers.pkt").read_bytes()
xml_str = decrypt_pkt_data(data).decode('utf-8')
root = ET.fromstring(xml_str)

# Trova i saveref di Router0 e Router1
device_saverefs = {}
for dev in root.findall('.//DEVICE'):
    name = dev.findtext('ENGINE/NAME')
    saveref = dev.findtext('ENGINE/SAVE_REF_ID')
    if name and saveref:
        device_saverefs[name] = saveref
        print(f'{name} -> {saveref}')

# Carica template link da simple_ref
template = Path('templates/simple_ref.pkt')
template_data = template.read_bytes()
template_xml = decrypt_pkt_data(template_data).decode('utf-8')
template_root = ET.fromstring(template_xml)
template_link = template_root.find('.//LINKS/LINK')

# Clona il link e modifica SOLO FROM e TO
link_copy = copy.deepcopy(template_link)
cable = link_copy.find('CABLE')
if cable:
    from_elem = cable.find('FROM')
    to_elem = cable.find('TO')
    if from_elem is not None:
        from_elem.text = device_saverefs['Router0']
    if to_elem is not None:
        to_elem.text = device_saverefs['Router1']
    print(f'Link modificato: FROM={from_elem.text}, TO={to_elem.text}')

# Aggiungi il link
links = root.find('.//LINKS')
if links is not None:
    links.append(link_copy)
    print(f'Link aggiunto. Totale: {len(links.findall("LINK"))}')

# Salva
xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='utf-8')
encrypted = encrypt_pkt_data(xml_bytes)
output = Path('tmp_step1/test_modified_link.pkt')
output.write_bytes(encrypted)
print(f'Salvato: {output}')
