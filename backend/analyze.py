import sys
import os

from app.services.pkt_crypto import decrypt_pkt_data

def analyze(filename):
    print(f"=== Analyzing {filename} ===")
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return
    
    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"Total size: {len(data)} bytes")
    print("First 256 bytes hex dump:")
    
    # Dump first 256 bytes
    # Instead of hexdump module which might not be installed, let's write a simple one
    for i in range(0, min(256, len(data)), 16):
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{i:04x}  {hex_str:<48}  |{ascii_str}|")
    
    try:
        xml = decrypt_pkt_data(data)
        print(f"Decryption successful. XML size: {len(xml)} bytes")
        print("First 100 bytes of XML:")
        print(xml[:100].decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"Decryption failed: {e}")
    print()

if __name__ == '__main__':
    analyze('manual_1r2s4p.pkt')
    analyze('testko.pkt')
