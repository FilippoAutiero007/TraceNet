import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path
xml = decrypt_pkt_data(Path(r'C:\Users\pippo\OneDrive\Desktop\test_finale.pkt').read_bytes()).decode('utf-8')
idx = xml.find('serverPool')
while idx != -1:
    print('Trovato a pos', idx, ':', xml[max(0,idx-100):idx+100])
    print('---')
    idx = xml.find('serverPool', idx+1)
