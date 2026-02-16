from typing import List, Dict, Optional
from pydantic import BaseModel

class Port(BaseModel):
    id: str  # es. "Fa0/0", "Gi0/1"
    type: str  # "ethernet", "serial", "console"
    speed: Optional[str] = "1G"  # "10M", "100M", "1G", "10G"

class Capabilities(BaseModel):
    layer2: bool = False
    layer3: bool = False
    staticRouting: bool = False
    ripv2: bool = False
    ospf: bool = False
    eigrp: bool = False
    vlans: bool = False
    vpn: bool = False
    firewall: bool = False
    dhcpClient: bool = False
    dhcpServer: bool = False
    dnsServer: bool = False
    webServer: bool = False

class DeviceType(BaseModel):
    id: str  # "cisco-2911", "cisco-2960", "generic-pc"
    category: str  # "router", "switch", "pc", "server"
    displayName: str
    ports: List[Port]
    capabilities: Capabilities
    icon: Optional[str] = None  # path per frontend

# Esempio di utilizzo
DEVICE_CATALOG = {
    "cisco-2911": DeviceType(
        id="cisco-2911",
        category="router",
        displayName="Cisco 2911 Router",
        ports=[
            Port(id="Fa0/0", type="ethernet", speed="1G"),
            Port(id="Fa0/1", type="ethernet", speed="1G"),
        ],
        capabilities=Capabilities(
            layer3=True,
            staticRouting=True,
            ripv2=True,
            ospf=True,
            eigrp=True,
            vlans=True,
            vpn=True,
            firewall=True
        )
    ),
    "cisco-2911-large": DeviceType(
        id="cisco-2911-large",
        category="router",
        displayName="Cisco 2911 Router (8 ports)",
        ports=[
            Port(id=f"Fa0/{i}", type="ethernet", speed="1G") 
            for i in range(8)
        ],
        capabilities=Capabilities(
            layer3=True,
            staticRouting=True,
            ripv2=True,
            ospf=True,
            eigrp=True,
            vlans=True,
            vpn=True,
            firewall=True
        )
    ),
    # Aggiungi altri device qui...
}
