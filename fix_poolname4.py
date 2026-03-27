f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', encoding='utf-8')
content = f.read()
f.close()

old = '            pool_name = "serverPool" if pool_cfg == dhcp_pools[0] else str(pool_cfg.get("name", "serverPool")).strip()'
new = '            if pool_cfg == dhcp_pools[0]:\n                pool_name = "serverPool"\n            else:\n                raw_net = str(pool_cfg.get("network", "")).strip()\n                pool_name = str(pool_cfg.get("name", f"rete{raw_net}")).strip() if not str(pool_cfg.get("name","")).startswith("Server") else f"rete{raw_net}"'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE')
