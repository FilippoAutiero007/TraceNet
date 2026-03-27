import sys, re
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_crypto import decrypt_pkt_data
from pathlib import Path

for label, path in [('FILE1', r'\tmp\tracenet\network_20260326_195046_572519.pkt'), ('FILE2', r'\tmp\tracenet\network_20260326_195050_292612.pkt')]:
    xml = decrypt_pkt_data(Path(path).read_bytes()).decode('utf-8')
    pools = re.findall(r'<POOL>.*?</POOL>', xml, re.DOTALL)
    print(f'\n=== {label} - {len(pools)} pool ===')
    for p in pools:
        name = re.search(r'<NAME>(.*?)</NAME>', p)
        net  = re.search(r'<NETWORK>(.*?)</NETWORK>', p)
        gw   = re.search(r'<DEFAULT_ROUTER>(.*?)</DEFAULT_ROUTER>', p)
        print(f'  {name.group(1) if name else "?"} | NET: {net.group(1) if net else "?"} | GW: {gw.group(1) if gw else "?"}')
