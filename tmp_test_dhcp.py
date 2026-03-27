import xml.etree.ElementTree as ET
from app.services.pkt_generator.server_config import write_dhcp_config

def test_large_subnet():
    engine = ET.Element("ENGINE")
    dhcp_servers = ET.SubElement(engine, "DHCP_SERVERS")
    pool = ET.SubElement(dhcp_servers, "ASSOCIATED_PORTS")
    ap = ET.SubElement(pool, "ASSOCIATED_PORT")
    ET.SubElement(ap, "NAME").text = "FastEthernet0"

    cfg = {
        "network": "10.0.0.0/8",
        "ip": "10.0.0.2",
    }
    write_dhcp_config(engine, cfg)
    xml_str = ET.tostring(engine, encoding="unicode")
    print(xml_str)

test_large_subnet()
