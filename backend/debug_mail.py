import json
from app.models.schemas import NormalizedNetworkRequest, SubnetRequest
from app.services.subnet_calculator import calculate_vlsm
from app.services.pkt_generator.entrypoint import save_pkt_file

data = {
  "base_network": "192.168.1.0/24",
  "routers": 1, "switches": 1, "pcs": 3, "servers": 4,
  "routing_protocol": "STATIC", "dhcp_from_router": False,
  "server_services": [],
  "servers_config": [
    {"services": ["dns"], "hostname": "dns1.local"},
    {"services": ["http"], "hostname": "web1.local"},
    {"services": ["email"], "hostname": "mail1.local",
     "mail_domain": "tracenet.com",
     "mail_users": [
       {"username": "filippo", "password": "Filippo07!"},
       {"username": "giacomo", "password": "giacomo99"}
     ]},
    {"services": ["dhcp"], "hostname": "dhcp1.local"}
  ],
  "subnets": [{"name": "LAN1", "required_hosts": 40}]
}

req = NormalizedNetworkRequest(**data)
subnets = calculate_vlsm(req.base_network,
    [SubnetRequest(name=s.name, required_hosts=s.required_hosts) for s in req.subnets])

config = {
    "devices": {"routers": 1, "switches": 1, "pcs": 3, "servers": 4},
    "routing_protocol": req.routing_protocol,
    "dhcp_from_router": req.dhcp_from_router,
    "dhcp_dns": req.dhcp_dns,
    "server_services": req.server_services,
    "servers_config": [srv.model_dump() for srv in req.servers_config],
    "topology": {},
}

res = save_pkt_file(subnets, config, output_dir="pkt_visual_test")

print("\n=== SERVER EMAIL ===")
for d in res["devices"]:
    if str(d.get("type","")).lower() == "server":
        svc = d.get("server_services", [])
        if "email" in svc:
            print(f"  mail_users: {d.get('mail_users', 'MANCANTE')}")
            print(f"  mail_domain: {d.get('mail_domain', 'MANCANTE')}")

print("\n=== PC MAIL CONFIG ===")
for d in res["devices"]:
    if str(d.get("type","")).lower() == "pc":
        print(f"  {d['name']}: mail_username={d.get('mail_username','NESSUNO')} mail_domain={d.get('mail_domain','NESSUNO')}")
