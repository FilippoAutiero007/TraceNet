f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
content = f.read()
f.close()

old = '            if not d.get("dhcp_pools"):\n                d["dhcp_pools"] = all_pools'
new = '''            user_pools = d.get("dhcp_pools") or []
            if user_pools:
                # Merge: usa nomi utente ma dati di rete da all_pools
                merged = []
                for i, auto_pool in enumerate(all_pools):
                    user_name = user_pools[i]["name"] if i < len(user_pools) and user_pools[i].get("name") else auto_pool["name"]
                    merged.append({**auto_pool, "name": user_name})
                d["dhcp_pools"] = merged
            else:
                d["dhcp_pools"] = all_pools'''

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE')
