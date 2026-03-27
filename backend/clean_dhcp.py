with open("app/services/pkt_generator/server_config.py", "r") as f:
    lines = f.readlines()

# Rimuovi duplicati del controllo DHCP (righe 153-157)
fixed = []
skip_next = False
for i, line in enumerate(lines):
    if "def write_dhcp_config" in line:
        skip_next = False
    if skip_next or (i >= 153 and i <= 157 and '"dhcp" not in {' in line and line.strip() != lines[152].strip()):
        skip_next = True
        continue
    fixed.append(line)

with open("app/services/pkt_generator/server_config.py", "w") as f:
    f.writelines(fixed)
print("Duplicati DHCP rimossi!")
