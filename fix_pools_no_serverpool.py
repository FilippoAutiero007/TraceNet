f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
lines = f.readlines()
f.close()

# Trova riga 362 circa (all_pools = []) e sostituisce il blocco fino alla riga 383
start = None
end = None
for i, l in enumerate(lines):
    if 'all_pools = []' in l and 'Pool per la LAN del server stesso' in ''.join(lines[i:i+5]):
        start = i
    if start is not None and i > start and 'user_pools = d.get' in l:
        end = i
        break

print(f'start={start} end={end}')
if start is not None and end is not None:
    new_block = [
        '            all_pools = []\n',
        '            # Pool per ogni LAN: prima quella del server, poi le altre\n',
        '            for seg in lan_segments:\n',
        '                seg_net = seg.get("network", "")\n',
        '                seg_net_base = seg_net.split("/")[0] if "/" in seg_net else seg_net\n',
        '                if not seg_net:\n',
        '                    continue\n',
        '                pool_name = f"rete{seg_net_base}"\n',
        '                pool_gw = seg.get("gateway", gw)\n',
        '                pool_mask = seg.get("mask", mask)\n',
        '                all_pools.append({\n',
        '                    "name": pool_name,\n',
        '                    "network": seg_net_base,\n',
        '                    "mask": pool_mask,\n',
        '                    "gateway": pool_gw,\n',
        '                    "dns": server_ip,\n',
        '                })\n',
        '            # Fallback: se lan_segments vuoto usa la rete del server stesso\n',
        '            if not all_pools:\n',
        '                all_pools.append({\n',
        '                    "name": f"rete{network_addr}",\n',
        '                    "network": network_addr,\n',
        '                    "mask": mask,\n',
        '                    "gateway": gw,\n',
        '                    "dns": server_ip,\n',
        '                })\n',
    ]
    lines[start:end] = new_block
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').writelines(lines)
    print('OK')
else:
    print('ERRORE - blocco non trovato')
