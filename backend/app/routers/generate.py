"""Generate router - parser endpoint + deterministic PKT generation endpoints."""

import os
import re
import shutil
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.models.manual_schemas import ManualNetworkRequest, ManualPktGenerateResponse
from app.models.schemas import (
    DeviceConfig,
    GenerateResponse,
    NetworkConfig,
    NormalizedNetworkRequest,
    ParseNetworkRequest,
    ParseNetworkResponse,
    PktGenerateResponse,
    RoutingProtocol,
    SubnetRequest,
)
from app.services.nlp_parser import parse_network_request
from app.services.pkt_file_generator import get_template_path, save_pkt_file
from app.services.pkt_generator import generate_cisco_config
from app.services.subnet_calculator import calculate_vlsm
from app.utils.logger import setup_logger
from app.utils.rate_limiter import limiter

logger = setup_logger("tracenet.router")

_REQUEST_LOCKS: dict[str, Lock] = defaultdict(Lock)
_LOCKS_CLEANUP_LOCK = Lock()
FILENAME_REGEX = re.compile(r"^[\w\-.]+$")

router = APIRouter(tags=["generate"])


def get_request_lock(request_id: str) -> Lock:
    with _LOCKS_CLEANUP_LOCK:
        return _REQUEST_LOCKS[request_id]


def release_request_lock(request_id: str):
    with _LOCKS_CLEANUP_LOCK:
        if request_id in _REQUEST_LOCKS:
            del _REQUEST_LOCKS[request_id]


def cleanup_old_files(ttl_seconds: int = 3600):
    output_dir = str(settings.output_dir)
    if not os.path.exists(output_dir):
        return

    cutoff_time = time.time() - ttl_seconds
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        try:
            if os.path.getmtime(item_path) < cutoff_time:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        except Exception as exc:
            logger.warning("Failed to cleanup %s: %s", item_path, exc)


def _validate_filename(filename: str):
    decoded = unquote(filename)
    if not FILENAME_REGEX.fullmatch(decoded):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if '..' in decoded or '/' in decoded or '\\' in decoded:
        raise HTTPException(status_code=400, detail="Invalid filename")


def _resolve_safe_path(output_dir: Path, filename: str) -> Path:
    decoded = unquote(filename)
    _validate_filename(decoded)
    filepath = (output_dir / decoded).resolve()
    try:
        filepath.relative_to(output_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Access denied") from exc
    return filepath


def _to_network_config(request: NormalizedNetworkRequest) -> tuple[NetworkConfig, list[SubnetRequest]]:
    subnets_input = request.subnets or [SubnetRequest(name="LAN", required_hosts=max(request.pcs, 1))]
    routing = RoutingProtocol.STATIC if request.routing_protocol == "STATIC" else RoutingProtocol(request.routing_protocol)
    config = NetworkConfig(
        base_network=request.base_network,
        subnets=subnets_input,
        devices=DeviceConfig(routers=request.routers, switches=request.switches, pcs=request.pcs),
        routing_protocol=routing,
    )
    return config, subnets_input


@router.post("/parse-network-request", response_model=ParseNetworkResponse)
@limiter.limit("30/minute")
async def parse_network_endpoint(http_request: Request, request: ParseNetworkRequest):
    del http_request
    return await parse_network_request(request.user_input, request.current_state)


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit("20/minute")
async def generate_network(http_request: Request, request: NormalizedNetworkRequest):
    del http_request
    try:
        network_config, _ = _to_network_config(request)
        subnets = calculate_vlsm(network_config.base_network, network_config.subnets)
        cli_script = generate_cisco_config(network_config, subnets)
        return GenerateResponse(success=True, config_json=network_config, subnets=subnets, cli_script=cli_script)
    except ValueError as exc:
        return GenerateResponse(success=False, error=f"Validation error: {exc}")
    except Exception as exc:
        return GenerateResponse(success=False, error=f"Generation failed: {exc}")


@router.post("/generate-pkt", response_model=PktGenerateResponse)
@limiter.limit(settings.max_requests_per_minute)
async def generate_pkt_file(
    http_request: Request,
    request: NormalizedNetworkRequest,
    background_tasks: BackgroundTasks,
):
    del http_request
    request_id = str(uuid.uuid4())
    lock = get_request_lock(request_id)

    try:
        _, subnets_input = _to_network_config(request)
        protocol_value = "static" if request.routing_protocol == "STATIC" else request.routing_protocol
        network_config_dict = {
            "base_network": request.base_network,
            "subnets": [s.model_dump() for s in subnets_input],
            "devices": {"routers": request.routers, "switches": request.switches, "pcs": request.pcs},
            "routing_protocol": protocol_value,
            "XML_VERSION": "8.2.2.0400",
        }
        subnets = calculate_vlsm(request.base_network, subnets_input)

        output_base = str(settings.output_dir)
        output_dir = os.path.join(output_base, request_id)

        with lock:
            os.makedirs(output_dir, exist_ok=True)
            result = save_pkt_file(subnets, network_config_dict, output_dir)

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        pkt_filename = os.path.basename(result["pkt_path"])
        xml_filename = os.path.basename(result["xml_path"])

        background_tasks.add_task(cleanup_old_files)

        return PktGenerateResponse(
            success=True,
            message=f"✅ File .pkt generato con successo! (Encoding: {result['encoding_used']})",
            pkt_path=result["pkt_path"],
            xml_path=result["xml_path"],
            pkt_download_url=f"/api/download/{request_id}/{pkt_filename}",
            xml_download_url=f"/api/download/{request_id}/{xml_filename}",
            config_summary={
                "base_network": request.base_network,
                "subnets_count": len(subnets),
                "routers": request.routers,
                "switches": request.switches,
                "pcs": request.pcs,
                "routing_protocol": request.routing_protocol,
            },
            subnets=[
                {"name": s.name, "network": s.network, "gateway": s.gateway, "usable_hosts": s.usable_hosts}
                for s in subnets
            ],
        )
    except ValueError as exc:
        return PktGenerateResponse(success=False, error=f"Validation error: {exc}")
    except Exception as exc:
        return PktGenerateResponse(success=False, error=f"PKT generation failed: {exc}")
    finally:
        release_request_lock(request_id)


@router.post("/generate-pkt-manual", response_model=ManualPktGenerateResponse)
@limiter.limit("10/minute")
async def generate_pkt_file_manual(
    http_request: Request,
    request: ManualNetworkRequest,
    background_tasks: BackgroundTasks,
):
    del http_request
    request_id = str(uuid.uuid4())
    lock = get_request_lock(request_id)

    try:
        subnets = calculate_vlsm(request.base_network, request.subnets)
        network_config_dict = {
            "base_network": request.base_network,
            "subnets": [s.model_dump() for s in request.subnets],
            "devices": request.devices.model_dump(),
            "routing_protocol": request.routing_protocol.value,
            "XML_VERSION": "8.2.2.0400",
        }

        output_base = str(settings.output_dir)
        output_dir = os.path.join(output_base, request_id)

        with lock:
            os.makedirs(output_dir, exist_ok=True)
            result = save_pkt_file(subnets, network_config_dict, output_dir)

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        pkt_filename = os.path.basename(result["pkt_path"])
        xml_filename = os.path.basename(result["xml_path"])

        background_tasks.add_task(cleanup_old_files)

        return ManualPktGenerateResponse(
            success=True,
            message=f"✅ File .pkt generato con successo! (Encoding: {result['encoding_used']}, Size: {result['file_size']} bytes)",
            pkt_path=result["pkt_path"],
            xml_path=result["xml_path"],
            pkt_download_url=f"/api/download/{request_id}/{pkt_filename}",
            xml_download_url=f"/api/download/{request_id}/{xml_filename}",
            config_summary={
                "base_network": request.base_network,
                "subnets_count": len(subnets),
                "routers": request.devices.routers,
                "switches": request.devices.switches,
                "pcs": request.devices.pcs,
                "routing_protocol": request.routing_protocol.value,
            },
            subnets=[
                {"name": s.name, "network": s.network, "gateway": s.gateway, "usable_hosts": s.usable_hosts}
                for s in subnets
            ],
            encoding_method=result["encoding_used"],
        )
    except ValueError as exc:
        return ManualPktGenerateResponse(success=False, error=f"Validation error: {exc}")
    except Exception as exc:
        return ManualPktGenerateResponse(success=False, error=f"PKT generation failed: {exc}")
    finally:
        release_request_lock(request_id)


@router.get("/download/{request_id}/{filename}")
async def download_file(request_id: str, filename: str):
    _validate_filename(request_id)
    output_dir = settings.output_dir / request_id

    filepath = _resolve_safe_path(output_dir, filename)

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if filename.endswith(".pkt"):
        media_type = "application/gzip"
    elif filename.endswith(".xml"):
        media_type = "application/xml"
    else:
        media_type = "application/octet-stream"

    return FileResponse(str(filepath), media_type=media_type, filename=filename)


@router.get("/health")
async def health_check_router():
    checks = {"status": "healthy", "timestamp": datetime.now().isoformat(), "checks": {}}

    output_dir = str(settings.output_dir)
    try:
        os.makedirs(output_dir, exist_ok=True)
        test_file = os.path.join(output_dir, ".health_check")
        with open(test_file, "w", encoding="utf-8") as file_handle:
            file_handle.write("ok")
        os.remove(test_file)
        checks["checks"]["filesystem"] = "ok"
    except Exception as exc:
        checks["checks"]["filesystem"] = f"error: {exc}"
        checks["status"] = "degraded"

    try:
        get_template_path()
        checks["checks"]["template"] = "ok"
    except FileNotFoundError:
        checks["checks"]["template"] = "missing"
        checks["status"] = "unhealthy"

    checks["checks"]["mistral_api"] = "ok" if settings.mistral_api_key else "no_key"

    status_code = 200 if checks["status"] == "healthy" else 503
    return JSONResponse(content=checks, status_code=status_code)


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
