from pathlib import Path
import sys
sys.path.insert(0, ".")

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator.generator import PKTGenerator

outdir = Path("tmp_out_min")
outdir.mkdir(exist_ok=True)

g = PKTGenerator()
devices = [{"name": "Router0", "type": "router-2port"}]
links = []

pkt_path = outdir / "minimal.pkt"
g.generate(devices, links_config=links, output_path=str(pkt_path))

xml = decrypt_pkt_data(pkt_path.read_bytes())
(outdir / "minimal.xml").write_bytes(xml)

print("Wrote", pkt_path, "size", pkt_path.stat().st_size)
print("XML bytes", len(xml))
