"""
Pydantic models for NetTrace API
"""

import re
import ipaddress
from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RoutingProtocol(str, Enum):
    STATIC = "static"
    RIP = "RIP"
    OSPF = "OSPF"
    EIGRP = "EIGRP"


class SubnetRequest(BaseModel):
    """Request for a single subnet"""
    name: str = Field(..., min_length=1, max_length=64, description="Subnet name")
    required_hosts: int = Field(..., ge=1, le=16777214, description="Number of required hosts")
    dns_server: Optional[str] = Field(default=None, description="Optional DNS server IP for this subnet")

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
    servers: int = Field(default=0, ge=0)  


class NetworkConfig(BaseModel):
    """Parsed network configuration from NLP"""
    base_network: str = Field(..., description="Base network in CIDR notation")
    subnets: List[SubnetRequest] = Field(default_factory=list, max_length=10)
    devices: DeviceConfig = Field(default_factory=DeviceConfig)
    routing_protocol: RoutingProtocol = Field(default=RoutingProtocol.STATIC)
    dhcp_dns: Optional[str] = Field(default=None, description="Optional DNS server IP for router DHCP pools")

    @field_validator("base_network")
    @classmethod
    def validate_cidr(cls, value: str) -> str:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation: {e}")
        return value


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
    dns_server: Optional[str] = None


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
    dns_server: Optional[str] = Field(default=None, description="Optional DNS server IP for this subnet")


class TopologyConfig(BaseModel):
    """Optional topology hints for PKT link generation."""
    edge_routers: Optional[int] = Field(
        default=None,
        ge=0,
        description="Routers attached to LAN switches (default: auto)",
    )
    backbone_mode: str = Field(default="chain", description="Router backbone strategy: chain or full-mesh")
    gateway_position: str = Field(default="first", description="Gateway position: 'first' (default) or 'last'")
    wan_network: str = Field(
        default="11.0.0.0",
        description="Base network per i link WAN router-router (default classe A pubblica)",
    )
    wan_prefix: int = Field(
        default=30,
        ge=8,
        le=31,
        description="Prefix length per i link WAN (/30 di default, minimo spreco IP)",
    )

    @field_validator("backbone_mode")
    @classmethod
    def validate_backbone_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"chain", "full-mesh"}:
            raise ValueError("backbone_mode must be 'chain' or 'full-mesh'")
        return normalized

    @field_validator("gateway_position")
    @classmethod
    def validate_gateway_position(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"first", "last"}:
            raise ValueError("gateway_position must be 'first' or 'last'")
        return normalized

    @field_validator("wan_network")
    @classmethod
    def validate_wan_network(cls, value: str) -> str:
        import ipaddress

        try:
            ipaddress.ip_address(value.strip())
        except ValueError:
            raise ValueError(f"wan_network deve essere un indirizzo IP valido, ricevuto: {value!r}")
        return value.strip()


class VlanConfig(BaseModel):
    """Optional VLAN configuration for switches/router-on-a-stick (best-effort schema)."""
    id: int = Field(..., ge=1, le=4094, description="VLAN ID")
    name: Optional[str] = Field(default=None, description="VLAN name")

    model_config = ConfigDict(extra="allow")


class NatConfig(BaseModel):
    """Optional NAT configuration (best-effort schema)."""
    type: Literal["static", "dynamic", "pool", "pat", "overload"] = Field(..., description="NAT type")

    model_config = ConfigDict(extra="allow")


class AclRule(BaseModel):
    """Optional ACL rule entry (best-effort schema)."""
    action: Optional[str] = None
    line: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class AclConfig(BaseModel):
    """Optional ACL definition (best-effort schema)."""
    type: Literal["standard", "extended"] = Field(..., description="ACL type")
    id: Optional[str] = Field(default=None, description="Standard ACL number (e.g. '10')")
    name: Optional[str] = Field(default=None, description="Extended ACL name (e.g. 'BLOCK_WEB')")
    rules: List[AclRule] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ServerConfig(BaseModel):
    services: List[str] = Field(default_factory=list)
    hostname: str = Field(default="")
    ftp_user: Optional[str] = Field(default=None)
    ftp_password: Optional[str] = Field(default=None)
    ftp_users: Optional[list] = Field(default=None)
    dns_records: Optional[list] = Field(default=None)
    auto_dns_records: bool = Field(default=False)



class NormalizedNetworkRequest(BaseModel):  
    """Normalized payload accepted by /api/generate-pkt (no free text)."""
    base_network: str = Field(..., description="Base network in CIDR notation")
    routers: int = Field(..., ge=1)
    switches: int = Field(..., ge=0)
    pcs: int = Field(..., ge=1)
    servers: int = Field(default=0, ge=0)
    routing_protocol: str = Field(..., description="STATIC | RIP | OSPF | EIGRP")
    dhcp_from_router: bool = Field(default=False, description="Enable IOS DHCP pools on routers and set PCs as DHCP clients")
    dhcp_dns: Optional[str] = Field(default=None, description="Optional DNS server IP for router DHCP pools")
    server_services: List[str] = Field(default_factory=list, description="Services to enable on Server-PT (Packet Tracer XML)")
    servers_config: List[ServerConfig] = Field(default_factory=list)
    vlans: List[VlanConfig] = Field(default_factory=list, description="VLAN definitions for switches")
    nat: Optional[NatConfig] = Field(default=None, description="NAT configuration for routers")
    acl: List[AclConfig] = Field(default_factory=list, description="ACL configurations for routers")
    subnets: List[NormalizedSubnet] = Field(default_factory=list)
    topology: Optional[TopologyConfig] = Field(
        default=None,
        description="Optional topology hints for separating edge and backbone routers",
    )

    @field_validator("base_network")
    @classmethod
    def validate_cidr(cls, value: str) -> str:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation: {e}")
        return value

    @model_validator(mode="after")
    def validate_coherence(self):
        allowed_protocols = {"STATIC", "RIP", "OSPF", "EIGRP"}
        protocol = self.routing_protocol.strip().upper()
        if protocol not in allowed_protocols:
            raise ValueError(f"routing_protocol must be one of {sorted(allowed_protocols)}")
        self.routing_protocol = protocol

        # Normalize service names for downstream code (entrypoint/config_generator).
        if self.server_services:
            self.server_services = [str(s).strip().lower() for s in self.server_services if str(s).strip()]

        if self.servers_config:
            for srv in self.servers_config:
                if srv.services:
                    srv.services = [str(s).strip().lower() for s in srv.services if str(s).strip()]
                srv.hostname = str(srv.hostname or "").strip()

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
    error: Optional[str] = None

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
