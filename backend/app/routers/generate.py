"""Generate router - parser endpoint + deterministic PKT generation endpoints."""

import os
import logging
import ipaddress
from time import perf_counter
from threading import Lock

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.models.manual_schemas import ManualNetworkRequest, ManualPktGenerateResponse
from app.models.schemas import (
    GenerateResponse,
    NetworkConfig,
    ParseNetworkRequest,
    ParseNetworkResponse,
    ParseIntent,
    NormalizedNetworkRequest,
    PktGenerateResponse,
    PktAnalysisResponse,
    UserCapabilitiesResponse,
    RoutingProtocol,
    SubnetRequest,
    DeviceConfig,
)
from app.services.auth import AuthContext, get_optional_auth_context, require_pro_user
from app.services.generation_quota import consume_generation_quota, get_generation_quota_status
from app.services.nlp_parser import ParserServiceError, parse_network_request
from app.services.pkt_analyzer import analyze_pkt_bytes
from app.services.pkt_generator import save_pkt_file
from app.services.pkt_generator import generate_cisco_config
from app.services.subnet_calculator import calculate_vlsm
from app.services.pkt_review import review_pkt_analysis
from app.utils.errors import api_error, get_request_id

_pkt_generation_lock = Lock()
logger = logging.getLogger(__name__)
router = APIRouter(tags=["generate"])


def _default_subnet_for_base(base_network: str) -> SubnetRequest:
    """Use the full base network when no explicit subnets are provided."""
    net = ipaddress.ip_network(base_network, strict=False)
    if net.num_addresses < 4:
        raise ValueError(
            f"Base network {base_network} is too small to auto-create a default LAN subnet. "
            "Use a network with at least 4 addresses (/30 or larger)."
        )
    usable_hosts = max(1, int(net.num_addresses) - 2)
    return SubnetRequest(name="LAN", required_hosts=usable_hosts)


def _build_pkt_network_config_dict(
    request: NormalizedNetworkRequest,
    subnets_input: list[SubnetRequest],
    protocol_value: str,
) -> dict:
    return {
        "base_network": request.base_network,
        "subnets": [s.model_dump() for s in subnets_input],
        "devices": {
            "routers": request.routers,
            "switches": request.switches,
            "pcs": request.pcs,
            "servers": getattr(request, "servers", 0),
        },
        "routing_protocol": protocol_value,
        "dhcp_from_router": getattr(request, "dhcp_from_router", False),
        "dhcp_dns": getattr(request, "dhcp_dns", None),
        "server_services": request.server_services or [],
        "servers_config": [s.model_dump() for s in request.servers_config] if request.servers_config else [],
        "vlans": [v.model_dump() for v in getattr(request, "vlans", []) or []],
        "nat": request.nat.model_dump() if getattr(request, "nat", None) else None,
        "acl": [a.model_dump() for a in getattr(request, "acl", []) or []],
        "XML_VERSION": "8.2.2.0400",
        "topology": request.topology.model_dump() if request.topology else None,
        "dns_records": [],
    }


def _validate_filename(filename: str) -> str:
    """Path traversal guard for downloadable filenames."""
    import re

    if not re.match(r"^[\w\-\.]+$", filename):
        raise api_error(400, "SEC_INVALID_FILENAME", "Invalid filename.")

    if ".." in filename or "/" in filename or "\\" in filename:
        raise api_error(400, "SEC_INVALID_FILENAME", "Invalid filename.")

    return filename


@router.post("/parse-network-request", response_model=ParseNetworkResponse)
async def parse_network_endpoint(request: ParseNetworkRequest):
    """LLM parser endpoint returning only strict intent + normalized JSON."""
    started_at = perf_counter()
    try:
        response = await parse_network_request(request.user_input, request.current_state)
        logger.info(
            "parse-network-request completed",
            extra={
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                "intent": response.intent.value,
                "missing": response.missing,
            },
        )
        return response
    except ParserServiceError as exc:
        logger.error("Parse network request failed: %s", exc, exc_info=True)
        raise api_error(502, "PARSER_BACKEND_FAILURE", "Parser service unavailable.") from exc


@router.post("/generate", response_model=GenerateResponse)
async def generate_network(request: NormalizedNetworkRequest, http_request: Request):
    """Generate CLI configuration from normalized JSON only."""
    try:
        # Ensure protocol normalization stays consistent with schema expectations.
        protocol = request.routing_protocol.strip().upper()
        subnets_input = request.subnets or [_default_subnet_for_base(request.base_network)]
        network_config = NetworkConfig(
            base_network=request.base_network,
            subnets=subnets_input,
            devices=DeviceConfig(routers=request.routers, switches=request.switches, pcs=request.pcs),
            routing_protocol=RoutingProtocol(protocol if protocol != "STATIC" else "static"),
            dhcp_dns=request.dhcp_dns,
        )

        subnets = calculate_vlsm(network_config.base_network, network_config.subnets)
        cli_script = generate_cisco_config(network_config, subnets)

        return GenerateResponse(
            success=True,
            config_json=network_config,
            subnets=subnets,
            cli_script=cli_script,
        )
    except ValueError as exc:
        logger.warning("Network generation validation failed", extra={"request": request.model_dump(), "request_id": get_request_id(http_request)}, exc_info=True)
        return GenerateResponse(
            success=False,
            error="Invalid network generation request.",
            error_code="SEC_INVALID_SCHEMA",
            request_id=get_request_id(http_request),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Network generation failed", extra={"request": request.model_dump(), "request_id": get_request_id(http_request)}, exc_info=True)
        return GenerateResponse(
            success=False,
            error="Network generation failed.",
            error_code="GENERATION_FAILED",
            request_id=get_request_id(http_request),
        )


@router.post("/generate-pkt", response_model=PktGenerateResponse)
async def generate_pkt_file(
    request: NormalizedNetworkRequest,
    http_request: Request,
    auth: AuthContext | None = Depends(get_optional_auth_context),
):
    """Generate Packet Tracer .pkt from normalized JSON only (no free text)."""
    started_at = perf_counter()
    try:
        consume_generation_quota(auth, http_request)
        after_quota = perf_counter()
        subnets_input = request.subnets or [_default_subnet_for_base(request.base_network)]
        protocol_value = "static" if request.routing_protocol == "STATIC" else request.routing_protocol

        network_config_dict = _build_pkt_network_config_dict(request, subnets_input, protocol_value)

        subnets = calculate_vlsm(request.base_network, subnets_input)
        after_vlsm = perf_counter()

        output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
        os.makedirs(output_dir, exist_ok=True)
        
        # Lock con timeout per evitare deadlock (max 30 secondi)
        acquired = _pkt_generation_lock.acquire(timeout=30)
        if not acquired:
            logger.warning("PKT generation lock timeout after 30s")
            return PktGenerateResponse(
                success=False,
                error="Server busy. Please retry in a few seconds.",
                error_code="GENERATION_BUSY",
                request_id=get_request_id(http_request),
            )
        
        try:
            result = save_pkt_file(subnets, network_config_dict, output_dir)
        finally:
            _pkt_generation_lock.release()
        after_generation = perf_counter()

        if not result.get("success"):
            raise Exception(result.get("error", "Unknown error during PKT file save"))

        pkt_filename = os.path.basename(result["pkt_path"])
        xml_filename = os.path.basename(result["xml_path"])

        logger.info(
            "generate-pkt completed",
            extra={
                "duration_ms": round((after_generation - started_at) * 1000, 2),
                "quota_ms": round((after_quota - started_at) * 1000, 2),
                "vlsm_ms": round((after_vlsm - after_quota) * 1000, 2),
                "pkt_generation_ms": round((after_generation - after_vlsm) * 1000, 2),
                "routers": request.routers,
                "switches": request.switches,
                "pcs": request.pcs,
                "subnets_count": len(subnets),
                "encoding_used": result.get("encoding_used"),
            },
        )

        return PktGenerateResponse(
            success=True,
            message=f"✅ File .pkt generato con successo! (Encoding: {result['encoding_used']})",
            pkt_path=result["pkt_path"],
            xml_path=result["xml_path"],
            pkt_download_url=f"/api/download/{pkt_filename}",
            xml_download_url=f"/api/download/{xml_filename}",
            config_summary={
                "base_network": request.base_network,
                "subnets_count": len(subnets),
                "routers": request.routers,
                "switches": request.switches,
                "pcs": request.pcs,
                "routing_protocol": protocol_value,
            },
            subnets=[
                {
                    "name": s.name,
                    "network": s.network,
                    "gateway": s.gateway,
                    "usable_hosts": s.usable_hosts,
                }
                for s in subnets
            ],
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("PKT generation validation failed", extra={"request": request.model_dump(), "request_id": get_request_id(http_request)}, exc_info=True)
        return PktGenerateResponse(
            success=False,
            error="Invalid PKT generation request.",
            error_code="SEC_INVALID_SCHEMA",
            request_id=get_request_id(http_request),
        )
    except Exception as exc:
        logger.error("PKT generation failed", extra={"request": request.model_dump(), "request_id": get_request_id(http_request)}, exc_info=True)
        return PktGenerateResponse(
            success=False,
            error="PKT generation failed.",
            error_code="GENERATION_FAILED",
            request_id=get_request_id(http_request),
        )


@router.post("/generate-pkt-manual", response_model=ManualPktGenerateResponse)
async def generate_pkt_file_manual(
    request: ManualNetworkRequest,
    http_request: Request,
    auth: AuthContext | None = Depends(get_optional_auth_context),
):
    """Generate Cisco Packet Tracer .pkt file from structured parameters."""
    try:
        consume_generation_quota(auth, http_request)
        subnets = calculate_vlsm(request.base_network, request.subnets)

        network_config_dict = {
            "base_network": request.base_network,
            "subnets": [s.model_dump() for s in request.subnets],
            "devices": request.devices.model_dump(),
            "routing_protocol": request.routing_protocol.value,
            "dhcp_from_router": bool(getattr(request, "dhcp_from_router", False)),
            "dhcp_dns": getattr(request, "dhcp_dns", None),
            "nat": request.nat.model_dump() if getattr(request, "nat", None) else None,
            "XML_VERSION": "8.2.2.0400",
            "topology": request.topology.model_dump() if request.topology else None,
            "dns_records": request.dns_records or [],
            "server_services": request.server_services or [],
            "servers_config": [s.model_dump() for s in (request.servers_config or [])],
            "vlans": [v.model_dump() for v in (request.vlans or [])],
            "acl": [a.model_dump() for a in (request.acl or [])],
            "pcs_config": [p.model_dump() for p in (request.pcs_config or [])],
        }

        output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
        os.makedirs(output_dir, exist_ok=True)
        
        # Lock con timeout per evitare deadlock (max 30 secondi)
        acquired = _pkt_generation_lock.acquire(timeout=30)
        if not acquired:
            logger.warning("Manual PKT generation lock timeout after 30s")
            return ManualPktGenerateResponse(
                success=False,
                error="Server busy. Please retry in a few seconds.",
                error_code="GENERATION_BUSY",
                request_id=get_request_id(http_request),
            )
        
        try:
            result = save_pkt_file(subnets, network_config_dict, output_dir)
        finally:
            _pkt_generation_lock.release()

        if not result.get("success"):
            raise Exception(result.get("error", "Unknown error during manual PKT file save"))

        pkt_filename = os.path.basename(result["pkt_path"])
        xml_filename = os.path.basename(result["xml_path"])

        return ManualPktGenerateResponse(
            success=True,
            message=f"✅ File .pkt generato con successo! (Encoding: {result['encoding_used']}, Size: {result['file_size']} bytes)",
            pkt_path=result["pkt_path"],
            xml_path=result["xml_path"],
            pkt_download_url=f"/api/download/{pkt_filename}",
            xml_download_url=f"/api/download/{xml_filename}",
            config_summary={
                "base_network": request.base_network,
                "subnets_count": len(subnets),
                "routers": request.devices.routers,
                "switches": request.devices.switches,
                "pcs": request.devices.pcs,
                "routing_protocol": request.routing_protocol.value,
            },
            subnets=[
                {
                    "name": s.name,
                    "network": s.network,
                    "gateway": s.gateway,
                    "usable_hosts": s.usable_hosts,
                }
                for s in subnets
            ],
            encoding_method=result["encoding_used"],
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("Manual PKT generation validation failed", extra={"request": request.model_dump(), "request_id": get_request_id(http_request)}, exc_info=True)
        return ManualPktGenerateResponse(
            success=False,
            error="Invalid PKT generation request.",
            error_code="SEC_INVALID_SCHEMA",
            request_id=get_request_id(http_request),
        )
    except Exception as exc:
        logger.error("Manual PKT generation failed", extra={"request": request.model_dump(), "request_id": get_request_id(http_request)}, exc_info=True)
        return ManualPktGenerateResponse(
            success=False,
            error="PKT generation failed.",
            error_code="GENERATION_FAILED",
            request_id=get_request_id(http_request),
        )


@router.post("/analyze-pkt", response_model=PktAnalysisResponse)
async def analyze_pkt_file(
    file: UploadFile = File(...),
    exercise_text: str | None = Form(default=None),
    _auth: AuthContext = Depends(require_pro_user),
):
    """Analyze an uploaded Packet Tracer file and return a Pro diagnostic report."""
    filename = file.filename or "network.pkt"
    if not filename.lower().endswith(".pkt"):
        raise api_error(400, "SEC_INVALID_FILE_TYPE", "Only .pkt files are supported.")

    # Enforcement of 10MB limit (DoS mitigation)
    limit = 10 * 1024 * 1024
    pkt_data = await file.read(limit + 1)
    if len(pkt_data) > limit:
        raise api_error(413, "SEC_FILE_TOO_LARGE", "File size exceeds 10MB limit.")

    if not pkt_data:
        raise api_error(400, "SEC_INVALID_FILE", "Uploaded file is empty.")

    analysis = analyze_pkt_bytes(pkt_data, filename=filename)
    analysis.exercise_text = exercise_text
    if analysis.success:
        analysis.review = review_pkt_analysis(analysis, exercise_text)
    return analysis


@router.get("/me/capabilities", response_model=UserCapabilitiesResponse)
async def get_user_capabilities(
    request: Request,
    auth: AuthContext | None = Depends(get_optional_auth_context),
):
    """Return the authenticated user's current feature capabilities."""
    quota = get_generation_quota_status(auth, request)
    if auth is None:
        return UserCapabilitiesResponse(
            is_authenticated=False,
            is_pro=False,
            can_use_pro_pkt_review=False,
            weekly_generation_limit=quota.limit,
            weekly_generation_used=quota.used,
            weekly_generation_remaining=quota.remaining,
        )

    return UserCapabilitiesResponse(
        is_authenticated=True,
        user_id=auth.user_id,
        plan=auth.plan,
        plan_scope=auth.plan_scope if auth.plan_scope in {"u", "o"} else None,
        is_pro=auth.is_pro,
        can_use_pro_pkt_review=auth.is_pro,
        weekly_generation_limit=quota.limit,
        weekly_generation_used=quota.used,
        weekly_generation_remaining=quota.remaining,
    )


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated .pkt or .xml file with path traversal protection"""
    from pathlib import Path
    
    _validate_filename(filename)
    
    output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
    filepath = Path(output_dir) / filename
    
    try:
        if not filepath.resolve().is_relative_to(Path(output_dir).resolve()):
            raise api_error(403, "SEC_ACCESS_DENIED", "Access denied.")
    except ValueError:
        raise api_error(403, "SEC_ACCESS_DENIED", "Access denied.")
    
    if not filepath.exists():
        raise api_error(404, "FILE_NOT_FOUND", "File not found.")

    if filename.endswith(".pkt"):
        media_type = "application/gzip"
    elif filename.endswith(".xml"):
        media_type = "application/xml"
    else:
        media_type = "application/octet-stream"

    return FileResponse(path=str(filepath), media_type=media_type, filename=filename)


@router.get("/templates")
async def get_templates():
    templates = [
        {
            "name": "Small Office",
            "description": "Rete piccolo ufficio con 2 VLAN",
            "example": "Create network with VLAN Admin (10 hosts) and VLAN Guest (20 hosts) using static routing",
        },
        {
            "name": "Corporate Campus",
            "description": "Campus aziendale multi-edificio",
            "example": "Network with 3 buildings: Building_A (100 hosts), Building_B (50 hosts), Building_C (25 hosts) using OSPF",
        },
        {
            "name": "Data Center",
            "description": "Rete data center con DMZ",
            "example": "Data center network with DMZ (5 servers), Production (50 hosts), Management (10 hosts) using EIGRP",
        },
        {
            "name": "School Network",
            "description": "Rete scolastica",
            "example": "School network with Labs (100 hosts), Teachers (30 hosts), Admin (10 hosts), Guests (50 hosts) using RIP",
        },
    ]

    return {"success": True, "templates": templates}
