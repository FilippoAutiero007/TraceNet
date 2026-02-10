import sys
sys.path.insert(0, '.')

# Import da pkt_crypto (NON pkt_encryption!)
from app.services.pkt_crypto import decrypt_pkt_data

# Read encrypted PKT file
with open('simple_ref.pkt', 'rb') as f:
    encrypted_data = f.read()

# Decrypt
try:
    xml_bytes = decrypt_pkt_data(encrypted_data)
    xml = xml_bytes.decode('utf-8')
    
    # Save decrypted XML
    with open('simple_ref_decrypted.xml', 'w', encoding='utf-8') as f:
        f.write(xml)
    
    print('✅ Decrypted successfully to simple_ref_decrypted.xml')
    print(f'📊 XML size: {len(xml)} chars')
    print('\n📋 First 500 chars:')
    print(xml[:500])
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
