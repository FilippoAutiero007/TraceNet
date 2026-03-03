from pathlib import Path
import sys
sys.path.insert(0,".")
from app.services.pkt_generator.generator import PKTGenerator

outdir=Path("tmp_out_min2"); outdir.mkdir(exist_ok=True)
g=PKTGenerator()
g.generate([{"name":"Router0","type":"router-2port"}], links_config=[], output_path=str(outdir/"minimal_noworkspace.pkt"))
print("written", outdir/"minimal_noworkspace.pkt")
