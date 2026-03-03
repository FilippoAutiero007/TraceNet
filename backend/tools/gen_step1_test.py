from pathlib import Path
import sys
sys.path.insert(0,".")
from app.services.pkt_generator.generator import PKTGenerator

outdir=Path("tmp_step1"); outdir.mkdir(exist_ok=True)
generator = PKTGenerator()
output_file = outdir / "minimal_step1.pkt"

devices_config = [
    {"name": "Router0", "type": "router-2port"},
    {"name": "Router1", "type": "router-2port"},
]
links_config = [
    {
        "from": "Router0",
        "to": "Router1",
        "from_port": "FastEthernet0/0",
        "to_port": "FastEthernet0/0",
    }
]

generator.generate(
    devices_config=devices_config,
    links_config=[],
    output_path=str(output_file),
)
print("OK ->", output_file)
