f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', encoding='utf-8')
content = f.read()
f.close()

old = '''    if routers:
        router = routers[0]
        placed_hosts = {h for v in grouped.values() for h in v}
        direct_neighbors = [n for n in adjacency.get(router, []) if n in endpoints and n not in placed_hosts]
        for idx, name in enumerate(sorted(direct_neighbors)):
            pos[name] = (params.base_x + 220, params.base_y + params.dy_layer + (idx + 1) * 75)'''

new = '''    if routers:
        router = routers[0]
        placed_hosts = {h for v in grouped.values() for h in v}
        direct_neighbors = [n for n in adjacency.get(router, []) if n in endpoints and n not in placed_hosts]
        # I server collegati direttamente al router vanno sotto il primo switch, non a fianco del router
        srv_neighbors = [n for n in direct_neighbors if is_server({"name": n})]
        other_neighbors = [n for n in direct_neighbors if n not in srv_neighbors]
        if srv_neighbors and switches:
            # Aggiungi i server al gruppo del primo switch e riposiziona
            first_sw = switches[0]
            if first_sw not in grouped:
                grouped[first_sw] = []
            grouped[first_sw] = srv_neighbors + grouped[first_sw]
            assign_hosts_under_switches(pos, {first_sw: grouped[first_sw]}, switch_y, params)
        for idx, name in enumerate(sorted(other_neighbors)):
            pos[name] = (params.base_x + 220, params.base_y + params.dy_layer + (idx + 1) * 75)'''

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE - blocco non trovato')
