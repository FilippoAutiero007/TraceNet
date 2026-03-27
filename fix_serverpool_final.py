f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', encoding='utf-8')
content = f.read()
f.close()

# Fix 1: fallback usa rete<network> invece di serverPool
old1 = '''            dhcp_pools = [{
                "name": "serverPool",'''
new1 = '''            dhcp_pools = [{
                "name": f"rete{network_addr}",'''
content = content.replace(old1, new1)

# Fix 2: rimuovi il forzaggio serverPool sul primo pool
old2 = '''            # Usa sempre "serverPool" come nome del primo pool per compatibilita con PT GUI
            if pool_cfg == dhcp_pools[0]:
                pool_name = "serverPool"
            else:
                raw_net = str(pool_cfg.get("network", "")).strip()
                pool_name = str(pool_cfg.get("name", f"rete{raw_net}")).strip() if not str(pool_cfg.get("name","")).startswith("Server") else f"rete{raw_net}"'''
new2 = '''            raw_net = str(pool_cfg.get("network", "")).strip()
            pool_name = str(pool_cfg.get("name", f"rete{raw_net}")).strip()'''

content = content.replace(old2, new2)

f = open(r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\app\services\pkt_generator\server_config.py', 'w', encoding='utf-8')
f.write(content)
f.close()

# Verifica
remaining = content.count('serverPool')
print(f'serverPool rimasti nel file: {remaining}')
