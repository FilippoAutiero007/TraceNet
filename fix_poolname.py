f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', encoding='utf-8')
content = f.read()
f.close()

old = '            pool_name = str(pool_cfg.get("name", "serverPool")).strip()'
new = '            # Usa sempre "serverPool" come nome del primo pool per compatibilita con PT GUI\n            pool_name = "serverPool" if pool_cfg == dhcp_pools[0] else str(pool_cfg.get("name", "serverPool")).strip()'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE')
