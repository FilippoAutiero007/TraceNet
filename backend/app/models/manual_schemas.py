"""
Pydantic models for manual PKT generation (structured parameters)
Bypasses NLP parsing for deterministic, fast generation
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.schemas import RoutingProtocol, DeviceConfig, SubnetRequest


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
