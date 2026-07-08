"""Generate router - parser endpoint + deterministic PKT generation endpoints."""

import ipaddress
import logging
import os
import re
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
    SubnetResult,
    SubnetRequest,
    DeviceConfig,
)
from app.services.auth import AuthContext, get_optional_auth_context
from app.services.generation_quota import consume_generation_quota, get_generation_quota_status
from app.services.nlp_parser import ParserServiceError, parse_network_request
from app.services.pkt_analyzer import analyze_pkt_bytes
from app.services.analysis_pdf import build_analysis_pdf_bytes
from app.services.pkt_generator import save_pkt_file
from app.services.pkt_generator import generate_cisco_config
from app.services.subnet_calculator import calculate_vlsm
from app.services.pkt_review import review_pkt_analysis
from app.utils.errors import api_error, get_request_id

_pkt_generation_lock = Lock()
logger = logging.getLogger(__name__)
router = APIRouter(tags=["generate"])


def _finalize_pkt_analysis(pkt_data: bytes, filename: str, exercise_text: str | None) -> PktAnalysisResponse:
    analysis = analyze_pkt_bytes(pkt_data, filename=filename)
    analysis.exercise_text = exercise_text
    if analysis.success:
        analysis.review = review_pkt_analysis(analysis, exercise_text)
    return analysis


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


def _subnet_result_from_explicit(request: SubnetRequest) -> SubnetResult:
    if not request.network:
        raise ValueError(f"Subnet '{request.name}' is missing an explicit network.")

    network = ipaddress.ip_network(request.network, strict=False)
    if network.num_addresses < 4:
        raise ValueError(f"Explicit subnet '{request.name}' is too small for Packet Tracer generation.")

    gateway_ip = request.gateway or str(network.network_address + 1)
    try:
        ipaddress.ip_address(gateway_ip)
    except ValueError as exc:
        raise ValueError(f"Invalid explicit gateway for subnet '{request.name}': {exc}") from exc

    usable_start = network.network_address + 2
    usable_end = network.broadcast_address - 1
    return SubnetResult(
        name=request.name,
        network=str(network),
        mask=str(network.netmask),
        gateway=gateway_ip,
        usable_range=[str(usable_start), str(usable_end)],
        broadcast=str(network.broadcast_address),
        total_hosts=network.num_addresses,
        usable_hosts=max(0, network.num_addresses - 2),
        dns_server=request.dns_server,
    )


def _resolve_generation_subnets(
    base_network: str,
    subnets_input: list[SubnetRequest],
) -> list[SubnetResult]:
    if subnets_input and all(getattr(subnet, "network", None) for subnet in subnets_input):
        return [_subnet_result_from_explicit(subnet) for subnet in subnets_input]
    return calculate_vlsm(base_network, subnets_input)


def _build_pkt_network_config_dict(
    plan: dict[str, object],
) -> dict:
    return {
        "base_network": plan["base_network"],
        "subnets": [s.model_dump() for s in plan["subnets_input"]],
        "devices": {
            "routers": plan["routers"],
            "switches": plan["switches"],
            "pcs": plan["pcs"],
            "servers": plan["servers"],
        },
        "routing_protocol": plan["routing_protocol_output"],
        "dhcp_from_router": plan["dhcp_from_router"],
        "dhcp_dns": plan["dhcp_dns"],
        "server_services": plan["server_services"],
        "servers_config": plan["servers_config"],
        "network_sites": plan["network_sites"],
        "requirements": plan["requirements"],
        "vlans": plan["vlans"],
        "nat": plan["nat"],
        "acl": plan["acl"],
        "pcs_config": plan["pcs_config"],
        "XML_VERSION": "8.2.2.0400",
        "topology": plan["topology"],
        "dns_records": [],
    }


def _requirement_flag(requirements: list[str], pattern: str) -> bool:
    return any(re.search(pattern, requirement, re.IGNORECASE) for requirement in requirements)


def _normalize_site_slug(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name.strip().upper()).strip("_") or "SITE"


def _derive_site_subnets(
    base_network: str,
    network_sites: list[dict[str, object]],
    requirements: list[str],
    subnet_hints: dict[str, int],
) -> list[SubnetRequest]:
    if not network_sites:
        return []

    derived: list[SubnetRequest] = []
    supplemental_pool = ipaddress.ip_network("10.255.250.0/24")
    supplemental_iter = supplemental_pool.subnets(new_prefix=29)
    needs_bologna_split = _requirement_flag(requirements, r"marketing") or _requirement_flag(requirements, r"technical|tecnic")

    for site in network_sites:
        site_name = str(site.get("name", "")).strip() or "Site"
        slug = _normalize_site_slug(site_name)
        site_cidr = str(site.get("base_network", "") or "").strip()
        site_network = ipaddress.ip_network(site_cidr, strict=False) if site_cidr else None

        if slug == "BOLOGNA" and site_network is not None and needs_bologna_split and site_network.prefixlen <= 24:
            split_prefix = min(max(site_network.prefixlen + 2, 26), 28)
            split_networks = list(site_network.subnets(new_prefix=split_prefix))
            labels = ["TECH_FLOOR1", "TECH_FLOOR2", "MARKETING", "SERVERS"]
            for idx, label in enumerate(labels):
                if idx >= len(split_networks):
                    break
                derived.append(
                    SubnetRequest(
                        name=f"{slug}_{label}",
                        network=str(split_networks[idx]),
                        site=site_name,
                    )
                )
            continue

        if site_network is None:
            site_network = next(supplemental_iter)
        elif site_network.prefixlen < 24:
            site_network = next(site_network.subnets(new_prefix=24))

        derived.append(
            SubnetRequest(
                name=f"{slug}_{'REMOTE' if slug == 'MONDRAGONE' else 'LAN'}",
                network=str(site_network),
                site=site_name,
            )
        )

    if not derived:
        return []

    if not any("MARKETING" in subnet.name for subnet in derived) and "MARKETING" in subnet_hints:
        derived.append(
            SubnetRequest(
                name="MARKETING",
                required_hosts=subnet_hints["MARKETING"],
            )
        )

    return derived


def _assign_server_subnets(servers_config: list[dict[str, object]], derived_subnets: list[SubnetRequest]) -> list[dict[str, object]]:
    subnet_names = {subnet.name: subnet for subnet in derived_subnets}
    bologna_servers = next((subnet.name for subnet in derived_subnets if subnet.name.endswith("_SERVERS")), None)
    firenze_dc = next((subnet.name for subnet in derived_subnets if subnet.name.startswith("FIRENZE")), None)
    marketing = next((subnet.name for subnet in derived_subnets if "MARKETING" in subnet.name), None)

    enriched: list[dict[str, object]] = []
    for server in servers_config:
        updated = dict(server)
        services = {str(service).strip().lower() for service in updated.get("services", [])}
        if updated.get("subnet_name") in subnet_names:
            enriched.append(updated)
            continue
        if "dhcp" in services and marketing:
            updated["subnet_name"] = marketing
            updated["site"] = "Bologna"
        elif {"dns", "http", "web"}.intersection(services) and firenze_dc:
            updated["subnet_name"] = firenze_dc
            updated["site"] = "Firenze"
        elif {"email", "smtp", "pop3"}.intersection(services):
            updated["subnet_name"] = bologna_servers or firenze_dc
            updated["site"] = "Bologna" if bologna_servers else "Firenze"
        enriched.append(updated)
    return enriched


def _build_semantic_pcs_config(
    total_pcs: int,
    derived_subnets: list[SubnetRequest],
    original_hints: dict[str, int],
) -> list[dict[str, object]]:
    if total_pcs <= 0 or not derived_subnets:
        return []

    pcs_config: list[dict[str, object]] = []
    marketing_subnet = next((subnet.name for subnet in derived_subnets if "MARKETING" in subnet.name), None)
    mondragone_subnet = next((subnet.name for subnet in derived_subnets if "MONDRAGONE" in subnet.name), None)
    tech_subnets = [subnet.name for subnet in derived_subnets if "TECH" in subnet.name]

    marketing_count = min(original_hints.get("MARKETING", 0), total_pcs) if marketing_subnet else 0
    mondragone_count = min(original_hints.get("MONDRAGONE", 0), max(0, total_pcs - marketing_count)) if mondragone_subnet else 0

    for _ in range(marketing_count):
        pcs_config.append({"subnet_name": marketing_subnet})
    for _ in range(mondragone_count):
        pcs_config.append({"subnet_name": mondragone_subnet})

    remaining = total_pcs - len(pcs_config)
    fallback_subnets = tech_subnets or [subnet.name for subnet in derived_subnets]
    for idx in range(remaining):
        pcs_config.append({"subnet_name": fallback_subnets[idx % len(fallback_subnets)]})
    return pcs_config


def _build_generation_plan(request: NormalizedNetworkRequest | ManualNetworkRequest) -> dict[str, object]:
    subnets_input = list(request.subnets or [])
    subnet_hints: dict[str, int] = {}
    for subnet in subnets_input:
        subnet_name = str(getattr(subnet, "name", "")).strip().upper()
        required_hosts = getattr(subnet, "required_hosts", None)
        if subnet_name and isinstance(required_hosts, int):
            subnet_hints[subnet_name] = required_hosts

    requirements = [str(item) for item in (getattr(request, "requirements", []) or [])]
    network_sites = [site.model_dump() if hasattr(site, "model_dump") else dict(site) for site in (getattr(request, "network_sites", []) or [])]
    servers_config = [cfg.model_dump() if hasattr(cfg, "model_dump") else dict(cfg) for cfg in (getattr(request, "servers_config", []) or [])]
    pcs_config = [cfg.model_dump() if hasattr(cfg, "model_dump") else dict(cfg) for cfg in (getattr(request, "pcs_config", []) or [])]
    server_services = list(getattr(request, "server_services", []) or [])
    vlans = [cfg.model_dump() if hasattr(cfg, "model_dump") else dict(cfg) for cfg in (getattr(request, "vlans", []) or [])]
    acl = [cfg.model_dump() if hasattr(cfg, "model_dump") else dict(cfg) for cfg in (getattr(request, "acl", []) or [])]
    nat = getattr(request, "nat", None)
    nat_dict = nat.model_dump() if hasattr(nat, "model_dump") else nat
    topology = getattr(request, "topology", None)
    topology_dict = topology.model_dump() if hasattr(topology, "model_dump") else topology

    derived_subnets = subnets_input
    if not derived_subnets and network_sites:
        derived_subnets = _derive_site_subnets(request.base_network, network_sites, requirements, subnet_hints)
    if not derived_subnets:
        derived_subnets = [_default_subnet_for_base(request.base_network)]

    if isinstance(request, ManualNetworkRequest):
        routers_count = int(request.devices.routers)
        switches_count = int(request.devices.switches)
        pcs_count = int(request.devices.pcs)
        servers_count = int(getattr(request.devices, "servers", 0) or 0)
        routing_protocol_value = request.routing_protocol.value
    else:
        routers_count = int(request.routers)
        switches_count = int(request.switches)
        pcs_count = int(request.pcs)
        servers_count = int(getattr(request, "servers", 0) or 0)
        routing_protocol_value = str(request.routing_protocol)

    if servers_config:
        servers_config = _assign_server_subnets(servers_config, derived_subnets)
    if not pcs_config:
        pcs_config = _build_semantic_pcs_config(pcs_count, derived_subnets, subnet_hints)

    routers = max(routers_count, len(network_sites) or routers_count)
    switches = max(switches_count, len(derived_subnets) or switches_count)
    servers = max(servers_count, len(servers_config), len(server_services))

    if nat_dict is None and _requirement_flag(requirements, r"nat/pat|nat"):
        nat_dict = {"type": "pat", "acl": "10"}

    return {
        "base_network": request.base_network,
        "subnets_input": derived_subnets,
        "routers": routers,
        "switches": switches,
        "pcs": pcs_count,
        "servers": servers,
        "routing_protocol": routing_protocol_value,
        "routing_protocol_output": "static" if str(routing_protocol_value).upper() == "STATIC" else str(routing_protocol_value),
        "dhcp_from_router": bool(getattr(request, "dhcp_from_router", False)),
        "dhcp_dns": getattr(request, "dhcp_dns", None),
        "server_services": server_services,
        "servers_config": servers_config,
        "pcs_config": pcs_config,
        "network_sites": network_sites,
        "requirements": requirements,
        "vlans": vlans,
        "nat": nat_dict,
        "acl": acl,
        "topology": topology_dict,
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
        plan = _build_generation_plan(request)
        # Ensure protocol normalization stays consistent with schema expectations.
        protocol = str(plan["routing_protocol"]).strip().upper()
        subnets_input = plan["subnets_input"]
        network_config = NetworkConfig(
            base_network=str(plan["base_network"]),
            subnets=subnets_input,
            devices=DeviceConfig(routers=int(plan["routers"]), switches=int(plan["switches"]), pcs=int(plan["pcs"])),
            routing_protocol=RoutingProtocol(protocol if protocol != "STATIC" else "static"),
            dhcp_dns=plan["dhcp_dns"],
        )

        subnets = _resolve_generation_subnets(network_config.base_network, network_config.subnets)
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
        plan = _build_generation_plan(request)
        consume_generation_quota(auth, http_request)
        after_quota = perf_counter()
        subnets_input = plan["subnets_input"]

        network_config_dict = _build_pkt_network_config_dict(plan)

        subnets = _resolve_generation_subnets(str(plan["base_network"]), subnets_input)
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
                "routers": plan["routers"],
                "switches": plan["switches"],
                "pcs": plan["pcs"],
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
                "base_network": plan["base_network"],
                "subnets_count": len(subnets),
                "routers": plan["routers"],
                "switches": plan["switches"],
                "pcs": plan["pcs"],
                "routing_protocol": plan["routing_protocol_output"],
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
        plan = _build_generation_plan(request)
        consume_generation_quota(auth, http_request)
        subnets = _resolve_generation_subnets(str(plan["base_network"]), plan["subnets_input"])

        network_config_dict = _build_pkt_network_config_dict(plan)
        network_config_dict["dns_records"] = request.dns_records or []

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
                "base_network": plan["base_network"],
                "subnets_count": len(subnets),
                "routers": plan["routers"],
                "switches": plan["switches"],
                "pcs": plan["pcs"],
                "routing_protocol": plan["routing_protocol_output"],
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
):
    """Analyze an uploaded Packet Tracer file."""
    filename = file.filename or "network.pkt"
    if not filename.lower().endswith(".pkt"):
        raise api_error(400, "SEC_INVALID_FILE_TYPE", "Only .pkt files are supported.")

    # Prevent memory exhaustion (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise api_error(413, "SEC_FILE_TOO_LARGE", "File size exceeds 10MB limit.")

    pkt_data = await file.read()
    if not pkt_data:
        raise api_error(400, "SEC_INVALID_FILE", "Uploaded file is empty.")

    return _finalize_pkt_analysis(pkt_data, filename, exercise_text)


@router.post("/analyze-pkt-report")
async def analyze_pkt_file_report(
    file: UploadFile = File(...),
    exercise_text: str | None = Form(default=None),
):
    """Analyze an uploaded Packet Tracer file and return a PDF report."""
    filename = file.filename or "network.pkt"
    if not filename.lower().endswith(".pkt"):
        raise api_error(400, "SEC_INVALID_FILE_TYPE", "Only .pkt files are supported.")

    # Prevent memory exhaustion (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise api_error(413, "SEC_FILE_TOO_LARGE", "File size exceeds 10MB limit.")

    pkt_data = await file.read()
    if not pkt_data:
        raise api_error(400, "SEC_INVALID_FILE", "Uploaded file is empty.")

    analysis = _finalize_pkt_analysis(pkt_data, filename, exercise_text)
    pdf_bytes = build_analysis_pdf_bytes(analysis)
    safe_stem = os.path.splitext(os.path.basename(filename))[0] or "network"
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_stem}_analysis_report.pdf"',
    }
    from fastapi.responses import Response

    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


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
