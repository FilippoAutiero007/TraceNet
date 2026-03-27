f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', encoding='utf-8')
content = f.read()
f.close()

old = '        if raw_cfg.get("mail_users"):\n            dev["mail_users"] = raw_cfg["mail_users"]'
new = '        if raw_cfg.get("mail_users"):\n            dev["mail_users"] = raw_cfg["mail_users"]\n        if raw_cfg.get("dhcp_pools"):\n            dev["dhcp_pools"] = raw_cfg["dhcp_pools"]'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE')
