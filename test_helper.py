import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')

from app.services.pkt_generator.entrypoint import save_pkt_file
from app.services.subnet_calculator import SubnetResult

# Simula due subnet: LAN1 (con DHCP server) e LAN2 (senza)
class FakeSubnet:
    def __init__(self, name, network, mask, gateway, start, end):
        self.name = name
        self.network = network
        self.mask = mask
        self.gateway = gateway
        self.usable_range = [start, end]
        self.dns_server = None

subnets = [
    FakeSubnet("LAN1", "192.168.1.0", "255.255.255.0", "192.168.1.1", "192.168.1.2", "192.168.1.254"),
    FakeSubnet("LAN2", "192.168.2.0", "255.255.255.0", "192.168.2.1", "192.168.2.2", "192.168.2.254"),
]

config = {
    "devices": {"routers": 2, "switches": 2, "pcs": 2, "servers": 1},
    "routing_protocol": "static",
    "server_services": ["dhcp"],
    "servers_config": [{"services": ["dhcp"]}],
}

result = save_pkt_file(subnets, config, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend\output')

if result.get("success"):
    print("PKT generato:", result["pkt_file"])
    for d in result["devices"]:
        if d.get("type") in ("router", "router-2port") or str(d.get("name","")).startswith("Router"):
            print(f"\n{d['name']}:")
            print(f"  dhcp_server_ip = {d.get('dhcp_server_ip', 'NON PRESENTE')}")
            for iface in d.get("interfaces") or []:
                print(f"  iface {iface.get('name')} role={iface.get('role')} ip={iface.get('ip')}")
else:
    print("ERRORE:", result.get("error"))
