import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_generator.server_config import build_server_configs

devices = [{'name': 'Server0', 'type': 'server', 'ip': '192.168.0.2', 'subnet': '255.255.255.192', 'gateway_ip': '192.168.0.1'}]
servers_config_list = [{'services': ['dhcp','dns'], 'hostname': 'dhcp1.local', 'dhcp_pools': [{'name': 'serverPool'}, {'name': 'reteArancione'}]}]

build_server_configs(1, servers_config_list, [], devices)
print('dhcp_pools nel device:', devices[0].get('dhcp_pools'))
