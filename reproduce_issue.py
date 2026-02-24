import os
import logging
from app.services.pkt_generator.topology import save_pkt_file, build_links_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockSubnet:
    def __init__(self):
        self.usable_range = ["192.168.1.2", "192.168.1.3"]
        self.mask = "255.255.255.0"

def reproduce():
    # User scenario: 1 Router, 1 Switch, 2 PCs
    num_routers = 1
    num_switches = 1
    num_pcs = 2

    print("--- Testing Link Config Generation ---")
    links_config = build_links_config(num_routers, num_switches, num_pcs)
    for l in links_config:
        print(f"Link: {l['from']}({l['from_port']}) -> {l['to']}({l['to_port']})")

    # Generate file to trigger logs (if template is set)
    # We need to set the env var for template path
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend", "templates", "simple_ref.pkt"))
    os.environ["PKT_TEMPLATE_PATH"] = template_path
    
    if not os.path.exists(template_path):
        print(f"Warning: Template not found at {template_path}. Skipping full generation.")
        return

    print("\n--- Generating PKT ---")
    subnets = [MockSubnet()]
    config = {
        "devices": {
            "routers": num_routers,
            "switches": num_switches,
            "pcs": num_pcs
        }
    }
    
    try:
        result = save_pkt_file(subnets, config, "pkt_debug_output")
        print("\nGeneration Result Keys:", result.keys())
        print("Generated Links count:", len(result["links"]))
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == "__main__":
    reproduce()
