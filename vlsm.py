import ipaddress
import math
from typing import List
from .schemas import SubnetRequest, SubnetResult

def calculate_vlsm(base_network: str, subnets: List[SubnetRequest]) -> List[SubnetResult]:
    """
    Calculate Variable Length Subnet Masking (VLSM) for given subnets.
    """
    try:
        network = ipaddress.ip_network(base_network, strict=False)
    except ValueError as e:
        raise ValueError(f"Invalid base network: {e}")
    
    if not subnets:
        return []
    
    # Sort subnets by required_hosts descending (VLSM best practice)
    sorted_subnets = sorted(subnets, key=lambda x: x.required_hosts, reverse=True)
    
    results: List[SubnetResult] = []
    current_network_addr = network.network_address
    
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
        # We need to make sure current_network_addr is aligned to the new prefix
        alignment = 2**host_bits
        offset = int(current_network_addr) % alignment
        if offset != 0:
            current_network_addr = ipaddress.ip_address(int(current_network_addr) + (alignment - offset))

        try:
            subnet = ipaddress.ip_network(f"{current_network_addr}/{prefix_length}", strict=False)
        except ValueError as e:
            raise ValueError(f"Failed to create subnet: {e}")
        
        # Check if subnet fits in base network
        if subnet.broadcast_address > network.broadcast_address:
            raise ValueError(
                f"Not enough address space for subnet '{subnet_req.name}'. "
                f"Required: {2**host_bits} addresses"
            )
        
        # Get usable hosts
        hosts = list(subnet.hosts())
        
        # First usable IP is gateway
        gateway = str(hosts[0]) if hosts else ""
        usable_start = str(hosts[1]) if len(hosts) > 1 else gateway
        usable_end = str(hosts[-1]) if hosts else ""
        
        result = SubnetResult(
            name=subnet_req.name,
            network=str(subnet),
            mask=str(subnet.netmask),
            gateway=gateway,
            usable_range=[usable_start, usable_end],
            broadcast=str(subnet.broadcast_address),
            total_hosts=subnet.num_addresses,
            usable_hosts=max(0, subnet.num_addresses - 2)
        )
        
        results.append(result)
        
        # Move to next available address block
        current_network_addr = subnet.broadcast_address + 1
    
    return results
