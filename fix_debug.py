f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\generator_components\device_build.py', encoding='utf-8')
lines = f.readlines()
f.close()

# Trova riga con write_dhcp_config(engine, dev_cfg)
for i, l in enumerate(lines):
    if 'write_dhcp_config(engine, dev_cfg)' in l:
        lines.insert(i, '        print(f\"DEBUG write_dhcp_config: DHCP_SERVERS ENABLED before={engine.find(chr(39)DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED chr(39))}, id(engine)={id(engine)}\")\n')
        lines.insert(i+2, '        print(f\"DEBUG write_dhcp_config: DHCP_SERVERS ENABLED after={engine.find(chr(39)DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED chr(39)).text if engine.find(chr(39)DHCP_SERVERS/ASSOCIATED_PORTS/ASSOCIATED_PORT/DHCP_SERVER/ENABLED chr(39)) is not None else None}\")\n')
        print(f'Inserito debug alla riga {i}')
        break

open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\generator_components\device_build.py', 'w', encoding='utf-8').writelines(lines)
print('OK')
