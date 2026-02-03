from typing import List
from .schemas import NetworkConfig, SubnetResult, RoutingProtocol

def generate_router_config(hostname: str, subnets: List[SubnetResult], 
                          protocol: RoutingProtocol) -> str:
    """Genera configurazione IOS per router con interfacce FastEthernet"""
    lines = [
        f"hostname {hostname}",
        "!",
        "enable secret cisco",
        "service password-encryption",
        "!",
    ]
    
    # CORRETTO: Usa FastEthernet per Router 1841
    for i, subnet in enumerate(subnets):
        if i < 2:  # Router 1841 ha FastEthernet 0/0, 0/1
            lines.extend([
                f"interface FastEthernet0/{i}",
                f" description LAN_{subnet.name}",
                f" ip address {subnet.gateway} {subnet.mask}",
                " no shutdown",
                "!",
            ])
    
    # Configurazione interfaccia non usata
    if len(subnets) < 2:
        lines.extend([
            "interface FastEthernet0/1",
            " no ip address",
            " shutdown",
            "!",
        ])
    
    # Routing protocols
    if protocol == RoutingProtocol.RIP:
        lines.extend([
            "router rip",
            " version 2",
            " no auto-summary",
        ])
        for subnet in subnets:
            net_addr = subnet.network.split('/')[0]
            lines.append(f" network {net_addr}")
        lines.append("!")
        
    elif protocol == RoutingProtocol.OSPF:
        lines.extend([
            "router ospf 1",
        ])
        for subnet in subnets:
            net_addr = subnet.network.split('/')[0]
            mask_octets = subnet.mask.split('.')
            wildcard = ".".join([str(255 - int(o)) for o in mask_octets])
            lines.append(f" network {net_addr} {wildcard} area 0")
        lines.append("!")
    
    # Console and VTY lines
    lines.extend([
        "line con 0",
        " password cisco",
        " login",
        "!",
        "line vty 0 4",
        " password cisco",
        " login",
        "!",
        "end",
    ])
    
    return "\n".join(lines)

def generate_switch_config(hostname: str) -> str:
    """Genera configurazione IOS base per switch"""
    return f"""hostname {hostname}
!
enable secret cisco
!
line con 0
 password cisco
 login
!
line vty 0 4
 password cisco
 login
!
end"""
