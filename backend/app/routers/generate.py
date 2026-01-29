"""
Generate router - API endpoint for network generation
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateRequest, GenerateResponse
from app.services.nlp_parser import parse_network_description
from app.services.subnet_calculator import calculate_vlsm
from app.services.pkt_generator import generate_cisco_config

router = APIRouter(tags=["generate"])

@router.post("/generate", response_model=GenerateResponse)
async def generate_network(request: GenerateRequest):
    """
    Generate Cisco network configuration from natural language description.
    
    Flow:
    1. Parse natural language with LLM
    2. Calculate VLSM subnets
    3. Generate Cisco CLI config
    """
    try:
        # Step 1: Parse natural language
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
