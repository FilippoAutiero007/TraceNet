f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
lines = f.readlines()
f.close()

start = None
end = None
for i, l in enumerate(lines):
    if 'd["dhcp_pools"] = [' in l:
        start = i
    if start is not None and i > start and l.strip() == ']':
        end = i
        break

print(f'start={start}, end={end}')
if start is not None and end is not None:
    new_lines = [
        '            # Crea un pool per ogni LAN presente (propria + quelle servite via helper-address)\n',
        '            all_pools = []\n',
        '            # Pool per la LAN del server stesso\n',
        '            all_pools.append({\n',
        '                "name": f"{d.get(\"name\", \"server\")}_pool",\n',
        '                "network": network_addr,\n',
        '                "mask": mask,\n',
        '                "gateway": gw,\n',
        '                "dns": server_ip,\n',
        '            })\n',
        '            # Pool aggiuntivi per le altre LAN (quelle con router che avranno ip helper-address)\n',
        '            for seg in lan_segments:\n',
        '                seg_net = seg.get("network", "")\n',
        '                if not seg_net or seg_net == network_addr:\n',
        '                    continue\n',
        '                all_pools.append({\n',
        '                    "name": f"{d.get(\"name\", \"server\")}_{seg_net.replace(\".\", \"_\")}_pool",\n',
        '                    "network": seg_net.split("/")[0] if "/" in seg_net else seg_net,\n',
        '                    "mask": seg["mask"],\n',
        '                    "gateway": seg["gateway"],\n',
        '                    "dns": server_ip,\n',
        '                })\n',
        '            d["dhcp_pools"] = all_pools\n',
    ]
    lines[start:end+1] = new_lines
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').writelines(lines)
    print('OK - fix applicata')
else:
    print('ERRORE - blocco non trovato')
