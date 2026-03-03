from pathlib import Path
import copy
import xml.etree.ElementTree as ET
from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from app.services.pkt_generator.utils import validate_name, rand_saveref, set_text

# Carica router_8port.pkt
template_path = Path("templates/Router/router_8port.pkt")
xml_str = decrypt_pkt_data(template_path.read_bytes()).decode("utf-8")
template_root = ET.fromstring(xml_str)

# Clone del device (esattamente come fa build_device)
template_devices = template_root.findall("NETWORK/DEVICES/DEVICE")
new_device = copy.deepcopy(template_devices[0])

# Cambia solo il nome
engine = new_device.find("ENGINE")
set_text(engine, "NAME", "TestRouter8", create=True)
set_text(engine, "SYSNAME", "TestRouter8", create=False)
saveref = rand_saveref()
set_text(engine, "SAVE_REF_ID", saveref, create=True)

# Carica simple_ref.pkt come base
base = Path("templates/simple_ref.pkt")
base_xml = decrypt_pkt_data(base.read_bytes()).decode("utf-8")
root = ET.fromstring(base_xml)

# Sostituisci i device
devices = root.find("NETWORK/DEVICES")
devices.clear()
devices.append(new_device)

# Rimuovi i link
links = root.find("NETWORK/LINKS")
links.clear()

# Salva
xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="utf-8")
encrypted = encrypt_pkt_data(xml_bytes)
output = Path("test_router8_manual.pkt")
output.write_bytes(encrypted)
print(f"Salvato: {output}")
