from __future__ import annotations

import ipaddress
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


def _normalize_service_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [s.strip().lower() for s in value.split(",") if s.strip()]
    if isinstance(value, list):
        return [str(s).strip().lower() for s in value if str(s).strip()]
    return []


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
    required_hosts: Optional[int] = Field(default=None, ge=1)
    network: Optional[str] = Field(default=None, description="Optional explicit subnet in CIDR notation")
    gateway: Optional[str] = Field(default=None, description="Optional explicit default gateway for the subnet")
    site: Optional[str] = Field(default=None, description="Optional site/office label")
    dns_server: Optional[str] = Field(default=None, description="Optional DNS server IP for this subnet")

    @model_validator(mode="after")
    def validate_subnet_shape(self):
        if self.required_hosts is None and not self.network:
            raise ValueError("Subnet requires either required_hosts or network.")
        if self.network:
            try:
                ipaddress.ip_network(self.network, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid subnet network: {exc}") from exc
        if self.gateway:
            try:
                ipaddress.ip_address(self.gateway)
            except ValueError as exc:
                raise ValueError(f"Invalid subnet gateway: {exc}") from exc
        return self


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
    subnet_name: Optional[str] = Field(default=None, description="Associated logical subnet name")
    native: bool = Field(default=False, description="Whether this VLAN is native on trunks")

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
    mail_users: Optional[list] = Field(default=None)
    mail_domain: Optional[str] = Field(default=None)
    dns_records: Optional[list] = Field(default=None)
    dhcp_pools: Optional[list] = Field(default=None)
    auto_dns_records: bool = Field(default=False)

    @field_validator("services", mode="before")
    @classmethod
    def normalize_services(cls, value: Any) -> List[str]:
        return _normalize_service_list(value)

    model_config = ConfigDict(extra="allow")


class PcConfig(BaseModel):
    mail_user: Optional[str] = Field(default=None)
    mail_password: Optional[str] = Field(default=None)

    model_config = ConfigDict(extra="allow")


class NetworkSite(BaseModel):
    name: str = Field(..., min_length=1)
    base_network: Optional[str] = Field(default=None, description="Primary private network for the site in CIDR form")
    public_ip: Optional[str] = Field(default=None, description="Optional public IP exposed by the site/router")
    notes: Optional[str] = Field(default=None)

    @field_validator("base_network")
    @classmethod
    def validate_optional_site_cidr(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise ValueError(f"Invalid site base network: {exc}") from exc
        return value

    @field_validator("public_ip")
    @classmethod
    def validate_optional_public_ip(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        try:
            ipaddress.ip_address(value)
        except ValueError as exc:
            raise ValueError(f"Invalid public IP: {exc}") from exc
        return value


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
    pcs_config: List[PcConfig] = Field(default_factory=list)
    vlans: List[VlanConfig] = Field(default_factory=list, description="VLAN definitions for switches")
    nat: Optional[NatConfig] = Field(default=None, description="NAT configuration for routers")
    acl: List[AclConfig] = Field(default_factory=list, description="ACL configurations for routers")
    subnets: List[NormalizedSubnet] = Field(default_factory=list)
    network_sites: List[NetworkSite] = Field(default_factory=list, description="Optional multi-site network hints extracted from the prompt")
    requirements: List[str] = Field(default_factory=list, description="Free-form technical/security requirements extracted from the prompt")
    topology: Optional[TopologyConfig] = Field(
        default=None,
        description="Optional topology hints for separating edge and backbone routers",
    )

    @field_validator("server_services", mode="before")
    @classmethod
    def normalize_server_services(cls, value: Any) -> List[str]:
        return _normalize_service_list(value)

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

        if self.server_services:
            self.server_services = _normalize_service_list(self.server_services)

        if self.servers_config:
            for srv in self.servers_config:
                if srv.services:
                    srv.services = _normalize_service_list(srv.services)
                srv.hostname = str(srv.hostname or "").strip()

        return self


class ParseNetworkResponse(BaseModel):
    """Strict parser response contract for frontend orchestration."""
    intent: ParseIntent
    missing: List[str] = Field(default_factory=list)
    json_payload: Dict[str, Any] = Field(default_factory=dict, alias="json", serialization_alias="json")
    suggested_defaults: Dict[str, Any] = Field(
        default_factory=dict,
        alias="suggestedDefaults",
        serialization_alias="suggestedDefaults",
    )
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
    error_code: Optional[str] = None
    request_id: Optional[str] = None


class PktAnalysisIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    title: str
    message: str
    device: Optional[str] = None
    interface: Optional[str] = None
    suggestion: Optional[str] = None


class PktReviewResult(BaseModel):
    source: Literal["mistral", "fallback"]
    exercise_context_provided: bool = False
    overview: str
    things_correct: List[str] = Field(default_factory=list)
    things_to_fix: List[str] = Field(default_factory=list)
    alignment_with_exercise: Optional[str] = None


class PktAnalysisResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    summary: Optional[str] = None
    report: Optional[str] = None
    device_count: int = 0
    link_count: int = 0
    issue_count: int = 0
    issues: List[PktAnalysisIssue] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)
    review: Optional[PktReviewResult] = None
    exercise_text: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None


class UserCapabilitiesResponse(BaseModel):
    is_authenticated: bool
    user_id: Optional[str] = None
    plan: Optional[str] = None
    plan_scope: Optional[Literal["u", "o"]] = None
    is_pro: bool = False
    can_use_pro_pkt_review: bool = False
    weekly_generation_limit: Optional[int] = None
    weekly_generation_used: int = 0
    weekly_generation_remaining: Optional[int] = None


class RoutingProtocol(str, Enum):
    STATIC = "static"
    RIP = "rip"
    OSPF = "ospf"
    EIGRP = "eigrp"


class SubnetRequest(BaseModel):
    name: str = Field(..., min_length=1)
    required_hosts: Optional[int] = Field(default=None, ge=1)
    network: Optional[str] = Field(default=None)
    gateway: Optional[str] = Field(default=None)
    site: Optional[str] = Field(default=None)
    dns_server: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_request_shape(self):
        if self.required_hosts is None and not self.network:
            raise ValueError("Subnet requires either required_hosts or network.")
        if self.network:
            try:
                ipaddress.ip_network(self.network, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid subnet network: {exc}") from exc
        if self.gateway:
            try:
                ipaddress.ip_address(self.gateway)
            except ValueError as exc:
                raise ValueError(f"Invalid subnet gateway: {exc}") from exc
        return self


class DeviceConfig(BaseModel):
    routers: int = Field(..., ge=1)
    switches: int = Field(..., ge=0)
    pcs: int = Field(..., ge=1)


class NetworkConfig(BaseModel):
    base_network: str = Field(..., description="Base network in CIDR notation")
    subnets: List[SubnetRequest] = Field(..., min_length=1)
    devices: DeviceConfig
    routing_protocol: RoutingProtocol
    dhcp_dns: Optional[str] = None


class SubnetResult(BaseModel):
    name: str
    network: str
    mask: str
    gateway: str
    usable_range: List[str]
    broadcast: str
    total_hosts: int
    usable_hosts: int
    dns_server: Optional[str] = None


class GenerateResponse(BaseModel):
    success: bool
    config_json: Optional[Union[NormalizedNetworkRequest, NetworkConfig, Dict[str, Any]]] = None
    subnets: Optional[Union[List[SubnetResult], List[Dict[str, Any]]]] = None
    cli_script: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
