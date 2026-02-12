"""
Pydantic models for NetTrace API
"""

from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RoutingProtocol(str, Enum):
    STATIC = "static"
    RIP = "RIP"
    OSPF = "OSPF"
    EIGRP = "EIGRP"


class SubnetRequest(BaseModel):
    """Request for a single subnet"""
    name: str = Field(..., min_length=1, max_length=64, description="Subnet name")
    required_hosts: int = Field(..., ge=1, le=4094, description="Number of required hosts")

    @field_validator("name")
    @classmethod
    def validate_subnet_name(cls, value: str) -> str:
        if not re.match(r"^[A-Za-z0-9_-]+$", value):
            raise ValueError("Subnet name must contain only letters, numbers, underscore or dash")
        return value



class DeviceConfig(BaseModel):
    """Device configuration"""
    routers: int = Field(default=1, ge=1, le=5)
    switches: int = Field(default=1, ge=0, le=10)
    pcs: int = Field(default=1, ge=1, le=100)



class NetworkConfig(BaseModel):
    """Parsed network configuration from NLP"""
    base_network: str = Field(..., description="Base network in CIDR notation")
    subnets: List[SubnetRequest] = Field(default_factory=list, max_length=10)
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


class PktGenerateRequest(BaseModel):
    """Request body for legacy /api/generate-pkt endpoint"""
    description: str = Field(..., min_length=10, description="Natural language network description")


class ParseIntent(str, Enum):
    NOT_NETWORK = "not_network"
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"


class ParseNetworkRequest(BaseModel):
    """Request body for /api/parse-network-request endpoint"""
    user_input: str = Field(..., min_length=1, description="User natural language input")
    current_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Already collected conversation fields"
    )


class NormalizedSubnet(BaseModel):
    """Normalized subnet entry used by backend generation."""
    name: str = Field(..., min_length=1)
    required_hosts: int = Field(..., ge=1)


class NormalizedNetworkRequest(BaseModel):
    """Normalized payload accepted by /api/generate-pkt (no free text)."""
    base_network: str = Field(..., description="Base network in CIDR notation")
    routers: int = Field(..., ge=1)
    switches: int = Field(..., ge=0)
    pcs: int = Field(..., ge=1)
    routing_protocol: str = Field(..., description="STATIC | RIP | OSPF | EIGRP")
    subnets: List[NormalizedSubnet] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_coherence(self):
        allowed_protocols = {"STATIC", "RIP", "OSPF", "EIGRP"}
        protocol = self.routing_protocol.strip().upper()
        if protocol not in allowed_protocols:
            raise ValueError(f"routing_protocol must be one of {sorted(allowed_protocols)}")
        self.routing_protocol = protocol

        if self.subnets:
            total_subnet_hosts = sum(subnet.required_hosts for subnet in self.subnets)
            if total_subnet_hosts < self.pcs:
                raise ValueError(
                    "Total subnet required_hosts must be >= pcs for coherent host allocation"
                )
        return self


class ParseNetworkResponse(BaseModel):
    """Strict parser response contract for frontend orchestration."""
    intent: ParseIntent
    missing: List[str] = Field(default_factory=list)
    json_payload: Dict[str, Any] = Field(default_factory=dict, alias="json", serialization_alias="json")

    model_config = ConfigDict(populate_by_name=True)

class PktGenerateResponse(BaseModel):
    """Response from /api/generate-pkt endpoint with .pkt file info"""
    success: bool
    message: Optional[str] = None
    pkt_path: Optional[str] = None
    xml_path: Optional[str] = None
    pkt_download_url: Optional[str] = None
    xml_download_url: Optional[str] = None
    config_summary: Optional[Dict[str, Any]] = None
    subnets: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
