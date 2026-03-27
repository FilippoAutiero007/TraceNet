f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\generator_components\device_build.py', encoding='utf-8')
lines = f.readlines()
f.close()

# Rimuovi le righe con DEBUG
lines = [l for l in lines if 'DEBUG write_dhcp_config' not in l]

# Trova riga con write_dhcp_config(engine, dev_cfg) e aggiungi print semplice
for i, l in enumerate(lines):
    if 'write_dhcp_config(engine, dev_cfg)' in l:
        indent = '        '
        lines.insert(i, indent + 'enabled_el = engine.find("DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED")\n')
        lines.insert(i+1, indent + 'print("DHCP BEFORE:", enabled_el.text if enabled_el is not None else "NOT FOUND")\n')
        lines.insert(i+3, indent + 'enabled_el2 = engine.find("DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED")\n')
        lines.insert(i+4, indent + 'print("DHCP AFTER:", enabled_el2.text if enabled_el2 is not None else "NOT FOUND")\n')
        print(f'Debug inserito alla riga {i}')
        break

open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\generator_components\device_build.py', 'w', encoding='utf-8').writelines(lines)
print('OK')
