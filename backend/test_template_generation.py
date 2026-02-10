# Quick test of template-based PKT generation
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.pkt_file_generator import save_pkt_file

# Mock subnet object
class MockSubnet:
    def __init__(self, name, network, mask, usable_range):
        self.name = name
        self.network = network
        self.mask = mask
        self.usable_range = usable_range

# Test data
subnets = [
    MockSubnet("Admin", "192.168.1.0", "255.255.255.192", 
               ["192.168.1.1", "192.168.1.2", "192.168.1.3"]),
    MockSubnet("Guest", "192.168.1.64", "255.255.255.192",
               ["192.168.1.65", "192.168.1.66", "192.168.1.67"])
]

config = {
    "devices": {
        "routers": 1,
        "switches": 1,
        "pcs": 4
    }
}

output_dir = "test_output"

print("🧪 Testing template-based PKT generation...")
print("=" * 60)

result = save_pkt_file(subnets, config, output_dir)

print("\n📊 Result:")
print(f"Success: {result.get('success')}")
print(f"PKT Path: {result.get('pkt_path')}")
print(f"XML Path: {result.get('xml_path')}")
print(f"Method: {result.get('method')}")
print(f"File Size: {result.get('file_size')} bytes")

if result.get('error'):
    print(f"❌ Error: {result.get('error')}")
else:
    print("\n✅ Test completed successfully!")
    print(f"\n📂 Generated file: {result.get('pkt_path')}")
    print("Try opening this file in Packet Tracer 8.2.2")
