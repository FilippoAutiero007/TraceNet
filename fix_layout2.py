f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', encoding='utf-8')
lines = f.readlines()
f.close()

# Trova le righe start e end del blocco da sostituire
start_line = None
end_line = None
for i, line in enumerate(lines):
    if 'sw_x = pos.get(switches[0]' in line:
        start_line = i
    if start_line is not None and 'pos[name] = (px + params.dx_host * 0.8, py)' in line:
        end_line = i
        break

print(f'start={start_line}, end={end_line}')
if start_line is not None and end_line is not None:
    new_lines = [
        '    # sw_x: centro medio di tutti gli switch presenti\n',
        '    if switches:\n',
        '        sw_xs = [pos.get(sw, (params.base_x, switch_y))[0] for sw in switches]\n',
        '        sw_x = sum(sw_xs) / len(sw_xs)\n',
        '    else:\n',
        '        sw_x = params.base_x\n',
        '\n',
        '    # Riga 4: server interni centrati rispetto agli switch\n',
        '    server_y = switch_y + params.dy_layer\n',
        '    dmz_servers = [s for s in servers if "dmz" in s.lower()]\n',
        '    internal_servers = [s for s in servers if s not in dmz_servers]\n',
        '\n',
        '    # DMZ server sulla sinistra (vicino al firewall)\n',
        '    set_row(pos, dmz_servers, params.base_x, params.base_y + params.dy_layer + 90, params.dx_host)\n',
        '\n',
        '    # Server interni: spaziatura larga, offset +60 per evitare sovrapposizione cavi\n',
        '    srv_spacing = max(params.dx_host * 1.8, 220)\n',
        '    total_srv = len(internal_servers)\n',
        '    for idx, srv in enumerate(internal_servers):\n',
        '        x = sw_x + (idx - (total_srv - 1) / 2.0) * srv_spacing + 60\n',
        '        pos[srv] = (x, server_y)\n',
        '\n',
        '    # Riga 5: PC con gap verticale doppio (salta la riga server)\n',
        '    pc_only = [h for h in endpoints if h not in servers]\n',
        '    grouped = hosts_by_parent(pc_only, switches, adjacency)\n',
        '    assign_hosts_under_switches(\n',
        '        pos,\n',
        '        grouped,\n',
        '        switch_y,\n',
        '        params,\n',
        '        host_base_layer_gap=params.dy_layer * 2 + 20,\n',
        '    )\n',
        '\n',
        '    # Offset orizzontale PC per disallineare cavi da quelli dei server\n',
        '    pc_set = set(pc_only)\n',
        '    for name in pc_set:\n',
        '        if name in pos:\n',
        '            px, py = pos[name]\n',
        '            pos[name] = (px - params.dx_host * 0.6, py)\n',
    ]
    lines[start_line:end_line+1] = new_lines
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\layout_scenarios.py', 'w', encoding='utf-8').writelines(lines)
    print('OK - fix layout applicata')
else:
    print('ERRORE - righe non trovate')
