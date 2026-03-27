f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
lines = f.readlines()
f.close()

# Trova la riga con "# Prepara i dhcp_pools"
for i, l in enumerate(lines):
    if '# Prepara i dhcp_pools per i server DHCP' in l:
        # Inserisci check prima del blocco
        lines.insert(i, '        # Se l\'utente ha gia specificato dhcp_pools via servers_config, non sovrascrivere\n')
        break

# Trova la riga che sovrascrive d["dhcp_pools"]
for i, l in enumerate(lines):
    if 'd["dhcp_pools"] = all_pools' in l:
        lines[i] = '            if not d.get("dhcp_pools"):\n                d["dhcp_pools"] = all_pools\n'
        break

open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').writelines(lines)
print('OK')
