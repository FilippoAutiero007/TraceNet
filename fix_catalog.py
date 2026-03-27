import json
f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\device_catalog.json', encoding='utf-8')
data = json.load(f)
f.close()
data['server']['category'] = 'server'
data['pc']['category'] = 'pc'
data['laptop']['category'] = 'laptop'
open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\device_catalog.json', 'w', encoding='utf-8').write(json.dumps(data, indent=4))
print('OK')
