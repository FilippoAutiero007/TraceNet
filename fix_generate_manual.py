f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\routers\generate.py', encoding='utf-8')
lines = f.readlines()
f.close()

for i, l in enumerate(lines):
    if '"server_services": request.server_services or [],' in l and i > 185:
        indent = '            '
        lines.insert(i+1, indent + '"dhcp_from_router": getattr(request, "dhcp_from_router", False),\n')
        lines.insert(i+2, indent + '"servers_config": [s.model_dump() for s in request.servers_config] if getattr(request, "servers_config", None) else [],\n')
        lines.insert(i+3, indent + '"pcs_config": [p.model_dump() for p in request.pcs_config] if getattr(request, "pcs_config", None) else [],\n')
        print(f'Fix inserita dopo riga {i+1}')
        break

open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\routers\generate.py', 'w', encoding='utf-8').writelines(lines)
print('OK')
