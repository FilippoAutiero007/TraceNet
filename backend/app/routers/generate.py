"""
Generate router - API endpoints for network generation and .pkt file download
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from app.models.schemas import GenerateRequest, GenerateResponse, PktGenerateRequest, PktGenerateResponse
from app.models.manual_schemas import ManualNetworkRequest, ManualPktGenerateResponse
from app.services.nlp_parser import parse_network_description
from app.services.subnet_calculator import calculate_vlsm
from app.services.pkt_generator import generate_cisco_config
from app.services.pkt_file_generator import save_pkt_file
import os
from threading import Lock

# Global lock per proteggere generazione file .pkt (FIX B2: previene race condition)
_pkt_generation_lock = Lock()

router = APIRouter(tags=["generate"])

@router.post("/generate", response_model=GenerateResponse)
async def generate_network(request: GenerateRequest):
    """
    Generate Cisco network configuration from natural language description.
    
    Returns CLI configuration and subnet details (JSON response).
    For downloadable .pkt file, use /generate-pkt endpoint.
    """
    try:
        # Step 1: Parse natural language with Mistral AI
        network_config = await parse_network_description(request.description)
        
        if not network_config:
            return GenerateResponse(
                success=False,
                error="Could not parse network description. Please be more specific."
            )
        
        # Step 2: Calculate VLSM subnets
        subnets = calculate_vlsm(
            network_config.base_network,
            network_config.subnets
        )
        
        # Step 3: Generate Cisco CLI config
        cli_script = generate_cisco_config(network_config, subnets)
        
        return GenerateResponse(
            success=True,
            config_json=network_config,
            subnets=subnets,
            cli_script=cli_script
        )
        
    except ValueError as e:
        return GenerateResponse(
            success=False,
            error=f"Validation error: {str(e)}"
        )
    except Exception as e:
        return GenerateResponse(
            success=False,
            error=f"Generation failed: {str(e)}"
        )

@router.post("/generate-pkt", response_model=PktGenerateResponse)
async def generate_pkt_file(request: GenerateRequest):
    """
    Generate Cisco Packet Tracer .pkt file from natural language description.
    
    Returns:
    - pkt_path: Path to download the .pkt file
    - xml_path: Path to download the debug .xml file
    - download_url: URL to download the .pkt file
    
    Note: .pkt files are BINARY (XML compressed with GZIP), not text files!
    """
    try:
        # Step 1: Parse natural language with Mistral AI
        network_config = await parse_network_description(request.description)
        
        if not network_config:
            return PktGenerateResponse(
                success=False,
                error="Could not parse network description. Please be more specific."
            )
        
        # Step 2: Calculate VLSM subnets
        subnets = calculate_vlsm(
            network_config.base_network,
            network_config.subnets
        )
        
        # Step 3: Generate and Save Packet Tracer File
        # FIX B2: Lock per evitare race condition su scrittura file concorrente
        output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
        
        with _pkt_generation_lock:
            # Protegge save_pkt_file da accessi concorrenti
            result = save_pkt_file(subnets, network_config.model_dump(), output_dir)
        
        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))
        
        pkt_path = result["pkt_path"]
        xml_path = result["xml_path"]
        encoding_method = result["encoding_used"]
        file_size = result["file_size"]
        pka2xml_avail = result["pka2xml_available"]
        
        # Generate download URLs
        pkt_filename = os.path.basename(pkt_path)
        xml_filename = os.path.basename(xml_path)
        
        return PktGenerateResponse(
            success=True,
            message=f"✅ File .pkt generato con successo! (Encoding: {encoding_method})",
            pkt_path=pkt_path,
            xml_path=xml_path,
            pkt_download_url=f"/api/download/{pkt_filename}",
            xml_download_url=f"/api/download/{xml_filename}",
            config_summary={
                "base_network": network_config.base_network,
                "subnets_count": len(subnets),
                "routers": network_config.devices.routers,
                "switches": network_config.devices.switches,
                "pcs": network_config.devices.pcs,
                "routing_protocol": network_config.routing_protocol.value
            },
            subnets=[{
                "name": s.name,
                "network": s.network,
                "gateway": s.gateway,
                "usable_hosts": s.usable_hosts
            } for s in subnets]
        )
        
    except ValueError as e:
        return PktGenerateResponse(
            success=False,
            error=f"Validation error: {str(e)}"
        )
    except Exception as e:
        return PktGenerateResponse(
            success=False,
            error=f"PKT generation failed: {str(e)}"
        )

@router.post("/generate-pkt-manual", response_model=ManualPktGenerateResponse)
async def generate_pkt_file_manual(request: ManualNetworkRequest):
    """
    Generate Cisco Packet Tracer .pkt file from structured parameters (NO NLP parsing).
    
    This endpoint bypasses Mistral AI NLP parsing and accepts direct structured parameters.
    Ideal for automation, testing, and when you already know exact network requirements.
    
    Args:
        request: ManualNetworkRequest with base_network, subnets, devices, routing_protocol
    
    Returns:
        - pkt_path: Path to download the .pkt file
        - xml_path: Path to download the debug .xml file
        - download_url: URL to download the .pkt file
        - encoding_method: Method used for encryption (external_pka2xml or legacy_xor_fallback)
    
    Example:
        ```json
        {
            "base_network": "192.168.0.0/24",
            "subnets": [
                {"name": "Admin", "required_hosts": 20},
                {"name": "Guest", "required_hosts": 50}
            ],
            "devices": {
                "routers": 1,
                "switches": 2,
                "pcs": 70
            },
            "routing_protocol": "static"
        }
        ```
    """
    try:
        # Step 1: Calculate VLSM subnets (no NLP parsing needed)
        subnets = calculate_vlsm(
            request.base_network,
            request.subnets
        )
        
        # Step 2: Create network config dict for PKT generation
        network_config_dict = {
            "base_network": request.base_network,
            "subnets": [s.model_dump() for s in request.subnets],
            "devices": request.devices.model_dump(),
            "routing_protocol": request.routing_protocol.value,
            "XML_VERSION": "8.2.2.0400"  # Default PT version
        }
        
        # Step 3: Generate and Save Packet Tracer File
        output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
        
        with _pkt_generation_lock:
            result = save_pkt_file(subnets, network_config_dict, output_dir)
        
        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))
        
        pkt_path = result["pkt_path"]
        xml_path = result["xml_path"]
        encoding_method = result["encoding_used"]
        file_size = result["file_size"]
        pka2xml_avail = result["pka2xml_available"]
        
        # Generate download URLs
        pkt_filename = os.path.basename(pkt_path)
        xml_filename = os.path.basename(xml_path)
        
        return ManualPktGenerateResponse(
            success=True,
            message=f"✅ File .pkt generato con successo! (Encoding: {encoding_method}, Size: {file_size} bytes)",
            pkt_path=pkt_path,
            xml_path=xml_path,
            pkt_download_url=f"/api/download/{pkt_filename}",
            xml_download_url=f"/api/download/{xml_filename}",
            config_summary={
                "base_network": request.base_network,
                "subnets_count": len(subnets),
                "routers": request.devices.routers,
                "switches": request.devices.switches,
                "pcs": request.devices.pcs,
                "routing_protocol": request.routing_protocol.value
            },
            subnets=[{
                "name": s.name,
                "network": s.network,
                "gateway": s.gateway,
                "usable_hosts": s.usable_hosts
            } for s in subnets],
            encoding_method=encoding_method
        )
        
    except ValueError as e:
        return ManualPktGenerateResponse(
            success=False,
            error=f"Validation error: {str(e)}"
        )
    except Exception as e:
        return ManualPktGenerateResponse(
            success=False,
            error=f"PKT generation failed: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download generated .pkt or .xml file
    
    Args:
        filename: Name of file to download (e.g., network_20240101_120000.pkt)
    """
    output_dir = os.environ.get("OUTPUT_DIR", "/tmp/tracenet")
    filepath = os.path.join(output_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type
    if filename.endswith('.pkt'):
        media_type = "application/gzip"  # .pkt è GZIP
    elif filename.endswith('.xml'):
        media_type = "application/xml"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        filepath,
        media_type=media_type,
        filename=filename
    )

@router.get("/templates")
async def get_templates():
    """
    Get list of network configuration templates
    """
    templates = [
        {
            "name": "Small Office",
            "description": "Rete piccolo ufficio con 2 VLAN",
            "example": "Create network with VLAN Admin (10 hosts) and VLAN Guest (20 hosts) using static routing"
        },
        {
            "name": "Corporate Campus", 
            "description": "Campus aziendale multi-edificio",
            "example": "Network with 3 buildings: Building_A (100 hosts), Building_B (50 hosts), Building_C (25 hosts) using OSPF"
        },
        {
            "name": "Data Center",
            "description": "Rete data center con DMZ",
            "example": "Data center network with DMZ (5 servers), Production (50 hosts), Management (10 hosts) using EIGRP"
        },
        {
            "name": "School Network",
            "description": "Rete scolastica",
            "example": "School network with Labs (100 hosts), Teachers (30 hosts), Admin (10 hosts), Guests (50 hosts) using RIP"
        }
    ]
    
    return {
        "success": True,
        "templates": templates
    }
