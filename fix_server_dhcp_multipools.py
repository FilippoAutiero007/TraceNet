f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_dhcp.py', encoding='utf-8')
content = f.read()
f.close()

old = '''    assoc_ports = dhcp_servers.findall("ASSOCIATED_PORTS/ASSOCIATED_PORT")
    for ap in assoc_ports:
        srv = _ensure_child(ap, "DHCP_SERVER")
        _set_text(srv, "ENABLED", "1")
        pools = _ensure_child(srv, "POOLS")

        # Remove existing pools so rewrite is idempotent.
        for old_pool in list(pools.findall("POOL")):
            pools.remove(old_pool)

        pool = ET.SubElement(pools, "POOL")
        _set_text(pool, "NAME", pool_name)
        _set_text(pool, "NETWORK", str(network_addr))
        _set_text(pool, "MASK", str(mask))
        _set_text(pool, "DEFAULT_ROUTER", str(gateway))
        _set_text(pool, "START_IP", str(start_ip))
        _set_text(pool, "END_IP", str(end_ip))
        _set_text(pool, "DNS_SERVER", dns_server)
        _set_text(pool, "MAX_USERS", max_users)
        _set_text(pool, "LEASE_TIME", lease_time)
        _set_text(pool, "TFTP_ADDRESS", tftp_address)
        _set_text(pool, "WLC_ADDRESS", wlc_address)
        _set_text(pool, "DOMAIN_NAME", domain_name)

        # Required empty nodes (present once).
        _ensure_child(pool, "DHCP_POOL_LEASES")
        _ensure_child(srv, "DHCP_RESERVATIONS")
        _ensure_child(srv, "AUTOCONFIG")'''

new = '''    # Usa dhcp_pools se presenti (multi-pool), altrimenti pool singolo
    dhcp_pools_cfg = dev_cfg.get("dhcp_pools") or []

    assoc_ports = dhcp_servers.findall("ASSOCIATED_PORTS/ASSOCIATED_PORT")
    for ap in assoc_ports:
        srv = _ensure_child(ap, "DHCP_SERVER")
        _set_text(srv, "ENABLED", "1")
        pools_el = _ensure_child(srv, "POOLS")

        # Remove existing pools so rewrite is idempotent.
        for old_pool in list(pools_el.findall("POOL")):
            pools_el.remove(old_pool)

        if dhcp_pools_cfg:
            # Multi-pool: uno per ogni LAN
            for pool_cfg in dhcp_pools_cfg:
                pool_gw_parsed = _parse_ipv4(pool_cfg.get("gateway", str(gateway)))
                pool_net = _parse_network_from_ip_and_mask(
                    pool_cfg.get("network", str(network_addr)),
                    pool_cfg.get("mask", str(mask))
                )
                if pool_net is None:
                    pool_net = net
                if pool_gw_parsed is None:
                    pool_gw_parsed = gateway
                p_first, p_last = _usable_bounds(pool_net)
                p_reserved = {pool_gw_parsed}
                p_si = _parse_ipv4(dev_cfg.get("ip"))
                if p_si:
                    p_reserved.add(p_si)
                p_start = _compute_start_ip(pool_net, start_offset=5, reserved=p_reserved)
                p_end = p_last
                p_dns = str(pool_cfg.get("dns", dns_server))
                p_name = str(pool_cfg.get("name", pool_name))

                pool = ET.SubElement(pools_el, "POOL")
                _set_text(pool, "NAME", p_name)
                _set_text(pool, "NETWORK", str(pool_net.network_address))
                _set_text(pool, "MASK", str(pool_net.netmask))
                _set_text(pool, "DEFAULT_ROUTER", str(pool_gw_parsed))
                _set_text(pool, "START_IP", str(p_start))
                _set_text(pool, "END_IP", str(p_end))
                _set_text(pool, "DNS_SERVER", p_dns)
                _set_text(pool, "MAX_USERS", max_users)
                _set_text(pool, "LEASE_TIME", lease_time)
                _set_text(pool, "TFTP_ADDRESS", tftp_address)
                _set_text(pool, "WLC_ADDRESS", wlc_address)
                _set_text(pool, "DOMAIN_NAME", domain_name)
                _ensure_child(pool, "DHCP_POOL_LEASES")
        else:
            # Pool singolo (fallback)
            pool = ET.SubElement(pools_el, "POOL")
            _set_text(pool, "NAME", pool_name)
            _set_text(pool, "NETWORK", str(network_addr))
            _set_text(pool, "MASK", str(mask))
            _set_text(pool, "DEFAULT_ROUTER", str(gateway))
            _set_text(pool, "START_IP", str(start_ip))
            _set_text(pool, "END_IP", str(end_ip))
            _set_text(pool, "DNS_SERVER", dns_server)
            _set_text(pool, "MAX_USERS", max_users)
            _set_text(pool, "LEASE_TIME", lease_time)
            _set_text(pool, "TFTP_ADDRESS", tftp_address)
            _set_text(pool, "WLC_ADDRESS", wlc_address)
            _set_text(pool, "DOMAIN_NAME", domain_name)
            _ensure_child(pool, "DHCP_POOL_LEASES")

        _ensure_child(srv, "DHCP_RESERVATIONS")
        _ensure_child(srv, "AUTOCONFIG")'''

if old in content:
    content = content.replace(old, new)
    open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_dhcp.py', 'w', encoding='utf-8').write(content)
    print('OK')
else:
    print('ERRORE - blocco non trovato')
