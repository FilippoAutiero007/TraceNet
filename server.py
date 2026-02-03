import os
import json
import base64
from typing import Optional
from mcp.server.fastmcp import FastMCP
from .schemas import NetworkConfig, SubnetRequest, RoutingProtocol, DeviceCount
from .vlsm import calculate_vlsm
from .xml_generator import create_pkt_xml, save_as_pkt, save_raw_xml
from openai import OpenAI

# Initialize FastMCP server
mcp = FastMCP("NetTrace")

# Initialize OpenAI client
client = OpenAI()

SYSTEM_PROMPT = """You are a network configuration parser. Extract structured data from natural language network descriptions.

Return ONLY valid JSON with this exact structure:
{
  "base_network": "X.X.X.X/XX",
  "subnets": [
    {"name": "Subnet-Name", "required_hosts": 50}
  ],
  "devices": {"routers": 1, "switches": 2, "pcs": 10, "servers": 1},
  "routing_protocol": "static"
}

Rules:
- base_network: Use CIDR notation (default "192.168.0.0/16" if not specified)
- subnets: Array of objects with name and required_hosts
- devices: Count of each device type mentioned
- routing_protocol: One of "static", "rip", "ospf", "eigrp"
- If not specified, use sensible defaults
- Always return valid JSON, nothing else"""

@mcp.tool()
async def generate_network(description: str) -> str:
    """
    Generates a Cisco Packet Tracer (.pkt) file from a natural language description.
    Includes full topology with cables, XY coordinates, and IOS configurations.
    """
    try:
        # 1. Parse description using LLM
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse this network description: {description}"}
            ],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        
        # 2. Map to Pydantic models
        config = NetworkConfig(
            base_network=data.get("base_network", "192.168.0.0/16"),
            subnets=[SubnetRequest(**s) for s in data.get("subnets", [])],
            devices=DeviceCount(**data.get("devices", {})),
            routing_protocol=RoutingProtocol(data.get("routing_protocol", "static").lower())
        )
        
        # 3. Calculate VLSM
        subnets = calculate_vlsm(config.base_network, config.subnets)
        
        # 4. Generate XML
        xml_content = create_pkt_xml(config, subnets)
        
        # 5. Save and compress
        output_path_pkt = "/home/ubuntu/network.pkt"
        output_path_xml = "/home/ubuntu/network.xml"
        save_as_pkt(xml_content, output_path_pkt)
        save_raw_xml(xml_content, output_path_xml)
        
        return (f"Rete generata con successo!\n"
                f"- File Packet Tracer: {output_path_pkt}\n"
                f"- File XML (per debug): {output_path_xml}\n"
                f"La rete include {len(subnets)} subnet, {config.devices.pcs} PC, e utilizza {config.routing_protocol}.")

    except Exception as e:
        return f"Errore durante la generazione della rete: {str(e)}"

if __name__ == "__main__":
    mcp.run()
