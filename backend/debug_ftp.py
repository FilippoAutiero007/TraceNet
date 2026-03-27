import json
from pathlib import Path
from app.services.pkt_generator.entrypoint import save_pkt_file
from app.models.schemas import NormalizedNetworkRequest, SubnetRequest
from app.services.subnet_calculator import calculate_vlsm

data = json.loads(Path("dhcp_bug_request.json").read_text("utf-8-sig"))

# Usa il body completo con FTP users
data2 = {
  "base_network": "192.168.1.0/24",
  "routers": 1, "switches": 1, "pcs": 3, "servers": 4,
  "routing_protocol": "STATIC", "dhcp_from_router": False,
  "server_services": [],
  "servers_config": [
    {"services": ["dns"], "hostname": "dns1.local", "dns_records": [{"hostname": "amazon.com", "ip": "15.2.2.2"}]},
    {"services": ["http"], "hostname": "web1.local"},
    {"services": ["ftp"], "hostname": "ftp1.local", "ftp_users": [
      {"username": "user1", "password": "pass1", "permissions": "rw"},
      {"username": "user2", "password": "pass2", "permissions": "rw"}
    ]},
    {"services": ["dhcp"], "hostname": "dhcp1.local"}
  ],
  "subnets": [{"name": "LAN1", "required_hosts": 30}]
}

req = NormalizedNetworkRequest(**data2)
subnets_input = [SubnetRequest(name=s.name, required_hosts=s.required_hosts) for s in req.subnets]
subnets = calculate_vlsm(req.base_network, subnets_input)

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

print("\n=== SERVER DEVICES DOPO BUILD ===")
for d in res["devices"]:
    if str(d.get("type", "")).lower() == "server":
        print(f"\n{d['name']}:")
        print(f"  services:  {d.get('server_services', [])}")
        print(f"  ftp_users: {d.get('ftp_users', 'MANCANTE')}")
        print(f"  ftp_user:  {d.get('ftp_user', 'MANCANTE')}")
