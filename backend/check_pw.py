import xml.etree.ElementTree as ET

def dump_pw_summary(path: str) -> None:
    root = ET.parse(path).getroot()
    pw = root.find("PHYSICALWORKSPACE")
    print("=== ", path, " ===")
    # conta quanti NODE per nome
    counts = {}
    for node in pw.iter("NODE"):
        name = (node.findtext("NAME") or "").strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    print("NODE names:", sorted(counts.items()))
    # per ogni device in NETWORK/DEVICES mostra catena PHYSICAL e uuid
    devices = root.find("NETWORK/DEVICES")
    pw_uuid = {}
    for node in pw.iter("NODE"):
        n = node.findtext("NAME")
        u = node.findtext("UUID_STR")
        if n and u:
            pw_uuid[n.strip()] = u.strip("{}")
    for dev in devices:
        name = dev.findtext("ENGINE/NAME")
        chain = dev.findtext("WORKSPACE/PHYSICAL", "")
        last = chain.split(",")[-1].strip("{} ") if chain else ""
        print(f"{name}: last={last}, pw_uuid={pw_uuid.get(name)}")

for f in ("testok.xml", "kotest.xml"):
    dump_pw_summary(f)
