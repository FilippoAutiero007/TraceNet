"""
Pydantic models for manual PKT generation (structured parameters)
Bypasses NLP parsing for deterministic, fast generation
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.schemas import (
    AclConfig,
    NatConfig,
    RoutingProtocol,
    DeviceConfig,
    PcConfig,
    ServerConfig,
    SubnetRequest,
    TopologyConfig,
    VlanConfig,
)


class ManualNetworkRequest(BaseModel):
    """
    Request body for /api/generate-pkt-manual endpoint
    Accepts structured parameters directly without NLP parsing
    """
    base_network: str = Field(
        ..., 
        description="Base network in CIDR notation (e.g., '192.168.0.0/24')",
        examples=["192.168.0.0/24", "10.0.0.0/16"]
    )
    subnets: List[SubnetRequest] = Field(
        ...,
        description="List of subnets with name and required hosts",
        min_length=1
    )
    devices: DeviceConfig = Field(
        default_factory=DeviceConfig,
        description="Device configuration (routers, switches, PCs)"
    )
    routing_protocol: RoutingProtocol = Field(
        default=RoutingProtocol.STATIC,
        description="Routing protocol to use"
    )
    dhcp_from_router: bool = Field(
        default=False,
        description="Enable router-based DHCP pools instead of dedicated DHCP server",
    )
    dhcp_dns: Optional[str] = Field(
        default=None,
        description="Optional DNS server IP for DHCP pools",
    )
    server_services: Optional[List[str]] = Field(default=None, description="Services to enable on server (dns, http, dhcp, ftp...)")
    servers_config: Optional[List[ServerConfig]] = Field(
        default=None,
        description="Per-server configuration (services, hostname, dns_records, dhcp_pools, mail users...)",
    )
    vlans: Optional[List[VlanConfig]] = Field(
        default=None,
        description="VLAN definitions for switches/router-on-a-stick",
    )
    acl: Optional[List[AclConfig]] = Field(
        default=None,
        description="ACL definitions for routers",
    )
    nat: Optional[NatConfig] = Field(
        default=None,
        description="NAT configuration for routers",
    )
    pcs_config: Optional[List[PcConfig]] = Field(
        default=None,
        description="Per-PC configuration (mail credentials, etc.)",
    )
    dns_records: Optional[List[dict]] = Field(default=None, description="DNS A records for DNS server")
    topology: Optional[TopologyConfig] = Field(
        default=None,
        description="Optional topology hints for edge/backbone router links"
    )


class ManualPktGenerateResponse(BaseModel):
    """
    Response from /api/generate-pkt-manual endpoint
    Same format as PktGenerateResponse for consistency
    """
    success: bool
    message: Optional[str] = None
    pkt_path: Optional[str] = None
    xml_path: Optional[str] = None
    pkt_download_url: Optional[str] = None
    xml_download_url: Optional[str] = None
    config_summary: Optional[dict] = None
    subnets: Optional[List[dict]] = None
    error: Optional[str] = None
    encoding_method: Optional[str] = Field(
        None,
        description="Encoding method used (external_pka2xml or legacy_xor_fallback)"
    )
