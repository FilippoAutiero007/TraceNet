import re
with open("app/services/pkt_generator/server_config.py", "r") as f:
    content = f.read()

# Pulisci le righe duplicate del controllo DHCP
content = re.sub(r'if "dhcp" not in \{[^\n]*\}\:\s*\n\s*return\n\s*if "dhcp" not in \{[^\n]*\}\:', 'if "dhcp" not in {str(s).strip().lower() for s in (dev_cfg.get("server_services") or [])}:\n        return', content)

with open("app/services/pkt_generator/server_config.py", "w") as f:
    f.write(content)
print("DHCP pulito!")
