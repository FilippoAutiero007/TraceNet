"""
NLP Parser Service - Uses Mistral AI to parse natural language network descriptions
"""

import os
import json
from mistralai import Mistral
from app.models.schemas import NetworkConfig, SubnetRequest, DeviceConfig, RoutingProtocol

SYSTEM_PROMPT = """You are a network configuration parser. Extract structured data from natural language network descriptions.

Return ONLY valid JSON with this exact structure:
{
  "base_network": "X.X.X.X/XX",
  "subnets": [
    {"name": "Subnet-1", "required_hosts": 50}
  ],
  "devices": {"routers": 1, "switches": 2, "pcs": 10},
  "routing_protocol": "static"
}

Rules:
- base_network: Use CIDR notation (e.g., "192.168.1.0/24"). Default: "192.168.0.0/16"
- subnets: Array of objects with name and required_hosts (extract from VLAN names, building names, etc.)
- devices: Count of each device type mentioned (routers, switches, pcs)
- routing_protocol: One of "static", "RIP", "OSPF", "EIGRP" (default: static)
- Extract numbers from text (e.g., "cinquanta host" → 50, "50 hosts" → 50)
- If not specified, use sensible defaults
- ALWAYS return valid JSON, nothing else

Examples:
Input: "Crea rete con VLAN Sales 50 host e IT 30 host, usa OSPF"
Output: {"base_network":"192.168.0.0/16","subnets":[{"name":"Sales","required_hosts":50},{"name":"IT","required_hosts":30}],"devices":{"routers":1,"switches":2,"pcs":80},"routing_protocol":"OSPF"}

Input: "Network with 3 buildings: A (100 hosts), B (50 hosts), C (25 hosts)"
Output: {"base_network":"192.168.0.0/16","subnets":[{"name":"Building_A","required_hosts":100},{"name":"Building_B","required_hosts":50},{"name":"Building_C","required_hosts":25}],"devices":{"routers":3,"switches":3,"pcs":175},"routing_protocol":"static"}"""

async def parse_network_description(description: str) -> NetworkConfig | None:
    """
    Parse natural language network description using Mistral AI.
    
    Args:
        description: Natural language description of the network
        
    Returns:
        NetworkConfig object or None if parsing fails
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not configured. Set MISTRAL_API_KEY in .env file.")
    
    client = Mistral(api_key=api_key)
    
    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse this network description:\n\n{description}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        # Build NetworkConfig from parsed data
        subnets = [
            SubnetRequest(name=s.get("name", f"Subnet-{i+1}"), required_hosts=s.get("required_hosts", 10))
            for i, s in enumerate(data.get("subnets", []))
        ]
        
        # Default subnet if none specified
        if not subnets:
            subnets = [SubnetRequest(name="LAN", required_hosts=30)]
        
        devices_data = data.get("devices", {})
        devices = DeviceConfig(
            routers=max(1, devices_data.get("routers", 1)),
            switches=max(1, devices_data.get("switches", 1)),
            pcs=devices_data.get("pcs", 0)
        )
        
        protocol_str = data.get("routing_protocol", "static").upper()
        if protocol_str == "STATIC":
            protocol = RoutingProtocol.STATIC
        elif protocol_str == "RIP":
            protocol = RoutingProtocol.RIP
        elif protocol_str == "OSPF":
            protocol = RoutingProtocol.OSPF
        elif protocol_str == "EIGRP":
            protocol = RoutingProtocol.EIGRP
        else:
            protocol = RoutingProtocol.STATIC
        
        return NetworkConfig(
            base_network=data.get("base_network", "192.168.0.0/16"),
            subnets=subnets,
            devices=devices,
            routing_protocol=protocol
        )
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise ValueError(f"LLM parsing failed: {e}")
