"""
PKT Generator Service - Generates Cisco IOS CLI configurations
"""

from typing import List
from app.models.schemas import NetworkConfig, SubnetResult

def generate_cisco_config(network_config: NetworkConfig, subnets: List[SubnetResult]) -> str:
    """
    Generate Cisco IOS CLI configuration commands.
    
    Args:
        network_config: Parsed network configuration
        subnets: Calculated subnet results
        
    Returns:
        Cisco IOS CLI configuration as string
    """
    lines = []
    
    # Header
    lines.append("!" * 60)
    lines.append("! NetTrace - Auto-generated Cisco Configuration")
    lines.append("! Generated from natural language description")
    lines.append("!" * 60)
    lines.append("")
    
    # Router configuration
    for router_num in range(1, network_config.devices.routers + 1):
        lines.append(f"! ========== Router R{router_num} Configuration ==========")
        lines.append(f"hostname R{router_num}")
        lines.append("!")
        lines.append("! Enable password encryption")
        lines.append("service password-encryption")
        lines.append("!")
        
        # Configure interfaces for each subnet
        for i, subnet in enumerate(subnets):
            interface_num = i
            lines.append(f"! Interface for {subnet.name}")
            lines.append(f"interface GigabitEthernet0/{interface_num}")
            lines.append(f" description {subnet.name} - {subnet.network}")
            lines.append(f" ip address {subnet.gateway} {subnet.mask}")
            lines.append(" no shutdown")
            lines.append("!")
        
        # Routing protocol configuration
        if network_config.routing_protocol.value == "RIP":
            lines.append("! RIP Routing Configuration")
            lines.append("router rip")
            lines.append(" version 2")
            for subnet in subnets:
                # Extract network address without prefix
                network_addr = subnet.network.split("/")[0]
                lines.append(f" network {network_addr}")
            lines.append(" no auto-summary")
            lines.append("!")
            
        elif network_config.routing_protocol.value == "OSPF":
            lines.append("! OSPF Routing Configuration")
            lines.append("router ospf 1")
            for i, subnet in enumerate(subnets):
                network_addr = subnet.network.split("/")[0]
                # Calculate wildcard mask
                octets = subnet.mask.split(".")
                wildcard = ".".join([str(255 - int(o)) for o in octets])
                lines.append(f" network {network_addr} {wildcard} area 0")
            lines.append("!")
            
        elif network_config.routing_protocol.value == "EIGRP":
            lines.append("! EIGRP Routing Configuration")
            lines.append("router eigrp 100")
            for subnet in subnets:
                network_addr = subnet.network.split("/")[0]
                lines.append(f" network {network_addr}")
            lines.append(" no auto-summary")
            lines.append("!")
        
        lines.append("")
    
    # Switch configuration
    for switch_num in range(1, network_config.devices.switches + 1):
        lines.append(f"! ========== Switch S{switch_num} Configuration ==========")
        lines.append(f"hostname S{switch_num}")
        lines.append("!")
        
        # Assign switch to a subnet (round-robin if more switches than subnets)
        if subnets:
            subnet_idx = (switch_num - 1) % len(subnets)
            subnet = subnets[subnet_idx]
            lines.append(f"! Management VLAN for {subnet.name}")
            lines.append("interface vlan 1")
            
            # Calculate management IP (use an IP from usable range)
            usable_start = subnet.usable_range[0]
            parts = usable_start.split(".")
            mgmt_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.{int(parts[3]) + switch_num}"
            
            lines.append(f" ip address {mgmt_ip} {subnet.mask}")
            lines.append(" no shutdown")
            lines.append("!")
            lines.append(f"ip default-gateway {subnet.gateway}")
            lines.append("!")
        
        lines.append("")
    
    # PC configuration hints
    if network_config.devices.pcs > 0:
        lines.append("! ========== PC Configuration Guide ==========")
        lines.append("! Configure PCs manually in Packet Tracer:")
        
        pc_num = 1
        for subnet in subnets:
            # Distribute PCs across subnets
            pcs_per_subnet = max(1, network_config.devices.pcs // len(subnets))
            
            usable_start = subnet.usable_range[0]
            parts = usable_start.split(".")
            
            for j in range(pcs_per_subnet):
                if pc_num > network_config.devices.pcs:
                    break
                    
                pc_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.{int(parts[3]) + j + 10}"
                lines.append(f"! PC{pc_num}: IP={pc_ip}, Mask={subnet.mask}, Gateway={subnet.gateway}")
                pc_num += 1
        
        lines.append("!")
    
    # Summary
    lines.append("")
    lines.append("!" * 60)
    lines.append("! SUBNET SUMMARY")
    lines.append("!" * 60)
    
    for subnet in subnets:
        lines.append(f"! {subnet.name}:")
        lines.append(f"!   Network: {subnet.network}")
        lines.append(f"!   Mask: {subnet.mask}")
        lines.append(f"!   Gateway: {subnet.gateway}")
        lines.append(f"!   Usable IPs: {subnet.usable_range[0]} - {subnet.usable_range[1]}")
        lines.append(f"!   Broadcast: {subnet.broadcast}")
        lines.append(f"!   Usable Hosts: {subnet.usable_hosts}")
        lines.append("!")
    
    lines.append("! End of configuration")
    
    return "\n".join(lines)
