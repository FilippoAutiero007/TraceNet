with open("app/services/pkt_generator/server_config.py", "r") as f:
    content = f.read()

old_dhcp = '''def write_dhcp_config(engine: ET.Element, dev_cfg: dict) -> None:'''
new_dhcp = '''def write_dhcp_config(engine: ET.Element, dev_cfg: dict) -> None:
    if "dhcp" not in {str(s).strip().lower() for s in (dev_cfg.get("server_services") or [])}:
        return'''

content = content.replace(old_dhcp, new_dhcp)
with open("app/services/pkt_generator/server_config.py", "w") as f:
    f.write(content)
print("DHCP fix applicato!")
