import json
from pathlib import Path
from app.services.pkt_generator.entrypoint import save_pkt_file
from app.models.schemas import NormalizedNetworkRequest, NormalizedSubnet

data = json.loads(Path("dhcp_bug_request.json").read_text("utf-8-sig"))
req = NormalizedNetworkRequest(**data)
subnets = [NormalizedSubnet(**s) for s in data["subnets"]]

config = {
    "devices": {"routers": 1, "switches": 1, "pcs": 3, "servers": 3},
    "routing_protocol": req.routing_protocol,
    "dhcp_from_router": req.dhcp_from_router,
    "dhcp_dns": req.dhcp_dns,
    "server_services": req.server_services,
    "servers_config": [srv.model_dump() for srv in req.servers_config],
    "topology": {},
}

import app.services.pkt_generator.entrypoint as ep
_orig = ep.save_pkt_file

import ipaddress

def patched(*args, **kwargs):
    subnets_arg = args[0]
    print("=== SUBNETS PASSATE ===")
    for s in subnets_arg:
        print(f"  {s}")
    return _orig(*args, **kwargs)

ep.save_pkt_file = patched

result = patched(subnets, config, output_dir="pkt_debug2")
print("done")
