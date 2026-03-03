from pathlib import Path
import copy
import xml.etree.ElementTree as ET
from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data

# Carica template
template = Path('templates/simple_ref.pkt')
data = template.read_bytes()
xml_str = decrypt_pkt_data(data).decode('utf-8')
root = ET.fromstring(xml_str)

# Trova il link originale
template_link = root.find('.//LINKS/LINK')
if template_link is None:
    print('ERRORE: Nessun link nel template!')
    exit(1)

# Clone del template completo
root_copy = copy.deepcopy(root)

# Trova LINKS nella copia
links = root_copy.find('.//LINKS')
if links:
    # Duplica il link originale (avremo 2 link identici)
    link_clone = copy.deepcopy(template_link)
    links.append(link_clone)
    print(f'Aggiunto link duplicato. Totale link: {len(links.findall("LINK"))}')

# Salva
xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root_copy, encoding='utf-8')
encrypted = encrypt_pkt_data(xml_bytes)

output = Path('tmp_step1/test_link_clone.pkt')
output.write_bytes(encrypted)
print(f'Salvato: {output}')
