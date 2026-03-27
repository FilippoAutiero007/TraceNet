f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', encoding='utf-8')
content = f.read()
f.close()

old = '''    # Server interni: spaziatura larga, offset +60 per evitare sovrapposizione cavi
    srv_spacing = max(params.dx_host * 1.8, 220)
    total_srv = len(internal_servers)
    for idx, srv in enumerate(internal_servers):
        x = sw_x + (idx - (total_srv - 1) / 2.0) * srv_spacing + 60
        pos[srv] = (x, server_y)'''

new = '''    # Server interni: centrati rispetto al loro switch di appartenenza
    srv_spacing = max(params.dx_host * 1.8, 220)
    total_srv = len(internal_servers)
    for idx, srv in enumerate(internal_servers):
        # Cerca lo switch a cui e collegato il server
        parent_sw = None
        for sw in switches:
            if srv in adjacency.get(sw, []):
                parent_sw = sw
                break
        if parent_sw and parent_sw in pos:
            x = pos[parent_sw][0]
        else:
            x = sw_x + (idx - (total_srv - 1) / 2.0) * srv_spacing
        pos[srv] = (x, server_y)'''

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE - blocco non trovato')
