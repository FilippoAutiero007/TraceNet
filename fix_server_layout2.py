f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', encoding='utf-8')
content = f.read()
f.close()

old = '        srv_neighbors = [n for n in direct_neighbors if is_server({"name": n})]'
new = '        srv_neighbors = [n for n in direct_neighbors if "server" in n.lower()]'

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE - riga non trovata')
    print('Cerco contesto...')
    idx = content.find('srv_neighbors')
    if idx != -1:
        print(repr(content[idx-5:idx+80]))
