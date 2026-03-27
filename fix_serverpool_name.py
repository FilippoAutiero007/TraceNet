f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
content = f.read()
f.close()

old = '''            all_pools = []
            # Pool per ogni LAN: prima quella del server, poi le altre
            for seg in lan_segments:
                seg_net = seg.get("network", "")
                seg_net_base = seg_net.split("/")[0] if "/" in seg_net else seg_net
                if not seg_net:
                    continue
                pool_name = f"rete{seg_net_base}"
                pool_gw = seg.get("gateway", gw)
                pool_mask = seg.get("mask", mask)
                all_pools.append({
                    "name": pool_name,
                    "network": seg_net_base,
                    "mask": pool_mask,
                    "gateway": pool_gw,
                    "dns": server_ip,
                })
            # Fallback: se lan_segments vuoto usa la rete del server stesso
            if not all_pools:
                all_pools.append({
                    "name": f"rete{network_addr}",
                    "network": network_addr,
                    "mask": mask,
                    "gateway": gw,
                    "dns": server_ip,
                })'''

new = '''            all_pools = []
            # Pool per ogni LAN:
            # - la LAN locale del server si chiama "serverPool" (richiesto da PT)
            # - le LAN remote si chiamano rete<network>
            for seg in lan_segments:
                seg_net = seg.get("network", "")
                seg_net_base = seg_net.split("/")[0] if "/" in seg_net else seg_net
                if not seg_net:
                    continue
                pool_gw = seg.get("gateway", gw)
                pool_mask = seg.get("mask", mask)
                # La LAN del server stesso usa serverPool
                if seg_net_base == network_addr:
                    pool_name = "serverPool"
                else:
                    pool_name = f"rete{seg_net_base}"
                all_pools.append({
                    "name": pool_name,
                    "network": seg_net_base,
                    "mask": pool_mask,
                    "gateway": pool_gw,
                    "dns": server_ip,
                })
            # Fallback: se lan_segments vuoto usa la rete del server stesso
            if not all_pools:
                all_pools.append({
                    "name": "serverPool",
                    "network": network_addr,
                    "mask": mask,
                    "gateway": gw,
                    "dns": server_ip,
                })'''

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE - blocco non trovato')
