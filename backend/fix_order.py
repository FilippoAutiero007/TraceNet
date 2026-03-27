import re
with open("app/services/pkt_generator/device_build.py", "r") as f:
    content = f.read()

# Sposta write_dhcp_config DOPO build_server_configs
content = re.sub(
    r'from app\.services\.pkt_generator\.server_config import write_dhcp_config\s*write_dhcp_config\(engine, dev_cfg\)',
    '',
    content
)

# Aggiungi dopo build_server_configs
content = re.sub(
    r'build_server_configs\([^)]+\)\s*',
    r'build_server_configs(num_servers, servers_config_list, server_services_global, devices_config)\n        if "dhcp" in {str(s).strip().lower() for s in server_services_global}:\n            from app.services.pkt_generator.server_config import write_dhcp_config\n            for dev in devices_config:\n                if str(dev.get("type", "")).lower() == "server":\n                    write_dhcp_config(engine, dev)',
    content
)

with open("app/services/pkt_generator/device_build.py", "w") as f:
    f.write(content)
print("DHCP ordine corretto!")
