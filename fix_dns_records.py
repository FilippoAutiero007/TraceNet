f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', encoding='utf-8')
content = f.read()
f.close()

old = '    if isinstance(dns_server.get("dns_records"), list) and not dns_server.get("auto_dns_records"):\n                return'
new = '    if isinstance(dns_server.get("dns_records"), list) and dns_server["dns_records"] and not dns_server.get("auto_dns_records"):\n        return'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE')
    idx = content.find('auto_dns_records')
    print(repr(content[idx-100:idx+100]))
