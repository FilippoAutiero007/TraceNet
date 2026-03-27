f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', encoding='utf-8')
content = f.read()
f.close()

old = (
    '        # Propaga dhcp_server_ip ai router per ip helper-address\n'
    '        for d in devices_config:\n'
    '            if d.get("type") == "server" and d.get("ip"):\n'
    '                svc = {str(s).lower() for s in (d.get("server_services") or [])}\n'
    '                if "dhcp" in svc:\n'
    '                    for r in routers_config:\n'
    '                        r["dhcp_server_ip"] = d["ip"]\n'
    '                    break'
)

new = (
    '        # Propaga dhcp_server_ip ai router per ip helper-address\n'
    '        # Solo ai router che NON sono nella stessa LAN del server DHCP\n'
    '        for d in devices_config:\n'
    '            if str(d.get("type", "")).lower() != "server":\n'
    '                continue\n'
    '            svc = {str(s).lower() for s in (d.get("server_services") or [])}\n'
    '            if "dhcp" not in svc or not d.get("ip"):\n'
    '                continue\n'
    '            dhcp_srv_network = None\n'
    '            try:\n'
    '                import ipaddress as _ipa\n'
    '                dhcp_srv_network = str(_ipa.IPv4Network(\n'
    '                    str(d["ip"]) + "/" + str(d.get("subnet", "255.255.255.0")),\n'
    '                    strict=False).network_address)\n'
    '            except Exception:\n'
    '                pass\n'
    '            for r in routers_config:\n'
    '                same_lan = False\n'
    '                for iface in r.get("interfaces") or []:\n'
    '                    if str(iface.get("role", "")).lower() != "lan":\n'
    '                        continue\n'
    '                    try:\n'
    '                        r_net = str(_ipa.IPv4Network(\n'
    '                            str(iface["ip"]) + "/" + str(iface.get("mask", "255.255.255.0")),\n'
    '                            strict=False).network_address)\n'
    '                        if dhcp_srv_network and r_net == dhcp_srv_network:\n'
    '                            same_lan = True\n'
    '                            break\n'
    '                    except Exception:\n'
    '                        continue\n'
    '                if not same_lan:\n'
    '                    r["dhcp_server_ip"] = d["ip"]\n'
    '            break'
)

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\entrypoint.py', 'w', encoding='utf-8').write(content)
    print('OK - fix applicata')
else:
    print('ERRORE - blocco non trovato')
