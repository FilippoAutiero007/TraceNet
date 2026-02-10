"""
PKT Generator - Template-based approach using simple_ref.pkt
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
import re

# 1. Decrypt simple_ref.pkt
print("📂 Loading simple_ref.pkt template...")
template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'simple_ref.pkt')
with open(template_path, 'rb') as f:
    encrypted = f.read()

xml_template = decrypt_pkt_data(encrypted).decode('utf-8')
print(f"✅ Template loaded: {len(xml_template)} chars")

# 2. Modify XML (replace device names, IPs, etc)
print("\n🔧 Modifying template...")

# Replace Router0 coordinates (keep it as is for testing)
# Replace Switch0 coordinates
# Replace PC0 coordinates

# For now, just change the device names to test
xml_modified = xml_template.replace('Router0', 'MyRouter')
xml_modified = xml_modified.replace('Switch0', 'MySwitch')
xml_modified = xml_modified.replace('PC0', 'MyPC')

print("✅ Template modified")

# 3. Save modified XML
with open('test_template_modified.xml', 'w', encoding='utf-8') as f:
    f.write(xml_modified)
print("✅ Modified XML saved: test_template_modified.xml")

# 4. Encrypt
print("\n🔒 Encrypting...")
xml_bytes = xml_modified.encode('utf-8')
encrypted = encrypt_pkt_data(xml_bytes)

# 5. Save PKT
pkt_path = 'test_from_template.pkt'
with open(pkt_path, 'wb') as f:
    f.write(encrypted)

print(f"✅ PKT saved: {pkt_path}")
print(f"📊 Size: {len(encrypted)} bytes")

# 6. Open in PT
import subprocess
subprocess.Popen(['start', pkt_path], shell=True)
print("\n🚀 Opening in Packet Tracer...")
print("✅ If this opens successfully, the encryption is working!")
print("   Then we can build a proper XML generator based on this template")