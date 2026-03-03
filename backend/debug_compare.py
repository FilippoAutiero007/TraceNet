from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
import xml.etree.ElementTree as ET

# 1. Apri router_8port originale
orig = Path("templates/Router/router_8port.pkt")
orig_xml = decrypt_pkt_data(orig.read_bytes()).decode("utf-8")
Path("debug_orig_router8.xml").write_text(orig_xml, encoding="utf-8")

# 2. Apri il file generato fallito
gen = Path("test_router8_fix.pkt")
if gen.exists():
    gen_xml = decrypt_pkt_data(gen.read_bytes()).decode("utf-8")
    Path("debug_gen_router8.xml").write_text(gen_xml, encoding="utf-8")

print("Salvati:")
print("  debug_orig_router8.xml (template originale)")
print("  debug_gen_router8.xml (file generato)")
print("\nConfronta i file per vedere cosa cambia!")
