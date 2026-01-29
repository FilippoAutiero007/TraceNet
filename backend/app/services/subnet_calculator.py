"""
Subnet Calculator Service - VLSM algorithm implementation
"""

import ipaddress
from typing import List
import math
from app.models.schemas import SubnetRequest, SubnetResult

def calculate_vlsm(base_network: str, subnets: List[SubnetRequest]) -> List[SubnetResult]:
    """
    Calculate Variable Length Subnet Masking (VLSM) for given subnets.
    
    Args:
        base_network: Base network in CIDR notation (e.g., "192.168.1.0/24")
        subnets: List of subnet requests with required hosts
        
    Returns:
        List of SubnetResult with calculated network details
    """
    try:
        network = ipaddress.ip_network(base_network, strict=False)
    except ValueError as e:
        raise ValueError(f"Invalid base network: {e}")
    
    if not subnets:
        raise ValueError("No subnets specified")
    
    # Sort subnets by required_hosts descending (VLSM best practice)
    sorted_subnets = sorted(subnets, key=lambda x: x.required_hosts, reverse=True)
    
    results: List[SubnetResult] = []
    current_network = network.network_address
    
    for subnet_req in sorted_subnets:
        # Calculate required bits for hosts (+2 for network and broadcast)
        required_addresses = subnet_req.required_hosts + 2
        host_bits = math.ceil(math.log2(required_addresses))
        
        # Minimum 2 host bits (for /30 network)
        host_bits = max(host_bits, 2)
        
        # Calculate prefix length
        prefix_length = 32 - host_bits
        
        # Ensure prefix is not smaller than base network
        if prefix_length < network.prefixlen:
            raise ValueError(
                f"Subnet '{subnet_req.name}' requires {subnet_req.required_hosts} hosts, "
                f"which exceeds available space in {base_network}"
            )
        
        # Create subnet at current position
        try:
            subnet = ipaddress.ip_network(f"{current_network}/{prefix_length}", strict=False)
        except ValueError as e:
            raise ValueError(f"Failed to create subnet: {e}")
        
        # Check if subnet fits in base network
        if subnet.broadcast_address > network.broadcast_address:
            raise ValueError(
                f"Not enough address space for subnet '{subnet_req.name}'. "
                f"Required: {2**host_bits} addresses"
            )
        
        # Get all usable hosts
        hosts = list(subnet.hosts())
        
        if len(hosts) < 2:
            raise ValueError(f"Subnet too small for '{subnet_req.name}'")
        
        # First usable IP is gateway
        gateway = hosts[0]
        
        # Usable range: second to last usable IP
        usable_start = hosts[1] if len(hosts) > 1 else hosts[0]
        usable_end = hosts[-1]
        
        result = SubnetResult(
            name=subnet_req.name,
            network=str(subnet),
            mask=str(subnet.netmask),
            gateway=str(gateway),
            usable_range=[str(usable_start), str(usable_end)],
            broadcast=str(subnet.broadcast_address),
            total_hosts=subnet.num_addresses,
            usable_hosts=len(hosts) - 1  # Exclude gateway
        )
        
        results.append(result)
        
        # Move to next available address block
        current_network = subnet.broadcast_address + 1
    
    # Restore original order
    ordered_results = []
    for subnet_req in subnets:
        for result in results:
            if result.name == subnet_req.name:
                ordered_results.append(result)
                break
    
    return ordered_results
