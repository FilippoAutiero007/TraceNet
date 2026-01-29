"""
Pydantic models for NetTrace API
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class RoutingProtocol(str, Enum):
    STATIC = "static"
    RIP = "RIP"
    OSPF = "OSPF"
    EIGRP = "EIGRP"

class SubnetRequest(BaseModel):
    """Request for a single subnet"""
    name: str = Field(..., description="Subnet name")
    required_hosts: int = Field(..., ge=1, description="Number of required hosts")

class DeviceConfig(BaseModel):
    """Device configuration"""
    routers: int = Field(default=0, ge=0)
    switches: int = Field(default=0, ge=0)
    pcs: int = Field(default=0, ge=0)

class NetworkConfig(BaseModel):
    """Parsed network configuration from NLP"""
    base_network: str = Field(..., description="Base network in CIDR notation")
    subnets: List[SubnetRequest] = Field(default_factory=list)
    devices: DeviceConfig = Field(default_factory=DeviceConfig)
    routing_protocol: RoutingProtocol = Field(default=RoutingProtocol.STATIC)

class SubnetResult(BaseModel):
    """Calculated subnet result"""
    name: str
    network: str
    mask: str
    gateway: str
    usable_range: List[str]
    broadcast: str
    total_hosts: int
    usable_hosts: int

class GenerateRequest(BaseModel):
    """Request body for /api/generate endpoint"""
    description: str = Field(..., min_length=10, description="Natural language network description")

class GenerateResponse(BaseModel):
    """Response from /api/generate endpoint"""
    success: bool
    config_json: Optional[NetworkConfig] = None
    subnets: Optional[List[SubnetResult]] = None
    cli_script: Optional[str] = None
    error: Optional[str] = None
