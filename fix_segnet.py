f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
content = f.read()
f.close()

old = '                seg_net = seg.get("network", "")\n                if not seg_net or seg_net == network_addr:\n                    continue'
new = '                seg_net = seg.get("network", "")\n                seg_net_base = seg_net.split("/")[0] if "/" in seg_net else seg_net\n                if not seg_net or seg_net_base == network_addr:\n                    continue'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE - riga non trovata')
