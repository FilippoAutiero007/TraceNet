"""
Final PKT Generator - Optimized with link support
"""
import sys
sys.path.insert(0, '.')

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
import xml.etree.ElementTree as ET
import random
import copy

class PKTGenerator:
    def __init__(self, template_path='simple_ref.pkt'):
        """Load template once at initialization."""
        print("📂 Loading PKT template...")
        with open(template_path, 'rb') as f:
            encrypted = f.read()
        
        xml_str = decrypt_pkt_data(encrypted).decode('utf-8')
        self.template_root = ET.fromstring(xml_str)
        
        # Extract device templates
        template_network = self.template_root.find('NETWORK')
        template_devices = template_network.find('DEVICES').findall('DEVICE')
        
        self.device_templates = {}
        for dev in template_devices:
            engine = dev.find('ENGINE')
            dev_type = engine.find('TYPE').text.lower()
            self.device_templates[dev_type] = dev
        
        # Extract link template
        template_links = template_network.find('LINKS').findall('LINK')
        self.link_template = template_links[0] if template_links else None
        
        print(f"✅ Template loaded with {len(self.device_templates)} device types")
    
    def generate(self, devices_config, links_config=None, output_path='output.pkt'):
        """
        Generate PKT file.
        
        Args:
            devices_config: [{'name': 'R1', 'type': 'router', 'ip': '10.0.0.1', ...}]
            links_config: [{'from': 'R1', 'from_port': 'Fa0/0', 'to': 'S1', 'to_port': 'Fa0/1'}]
            output_path: Output file path
        """
        print(f"\n🔨 Generating PKT: {output_path}")
        print("=" * 60)
        
        # Clone root template
        root = copy.deepcopy(self.template_root)
        network = root.find('NETWORK')
        devices_elem = network.find('DEVICES')
        links_elem = network.find('LINKS')
        
        # Clear existing
        devices_elem.clear()
        links_elem.clear()
        
        device_saverefs = {}
        
        # Create devices
        print(f"\n📦 Creating {len(devices_config)} devices...")
        for idx, dev_cfg in enumerate(devices_config):
            dev_type = dev_cfg.get('type', 'router').lower()
            
            # Get template
            template = self.device_templates.get(dev_type)
            if not template:
                print(f"   ⚠️  No template for '{dev_type}', using router")
                template = self.device_templates.get('router')
            
            # Clone and modify
            new_device = copy.deepcopy(template)
            engine = new_device.find('ENGINE')
            
            # Update basic info
            engine.find('NAME').text = dev_cfg['name']
            
            sysname = engine.find('SYSNAME')
            if sysname is not None:
                sysname.text = dev_cfg['name']
            
            # Generate new SAVEREFID
            new_saverefid = f"save-ref-id{random.randint(10**18, 10**19)}"
            saverefid_elem = engine.find('SAVEREFID')
            if saverefid_elem is not None:
                saverefid_elem.text = new_saverefid
            else:
                ET.SubElement(engine, 'SAVEREFID').text = new_saverefid
            
            device_saverefs[dev_cfg['name']] = new_saverefid
            
            # Update position
            coords = engine.find('COORDSETTINGS')
            if coords is not None:
                coords.find('XCOORD').text = str(dev_cfg.get('x', 200 + idx * 200))
                coords.find('YCOORD').text = str(dev_cfg.get('y', 300))
            
            # Update IP
            if 'ip' in dev_cfg:
                self._update_device_ip(engine, dev_cfg)
            
            devices_elem.append(new_device)
            print(f"   ✅ {dev_cfg['name']} ({dev_type})")
        
        # Create links
        if links_config:
            print(f"\n🔗 Creating {len(links_config)} links...")
            for link_cfg in links_config:
                self._create_link(links_elem, link_cfg, device_saverefs)
                print(f"   ✅ {link_cfg['from']} <-> {link_cfg['to']}")
        
        # Save
        xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
        xml_str += ET.tostring(root, encoding='unicode', method='xml')
        
        encrypted = encrypt_pkt_data(xml_str.encode('utf-8'))
        
        with open(output_path, 'wb') as f:
            f.write(encrypted)
        
        print(f"\n✅ Generated: {output_path} ({len(encrypted)} bytes)")
        return output_path
    
    def _update_device_ip(self, engine, dev_cfg):
        """Update first port IP."""
        module = engine.find('MODULE')
        if module is None:
            return
        
        slots = module.findall('SLOT')
        if not slots:
            return
        
        slot_module = slots[0].find('MODULE')
        if slot_module is None:
            return
        
        port = slot_module.find('PORT')
        if port is None:
            return
        
        # Update IP fields
        for tag, value in [
            ('IP', dev_cfg.get('ip', '')),
            ('SUBNET', dev_cfg.get('subnet', '255.255.255.0')),
            ('POWER', 'true'),
            ('UPMETHOD', '3')
        ]:
            elem = port.find(tag)
            if elem is not None:
                elem.text = value
    
    def _create_link(self, links_elem, link_cfg, device_saverefs):
        """Create link between devices."""
        if not self.link_template:
            print("   ⚠️  No link template available")
            return
        
        link = copy.deepcopy(self.link_template)
        
        # Update FROM
        from_saveref = device_saverefs.get(link_cfg['from'])
        to_saveref = device_saverefs.get(link_cfg['to'])
        
        if not from_saveref or not to_saveref:
            print(f"   ⚠️  Device not found for link")
            return
        
        link.find('FROM').text = from_saveref
        link.find('TO').text = to_saveref
        
        # Update ports
        ports = link.findall('PORT')
        if len(ports) >= 2:
            ports[0].text = link_cfg.get('from_port', 'FastEthernet0/0')
            ports[1].text = link_cfg.get('to_port', 'FastEthernet0/1')
        
        # Randomize memory addresses
        for tag in ['FROMDEVICEMEMADDR', 'TODEVICEMEMADDR', 
                    'FROMPORTMEMADDR', 'TOPORTMEMADDR']:
            elem = link.find(tag)
            if elem is not None:
                elem.text = str(random.randint(10**12, 10**13))
        
        links_elem.append(link)


def save_pkt_file(subnets: list, config: dict, output_dir: str) -> dict:
    """
    Generate and save PKT file using template-based approach.
    
    This function is called by the API endpoints and uses the PKTGenerator class
    which clones devices from simple_ref.pkt template for guaranteed compatibility.
    
    Args:
        subnets: List of subnet objects from VLSM calculation
        config: Network configuration dictionary
        output_dir: Directory to save output files
        
    Returns:
        dict with success status, file paths, and metadata
    """
    import os
    import logging
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    logger.info("🔨 Generating PKT file using template-based approach...")
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pkt_filename = f"network_{timestamp}.pkt"
        xml_filename = f"network_{timestamp}.xml"
        
        pkt_path = os.path.join(output_dir, pkt_filename)
        xml_path = os.path.join(output_dir, xml_filename)
        
        # Get template path
        template_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 
            'templates', 
            'simple_ref.pkt'
        )
        template_path = os.path.abspath(template_path)
        
        if not os.path.exists(template_path):
            logger.error(f"Template not found: {template_path}")
            return {
                "success": False,
                "error": f"Template file not found: {template_path}"
            }
        
        # Initialize generator
        logger.info(f"Loading template from: {template_path}")
        generator = PKTGenerator(template_path)
        
        # Convert subnets to device configuration
        devices_config = []
        device_counter = {"router": 0, "switch": 0, "pc": 0}
        
        # Get device counts from config
        device_counts = config.get("devices", {})
        num_routers = device_counts.get("routers", 1)
        num_switches = device_counts.get("switches", 1)
        num_pcs = device_counts.get("pcs", 0)
        
        # Create routers
        for i in range(num_routers):
            devices_config.append({
                "name": f"Router{i}",
                "type": "router",
                "x": 200 + i * 150,
                "y": 200
            })
        
        # Create switches
        for i in range(num_switches):
            devices_config.append({
                "name": f"Switch{i}",
                "type": "switch",
                "x": 200 + i * 150,
                "y": 350
            })
        
        # Create PCs with IPs from subnets
        pc_idx = 0
        for subnet in subnets:
            # Assign some PCs to this subnet
            subnet_pcs = min(3, num_pcs - pc_idx)  # Max 3 PCs per subnet
            
            for i in range(subnet_pcs):
                if pc_idx >= num_pcs:
                    break
                    
                # Get usable IP from subnet
                ip = subnet.usable_range[i] if i < len(subnet.usable_range) else ""
                
                devices_config.append({
                    "name": f"PC{pc_idx}",
                    "type": "pc",
                    "ip": ip,
                    "subnet": subnet.mask,
                    "x": 200 + pc_idx * 120,
                    "y": 500
                })
                pc_idx += 1
        
        logger.info(f"Generating {len(devices_config)} devices...")
        
        # Generate PKT file (no links for now - basic topology)
        generator.generate(devices_config, links_config=None, output_path=pkt_path)
        
        # Save XML for debugging
        with open(template_path, 'rb') as f:
            from app.services.pkt_crypto import decrypt_pkt_data
            xml_content = decrypt_pkt_data(f.read()).decode('utf-8')
            with open(xml_path, 'w', encoding='utf-8') as xml_f:
                xml_f.write(xml_content)
        
        # Get file size
        file_size = os.path.getsize(pkt_path)
        
        logger.info(f"✅ PKT file generated successfully: {pkt_path}")
        
        return {
            "success": True,
            "pkt_path": pkt_path,
            "xml_path": xml_path,
            "encoding_used": "template_based",
            "file_size": file_size,
            "pka2xml_available": False,  # Not using pka2xml
            "method": "template_cloning"
        }
        
    except Exception as e:
        logger.error(f"❌ PKT generation failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# Test
if __name__ == "__main__":
    gen = PKTGenerator('simple_ref.pkt')
    
    # Define network topology
    devices = [
        {'name': 'R1', 'type': 'router', 'ip': '192.168.1.1', 'x': 200, 'y': 300},
        {'name': 'S1', 'type': 'switch', 'x': 400, 'y': 300},
        {'name': 'PC1', 'type': 'pc', 'ip': '192.168.1.10', 'x': 600, 'y': 200},
        {'name': 'PC2', 'type': 'pc', 'ip': '192.168.1.11', 'x': 600, 'y': 400}
    ]
    
    links = [
        {'from': 'R1', 'from_port': 'FastEthernet0/0', 'to': 'S1', 'to_port': 'FastEthernet0/1'},
        {'from': 'S1', 'from_port': 'FastEthernet1/1', 'to': 'PC1', 'to_port': 'FastEthernet0'},
        {'from': 'S1', 'from_port': 'FastEthernet2/1', 'to': 'PC2', 'to_port': 'FastEthernet0'}
    ]
    
    output = gen.generate(devices, links, 'final_network.pkt')
    
    # Open
    import subprocess
    subprocess.Popen(['start', output], shell=True)
    print("\n🚀 Opening in Packet Tracer...")

