import json
from pathlib import Path
from app.services.pkt_generator.entrypoint import save_pkt_file
from app.models.schemas import NormalizedNetworkRequest, SubnetRequest
from app.services.subnet_calculator import calculate_vlsm

data = json.loads(Path("dhcp_bug_request.json").read_text("utf-8-sig"))
req = NormalizedNetworkRequest(**data)

# Converti subnet e chiama calculate_vlsm come fa il router reale
subnets_input = [SubnetRequest(name=s.name, required_hosts=s.required_hosts) for s in req.subnets]
subnets = calculate_vlsm(req.base_network, subnets_input)

print("=== SUBNETS DOPO VLSM ===")
for s in subnets:
    print(f"  {s.name}: network={s.network} gateway={s.gateway} usable_range={s.usable_range}")

config = {
    "devices": {"routers": 1, "switches": 1, "pcs": 3, "servers": 3},
    "routing_protocol": req.routing_protocol,
    "dhcp_from_router": req.dhcp_from_router,
    "dhcp_dns": req.dhcp_dns,
    "server_services": req.server_services,
    "servers_config": [srv.model_dump() for srv in req.servers_config],
    "topology": {},
}

res = save_pkt_file(subnets, config, output_dir="pkt_visual_test")
print("\nFile generato:", res.get("pkt_path") or res.get("output_path") or res)

print("\n=== SERVER DEVICES DOPO BUILD ===")
for d in res["devices"]:
    if str(d.get("type", "")).lower() == "server":
        print(f"\n{d['name']}:")
        print(f"  ip:          {d.get('ip', 'MANCANTE')}")
        print(f"  gateway:     {d.get('gateway_ip', 'MANCANTE')}")
        print(f"  services:    {d.get('server_services', [])}")
        print(f"  hostname:    {d.get('hostname')}")
        print(f"  dhcp_pools:  {d.get('dhcp_pools', 'nessuno')}")
        print(f"  dns_records: {d.get('dns_records', 'nessuno')}")
