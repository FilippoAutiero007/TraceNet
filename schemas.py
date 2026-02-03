from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class RoutingProtocol(str, Enum):
    STATIC = "static"
    RIP = "rip"
    OSPF = "ospf"
    EIGRP = "eigrp"

class SubnetRequest(BaseModel):
    name: str
    required_hosts: int

class DeviceCount(BaseModel):
    routers: int = 1
    switches: int = 1
    pcs: int = 0
    servers: int = 0

class NetworkConfig(BaseModel):
    base_network: str = "192.168.0.0/16"
    subnets: List[SubnetRequest] = []
    devices: DeviceCount = Field(default_factory=DeviceCount)
    routing_protocol: RoutingProtocol = RoutingProtocol.STATIC

class SubnetResult(BaseModel):
    name: str
    network: str
    mask: str
    gateway: str
    usable_range: List[str]
    broadcast: str
    total_hosts: int
    usable_hosts: int
