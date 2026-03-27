f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', encoding='utf-8')
lines = f.readlines()
f.close()

start = None
end = None
for i, l in enumerate(lines):
    if 'for ap in dhcp_servers.findall("ASSOCIATED_PORTS/ASSOCIATED_PORT"):' in l:
        start = i
    if start is not None and i > start and 'def write_ftp_users' in l:
        end = i
        break

print(f'start={start}, end={end}')
if start is not None and end is not None:
    new_lines = [
        '    for ap in dhcp_servers.findall("ASSOCIATED_PORTS/ASSOCIATED_PORT"):\n',
        '        dhcp_server = ap.find("DHCP_SERVER")\n',
        '        if dhcp_server is None:\n',
        '            continue\n',
        '\n',
        '        enabled = dhcp_server.find("ENABLED")\n',
        '        if enabled is None:\n',
        '            enabled = ET.SubElement(dhcp_server, "ENABLED")\n',
        '        enabled.text = "1"\n',
        '\n',
        '        pools = dhcp_server.find("POOLS")\n',
        '        if pools is None:\n',
        '            continue\n',
        '        # Rimuovi pool esistenti e riscrivi da dhcp_pools\n',
        '        for old_pool in list(pools.findall("POOL")):\n',
        '            pools.remove(old_pool)\n',
        '\n',
        '        dhcp_pools = dev_cfg.get("dhcp_pools") or []\n',
        '        if not dhcp_pools:\n',
        '            # Fallback: un pool dalla LAN del server\n',
        '            dhcp_pools = [{\n',
        '                "name": "serverPool",\n',
        '                "network": network_addr,\n',
        '                "mask": mask,\n',
        '                "gateway": gateway,\n',
        '                "dns": str(dns_ip),\n',
        '            }]\n',
        '\n',
        '        for pool_cfg in dhcp_pools:\n',
        '            pool_gw = str(pool_cfg.get("gateway", gateway)).strip()\n',
        '            pool_mask = str(pool_cfg.get("mask", mask)).strip()\n',
        '            pool_net = str(pool_cfg.get("network", network_addr)).strip()\n',
        '            pool_dns = str(pool_cfg.get("dns", dns_ip)).strip()\n',
        '            pool_name = str(pool_cfg.get("name", "serverPool")).strip()\n',
        '            try:\n',
        '                import ipaddress as _ipa\n',
        '                pnet = _ipa.IPv4Network(f"{pool_gw}/{pool_mask}", strict=False)\n',
        '                phosts = list(pnet.hosts())\n',
        '                pstart = str(phosts[5]) if len(phosts) > 5 else str(phosts[0])\n',
        '                pend = str(phosts[-1])\n',
        '                pnet_addr = str(pnet.network_address)\n',
        '            except Exception:\n',
        '                pstart = "0.0.0.0"\n',
        '                pend = "0.0.0.0"\n',
        '                pnet_addr = pool_net\n',
        '\n',
        '            pool = ET.SubElement(pools, "POOL")\n',
        '            def _st(tag: str, val: str) -> None:\n',
        '                elem = ET.SubElement(pool, tag)\n',
        '                elem.text = val\n',
        '            _st("NAME",           pool_name)\n',
        '            _st("NETWORK",        pnet_addr)\n',
        '            _st("MASK",           pool_mask)\n',
        '            _st("DEFAULT_ROUTER", pool_gw)\n',
        '            _st("TFTP_ADDRESS",   "0.0.0.0")\n',
        '            _st("START_IP",       pstart)\n',
        '            _st("END_IP",         pend)\n',
        '            _st("DNS_SERVER",     pool_dns)\n',
        '            _st("MAX_USERS",      "512")\n',
        '            _st("LEASE_TIME",     "86400000")\n',
        '            _st("WLC_ADDRESS",    "0.0.0.0")\n',
        '            _st("DOMAIN_NAME",    "")\n',
        '\n',
    ]
    lines[start:end] = new_lines
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', 'w', encoding='utf-8').writelines(lines)
    print('OK - fix applicata')
else:
    print('ERRORE - blocco non trovato')
