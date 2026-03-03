from app.services.pkt_generator.generator import PKTGenerator

gen = PKTGenerator()

devices_config = [
    {"name": "Router0", "type": "router-8port"},
    {"name": "Switch0", "type": "switch-24port"},
    {"name": "PC0", "type": "pc"},
]

links_config = [
    {"from": "Router0", "from_port": "FastEthernet0/0", "to": "Switch0", "to_port": "FastEthernet0/1"},
    {"from": "Switch0", "from_port": "FastEthernet0/2", "to": "PC0", "to_port": "FastEthernet0"},
]

gen.generate(
    devices_config=devices_config,
    links_config=links_config,
    output_path="test_router8_fix.pkt"
)
print("Generato: test_router8_fix.pkt")
