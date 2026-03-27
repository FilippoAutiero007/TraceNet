with open("app/services/pkt_generator/server_config.py", "r") as f:
    content = f.read()

# Fix DEFINITIVO: controlla server_services PRIMA di tutto
new_content = re.sub(
    r'def write_dhcp_config\\(engine: ET\\.Element, dev_cfg: dict\\) -> None:\\s*if "dhcp" not in',
    r'def write_dhcp_config(engine: ET.Element, dev_cfg: dict) -> None:\n    services = {str(s).strip().lower() for s in (dev_cfg.get("server_services") or [])}\n    if "dhcp" not in services:\n        return',
    content,
    flags=re.MULTILINE
)

with open("app/services/pkt_generator/server_config.py", "w") as f:
    f.write(new_content)
print("DHCP fix definitivo applicato!")
