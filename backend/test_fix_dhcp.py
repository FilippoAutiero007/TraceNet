import json
from pathlib import Path
from app.services.pkt_generator.entrypoint import save_pkt_file
from app.models.schemas import NormalizedNetworkRequest, NormalizedSubnet

# Carica il JSON di test (gestisce BOM)
data = json.loads(Path("dhcp_bug_request.json").read_text("utf-8-sig"))
req = NormalizedNetworkRequest(**data)

subnets = [NormalizedSubnet(name="LAN1", required_hosts=20)]

config = {
    "devices": {"routers": 1, "switches": 1, "pcs": 5, "servers": 3},
    "routing_protocol": req.routing_protocol,
    "dhcp_from_router": req.dhcp_from_router,
    "dhcp_dns": req.dhcp_dns,
    "server_services": req.server_services,
    "servers_config": [srv.model_dump() for srv in req.servers_config],
    "topology": {},
}

print("=== CONFIG INPUT ===")
print(json.dumps(config, indent=2))

res = save_pkt_file(subnets, config, output_dir="pkt_test_fix")
print("\n=== SERVER DEVICES DOPO BUILD ===")
for d in res["devices"]:
    if str(d.get("type", "")).lower() == "server":
        print(f"\n{d['name']}:")
        print(f"  services: {d.get('server_services', [])}")
        print(f"  hostname: {d.get('hostname')}")
        print(f"  has_dhcp_pool: {'dhcp_pools' in d}")
        if 'dhcp_pools' in d:
            print(f"  dhcp_pools: {d['dhcp_pools']}")
