import time
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Callable

@dataclass
class Packet:
    id: str
    source: str
    destination: str
    protocol: str
    size: int
    timestamp: float

@dataclass
class SimulationState:
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    active_packets: List[Dict[str, Any]]
    timestamp: float

class NetworkSimulation:
    def __init__(self, topology_type: str = "mesh"):
        self.topology_type = topology_type
        self.nodes = {}
        self.links = []
        self.handlers = {}
        self.packets = []

    def add_node(self, node_id: str, node_type: str = "router"):
        self.nodes[node_id] = {"id": node_id, "type": node_type}
        self._trigger_event("on_node_added", self.nodes[node_id])

    def add_link(self, from_node: str, to_node: str, **kwargs):
        link = {"from": from_node, "to": to_node, "params": kwargs}
        self.links.append(link)
        self._trigger_event("on_link_added", link)

    def send_packet(self, packet: Packet):
        self.packets.append(packet)
        self._trigger_event("on_packet_sent", asdict(packet))

    def simulate_step(self) -> SimulationState:
        # Basic simulation logic: move packets or process events
        current_time = time.time()
        state = SimulationState(
            nodes=list(self.nodes.values()),
            links=self.links,
            active_packets=[asdict(p) for p in self.packets],
            timestamp=current_time
        )
        return state

    def export_state(self) -> dict:
        return asdict(self.simulate_step())

    def register_handler(self, event: str, callback: Callable):
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(callback)

    def _trigger_event(self, event: str, data: Any):
        if event in self.handlers:
            for handler in self.handlers[event]:
                handler(data)

if __name__ == "__main__":
    sim = NetworkSimulation()
    sim.add_node("A", "host")
    sim.add_node("B", "router")
    sim.add_link("A", "B", bandwidth=100, delay=10)
    
    p = Packet("p1", "A", "B", "TCP", 64, time.time())
    sim.send_packet(p)
    
    print(json.dumps(sim.export_state(), indent=2))
