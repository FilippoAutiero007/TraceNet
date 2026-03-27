from app.services.pkt_generator.config_generator import calculate_static_routes


def test_calculate_static_routes_router_chain_basic():
    all_devices = [
        {
            "name": "Router0",
            "type": "router-2port",
            "interfaces": [
                {"name": "FastEthernet0/0", "ip": "192.168.10.1", "mask": "255.255.255.0", "role": "lan"},
                {"name": "FastEthernet1/0", "ip": "11.0.0.1", "mask": "255.255.255.252", "role": "wan"},
            ],
        },
        {
            "name": "Router1",
            "type": "router-3port",
            "interfaces": [
                {"name": "FastEthernet0/0", "ip": "192.168.20.1", "mask": "255.255.255.0", "role": "lan"},
                {"name": "FastEthernet1/0", "ip": "11.0.0.2", "mask": "255.255.255.252", "role": "wan"},
                {"name": "FastEthernet2/0", "ip": "11.0.0.5", "mask": "255.255.255.252", "role": "wan"},
            ],
        },
        {
            "name": "Router2",
            "type": "router-2port",
            "interfaces": [
                {"name": "FastEthernet0/0", "ip": "192.168.30.1", "mask": "255.255.255.0", "role": "lan"},
                {"name": "FastEthernet1/0", "ip": "11.0.0.6", "mask": "255.255.255.252", "role": "wan"},
            ],
        },
    ]
    links = [
        {"from": "Router0", "to": "Router1", "from_port": "FastEthernet1/0", "to_port": "FastEthernet1/0"},
        {"from": "Router1", "to": "Router2", "from_port": "FastEthernet2/0", "to_port": "FastEthernet1/0"},
    ]

    r0_routes = calculate_static_routes("Router0", all_devices, links)
    assert {"network": "192.168.20.0", "mask": "255.255.255.0", "next_hop": "11.0.0.2"} in r0_routes
    assert {"network": "192.168.30.0", "mask": "255.255.255.0", "next_hop": "11.0.0.2"} in r0_routes


def test_calculate_static_routes_works_even_when_interface_roles_missing():
    all_devices = [
        {
            "name": "Router0",
            "type": "router-2port",
            "interfaces": [
                {"name": "FastEthernet0/0", "ip": "192.168.10.1", "mask": "255.255.255.0"},
                {"name": "FastEthernet1/0", "ip": "11.0.0.1", "mask": "255.255.255.252"},
            ],
        },
        {
            "name": "Router1",
            "type": "router-2port",
            "interfaces": [
                {"name": "FastEthernet0/0", "ip": "192.168.20.1", "mask": "255.255.255.0"},
                {"name": "FastEthernet1/0", "ip": "11.0.0.2", "mask": "255.255.255.252"},
            ],
        },
    ]
    links = [
        {"from": "Router0", "to": "Router1", "from_port": "FastEthernet1/0", "to_port": "FastEthernet1/0"},
    ]

    r0_routes = calculate_static_routes("Router0", all_devices, links)
    assert {"network": "192.168.20.0", "mask": "255.255.255.0", "next_hop": "11.0.0.2"} in r0_routes

