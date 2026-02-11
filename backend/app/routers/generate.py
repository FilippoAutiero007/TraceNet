"""Generate router - parser endpoint + deterministic PKT generation endpoints."""

import os
from threading import Lock

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.manual_schemas import ManualNetworkRequest, ManualPktGenerateResponse
from app.models.schemas import (
    GenerateResponse,
    NetworkConfig,
    ParseNetworkRequest,
    ParseNetworkResponse,
    NormalizedNetworkRequest,
    PktGenerateResponse,
    RoutingProtocol,
    SubnetRequest,
    DeviceConfig,
)
from app.services.nlp_parser import parse_network_request
from app.services.pkt_file_generator import save_pkt_file
from app.services.pkt_generator import generate_cisco_config
from app.services.subnet_calculator import calculate_vlsm

_pkt_generation_lock = Lock()
router = APIRouter(tags=["generate"])


@router.post("/parse-network-request", response_model=ParseNetworkResponse)
async def parse_network_endpoint(request: ParseNetworkRequest):
    """LLM parser endpoint returning only strict intent + normalized JSON."""
    return await parse_network_request(request.user_input, request.current_state)


@router.post("/generate", response_model=GenerateResponse)
async def generate_network(request: NormalizedNetworkRequest):
    """Generate CLI configuration from normalized JSON only."""
    try:
        subnets_input = request.subnets or [SubnetRequest(name="LAN", required_hosts=max(request.pcs, 1))]
        network_config = NetworkConfig(
            base_network=request.base_network,
            subnets=subnets_input,
            devices=DeviceConfig(routers=request.routers, switches=request.switches, pcs=request.pcs),
            routing_protocol=RoutingProtocol(request.routing_protocol.lower() if request.routing_protocol == "STATIC" else request.routing_protocol),
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
        return GenerateResponse(success=False, error=f"Validation error: {exc}")
    except Exception as exc:
        return GenerateResponse(success=False, error=f"Generation failed: {exc}")


@router.post("/generate-pkt", response_model=PktGenerateResponse)
async def generate_pkt_file(request: NormalizedNetworkRequest):
    """Generate Packet Tracer .pkt from normalized JSON only (no free text)."""
    try:
        subnets_input = request.subnets or [SubnetRequest(name="LAN", required_hosts=max(request.pcs, 1))]
        protocol_value = "static" if request.routing_protocol == "STATIC" else request.routing_protocol

        network_config_dict = {
            "base_network": request.base_network,
            "subnets": [s.model_dump() for s in subnets_input],
            "devices": {"routers": request.routers, "switches": request.switches, "pcs": request.pcs},
            "routing_protocol": protocol_value,
            "XML_VERSION": "8.2.2.0400",
        }

        subnets = calculate_vlsm(request.base_network, subnets_input)

        output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
        with _pkt_generation_lock:
            result = save_pkt_file(subnets, network_config_dict, output_dir)

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        pkt_filename = os.path.basename(result["pkt_path"])
        xml_filename = os.path.basename(result["xml_path"])

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
                "routing_protocol": request.routing_protocol,
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
    except ValueError as exc:
        return PktGenerateResponse(success=False, error=f"Validation error: {exc}")
    except Exception as exc:
        return PktGenerateResponse(success=False, error=f"PKT generation failed: {exc}")


@router.post("/generate-pkt-manual", response_model=ManualPktGenerateResponse)
async def generate_pkt_file_manual(request: ManualNetworkRequest):
    """Generate Cisco Packet Tracer .pkt file from structured parameters."""
    try:
        subnets = calculate_vlsm(request.base_network, request.subnets)

        network_config_dict = {
            "base_network": request.base_network,
            "subnets": [s.model_dump() for s in request.subnets],
            "devices": request.devices.model_dump(),
            "routing_protocol": request.routing_protocol.value,
            "XML_VERSION": "8.2.2.0400",
        }

        output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
        with _pkt_generation_lock:
            result = save_pkt_file(subnets, network_config_dict, output_dir)

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

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
    except ValueError as exc:
        return ManualPktGenerateResponse(success=False, error=f"Validation error: {exc}")
    except Exception as exc:
        return ManualPktGenerateResponse(success=False, error=f"PKT generation failed: {exc}")


@router.get("/download/{filename}")
async def download_file(filename: str):
    output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    if filename.endswith(".pkt"):
        media_type = "application/gzip"
    elif filename.endswith(".xml"):
        media_type = "application/xml"
    else:
        media_type = "application/octet-stream"

    return FileResponse(filepath, media_type=media_type, filename=filename)


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
