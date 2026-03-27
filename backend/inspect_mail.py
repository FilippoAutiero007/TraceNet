from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data

# Prende il PKT più recente nella cartella
pkts = sorted(Path(".").glob("*.pkt"), key=lambda p: p.stat().st_mtime, reverse=True)
print(f"PKT trovati: {[p.name for p in pkts]}")

pkt_file = pkts[0]
print(f"Leggo: {pkt_file.name}")

xml = decrypt_pkt_data(pkt_file.read_bytes()).decode("utf-8", "ignore")

for tag in ["EMAIL_SERVER", "EMAIL_CLIENT"]:
    idx = xml.find(f"<{tag}>")
    if idx != -1:
        print(f"\n=== {tag} ===")
        print(xml[idx:idx+600])
    else:
        print(f"\n{tag}: NON TROVATO")
