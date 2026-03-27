import sys
sys.path.insert(0, r'C:\Users\pippo\OneDrive\Desktop\TraceNet\backend')
from app.services.pkt_generator.layout_scenarios import choose_layout_scenario
import json

# Simula la configurazione del test
devices = [
    {"name": "Router0", "type": "router"},
    {"name": "Switch0", "type": "switch"},
    {"name": "Switch1", "type": "switch"},
    {"name": "Server0", "type": "server"},
    {"name": "PC0", "type": "pc"},
    {"name": "PC1", "type": "pc"},
    {"name": "PC2", "type": "pc"},
    {"name": "PC3", "type": "pc"},
]
links = [
    {"source": "Router0", "target": "Switch0"},
    {"source": "Router0", "target": "Switch1"},
    {"source": "Switch0", "target": "Server0"},
    {"source": "Switch0", "target": "PC0"},
    {"source": "Switch0", "target": "PC2"},
    {"source": "Switch1", "target": "PC1"},
    {"source": "Switch1", "target": "PC3"},
]

scenario = choose_layout_scenario(devices, links)
print("Scenario scelto:", scenario)
