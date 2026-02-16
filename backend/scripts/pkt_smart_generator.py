"""
Smart PKT Generator - Modifies simple_ref.pkt template dynamically
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
import xml.etree.ElementTree as ET
import random
import os

def generate_pkt_from_template(devices_config: list, output_path: str):
    """
    Generate PKT file by modifying simple_ref.pkt template.
    
    Args:
        devices_config: List of device dicts with {name, type, ip, position}
        output_path: Path to save .pkt file
    """
    print("🔨 Smart PKT Generator")
    print("=" * 60)
    
    # 1. Load template
    print("\n📂 Step 1: Loading simple_ref.pkt template...")
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'simple_ref.pkt')
    with open(template_path, 'rb') as f:
        encrypted = f.read()
    
    xml_str = decrypt_pkt_data(encrypted).decode('utf-8')
    print(f"✅ Template loaded: {len(xml_str)} chars")
    
    # 2. Parse XML
    print("\n🔍 Step 2: Parsing XML...")
    root = ET.fromstring(xml_str)
    print("✅ XML parsed successfully")
    
    # 3. Find DEVICES section
    print("\n🔧 Step 3: Modifying devices...")
    network = root.find('NETWORK')
    devices_elem = network.find('DEVICES')
    links_elem = network.find('LINKS')
    
    # Clear existing devices and links
    devices_elem.clear()
    links_elem.clear()
    
    # 4. Find one device template from original XML (for cloning)
    print("   📋 Loading device template from simple_ref.pkt...")
    with open(template_path, 'rb') as f:
        template_encrypted = f.read()
    template_xml = decrypt_pkt_data(template_encrypted).decode('utf-8')
    template_root = ET.fromstring(template_xml)
    
    template_network = template_root.find('NETWORK')
    template_devices = template_network.find('DEVICES')
    original_devices = list(template_devices.findall('DEVICE'))
    
    print(f"   ✅ Found {len(original_devices)} device templates")
    
    # 5. Create devices from config
    device_saverefs = {}
    
    for idx, dev_config in enumerate(devices_config):
        print(f"\n   🔨 Creating device {idx+1}/{len(devices_config)}: {dev_config['name']}")
        
        # Clone appropriate template device
        device_type = dev_config.get('type', 'router').lower()
        
        # Find matching template
        template_device = None
        for orig_dev in original_devices:
            engine = orig_dev.find('ENGINE')
            type_elem = engine.find('TYPE')
            if device_type in type_elem.text.lower():
                template_device = orig_dev
                break
        
        if template_device is None:
            template_device = original_devices[0]  # Fallback to first
        
        # Deep copy device
        import copy
        new_device = copy.deepcopy(template_device)
        engine = new_device.find('ENGINE')
        
    # Update name
        name_elem = engine.find('NAME')
        name_elem.text = dev_config['name']
        
        # Update SYSNAME
        sysname = engine.find('SYSNAME')
        if sysname is not None:
            sysname.text = dev_config['name']
        
        # Update SAVEREFID (with check)
        saverefid_elem = engine.find('SAVEREFID')
        new_saverefid = f"save-ref-id{random.randint(10**18, 10**19)}"
        
        if saverefid_elem is not None:
            saverefid_elem.text = new_saverefid
        else:
            # Create SAVEREFID if missing
            saverefid_elem = ET.SubElement(engine, 'SAVEREFID')
            saverefid_elem.text = new_saverefid
        
        device_saverefs[dev_config['name']] = new_saverefid
        
        # Update position
        coords = engine.find('COORDSETTINGS')
        if coords is not None:
            # Determina automaticamente il numero di colonne in base ai dispositivi
            num_devices = len(devices_config)
            if num_devices <= 4:
                cols = 2  # Griglia 2 colonne per pochi dispositivi
            elif num_devices <= 9:
                cols = 3  # Griglia 3 colonne per numero medio
            else:
                cols = 4  # Griglia 4 colonne per molti dispositivi
            
            x_elem = coords.find('XCOORD')
            y_elem = coords.find('YCOORD')
            if x_elem is not None:
                x_elem.text = str(dev_config.get('x', 200 + (idx % cols) * 250))
            if y_elem is not None:
                y_elem.text = str(dev_config.get('y', 200 + (idx // cols) * 200))

        
        # Update IP if provided
        if 'ip' in dev_config and dev_config['ip']:
            module = engine.find('MODULE')
            if module is not None:
                slots = module.findall('SLOT')
                if slots:
                    first_slot = slots[0]
                    slot_module = first_slot.find('MODULE')
                    if slot_module is not None:
                        port = slot_module.find('PORT')
                        if port is not None:
                            ip_elem = port.find('IP')
                            subnet_elem = port.find('SUBNET')
                            power_elem = port.find('POWER')
                            upmethod_elem = port.find('UPMETHOD')
                            
                            if ip_elem is not None:
                                ip_elem.text = dev_config['ip']
                            if subnet_elem is not None:
                                subnet_elem.text = dev_config.get('subnet', '255.255.255.0')
                            if power_elem is not None:
                                power_elem.text = 'true'
                            if upmethod_elem is not None:
                                upmethod_elem.text = '3'
        
        # Add device to tree
        devices_elem.append(new_device)
        print(f"      ✅ Added {dev_config['name']} (SAVEREFID: {new_saverefid[:20]}...)")
    
    # 6. Create links if specified
    if 'links' in devices_config[0] if devices_config else False:
        print("\n   🔗 Creating links...")
        # For now skip links, focus on devices first
    
    # 7. Convert back to XML string
    print("\n📝 Step 4: Converting to XML string...")
    xml_str = ET.tostring(root, encoding='unicode', method='xml')
    xml_str = '<?xml version="1.0" encoding="utf-8"?>\n' + xml_str
    
    # 8. Encrypt
    print("\n🔒 Step 5: Encrypting...")
    xml_bytes = xml_str.encode('utf-8')
    encrypted = encrypt_pkt_data(xml_bytes)
    
    # 9. Save
    with open(output_path, 'wb') as f:
        f.write(encrypted)
    
    print(f"\n✅ PKT file generated: {output_path}")
    print(f"📊 Size: {len(encrypted)} bytes")
    print(f"📦 Devices: {len(devices_config)}")
    
    return output_path


# Test
if __name__ == "__main__":
    # Define custom network
    my_network = [
        {
            'name': 'CoreRouter',
            'type': 'router',
            'ip': '10.0.0.1',
            'subnet': '255.255.255.0',
            'x': 300,
            'y': 200
        },
        {
            'name': 'AccessSwitch',
            'type': 'switch',
            'x': 500,
            'y': 200
        },
        {
            'name': 'Workstation1',
            'type': 'pc',
            'ip': '10.0.0.10',
            'subnet': '255.255.255.0',
            'x': 700,
            'y': 200
        }
    ]
    
    output = generate_pkt_from_template(my_network, 'my_custom_network.pkt')
    
    # Open in PT
    import subprocess
    subprocess.Popen(['start', output], shell=True)
    print("\n🚀 Opening in Packet Tracer...")
