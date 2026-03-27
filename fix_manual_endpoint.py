f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\routers\generate.py', encoding='utf-8')
lines = f.readlines()
f.close()

# Trova la riga con "server_services": request.server_services or [],
start = None
end = None
for i, l in enumerate(lines):
    if '"server_services": request.server_services or [],' in l:
        start = i
    if start is not None and l.strip() == '}':
        end = i
        break

print(f'start={start}, end={end}')
if start is not None and end is not None:
    lines[start] = lines[start].rstrip('\n') + '\n'
    # Inserisci dopo server_services
    insert = [
        '            "dhcp_from_router": getattr(request, "dhcp_from_router", False),\n',
        '            "servers_config": [s.model_dump() for s in request.servers_config] if getattr(request, "servers_config", None) else [],\n',
        '            "pcs_config": [p.model_dump() for p in request.pcs_config] if getattr(request, "pcs_config", None) else [],\n',
    ]
    lines[start+1:start+1] = insert
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\routers\generate.py', 'w', encoding='utf-8').writelines(lines)
    print('OK - fix applicata')
else:
    print('ERRORE - riga non trovata')
