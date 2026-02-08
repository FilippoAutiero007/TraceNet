"""
Test script per validare la generazione di file .pkt con il nuovo sistema

Questo script testa:
1. Costruzione XML
2. Crittografia Twofish/EAX
3. Generazione file .pkt
4. Validazione roundtrip
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import SubnetResult, RoutingProtocol
from app.services.pkt_file_generator import save_pkt_file, validate_pkt_file


def test_pkt_generation():
    """Test complete PKT generation pipeline"""
    
    print("=" * 60)
    print("🧪 TraceNet PKT Generation Test")
    print("   Using Unpacket (Twofish/EAX) + pka2xml structure")
    print("=" * 60)
    print()
    
    # Create test subnets
    subnets = [
        SubnetResult(
            name="Admin",
            network="192.168.1.0/26",
            mask="255.255.255.192",
            gateway="192.168.1.1",
            usable_range=["192.168.1.2", "192.168.1.62"],
            broadcast="192.168.1.63",
            total_hosts=64,
            usable_hosts=62
        ),
        SubnetResult(
            name="Guest",
            network="192.168.1.64/26",
            mask="255.255.255.192",
            gateway="192.168.1.65",
            usable_range=["192.168.1.66", "192.168.1.126"],
            broadcast="192.168.1.127",
            total_hosts=64,
            usable_hosts=62
        )
    ]
    
    # Create test config
    config = {
        "routing_protocol": RoutingProtocol.STATIC,
        "routers": 1,
        "switches": 2,
        "pcs": 4
    }
    
    print("📋 Test Configuration:")
    print(f"   Subnets: {len(subnets)}")
    print(f"   Routers: {config['routers']}")
    print(f"   Switches: {config['switches']}")
    print(f"   PCs: {config['pcs']}")
    print(f"   Routing: {config['routing_protocol']}")
    print()
    
    # Generate PKT file
    print("🔧 Generating PKT file...")
    print()
    
    result = save_pkt_file(subnets, config, output_dir="/tmp/tracenet_test")
    
    print()
    print("=" * 60)
    print("📊 Generation Results:")
    print("=" * 60)
    
    if result["success"]:
        print(f"✅ Status: SUCCESS")
        print(f"📁 PKT File: {result['pkt_path']}")
        print(f"📁 XML File: {result['xml_path']}")
        print(f"📦 File Size: {result['file_size']:,} bytes")
        print(f"🔐 Encryption: {result['encoding_used']}")
        print(f"✔️  Validation: {result['validation']}")
        print()
        
        # Validate the generated file
        print("🔍 Running validation...")
        print()
        validation = validate_pkt_file(result['pkt_path'])
        
        if validation['valid']:
            print(f"✅ Validation: PASSED")
            print(f"   PT Version: {validation['version']}")
            print(f"   Devices: {validation['devices']}")
            print(f"   Links: {validation['links']}")
            print(f"   XML Size: {validation['xml_size']:,} bytes")
        else:
            print(f"❌ Validation: FAILED")
            print(f"   Error: {validation['error']}")
        
        print()
        print("=" * 60)
        print("📝 Next Steps:")
        print("=" * 60)
        print(f"1. Open file in Cisco Packet Tracer 8.x:")
        print(f"   {result['pkt_path']}")
        print()
        print(f"2. Inspect debug XML:")
        print(f"   {result['xml_path']}")
        print()
        
        return True
        
    else:
        print(f"❌ Status: FAILED")
        print(f"   Error: {result['error']}")
        return False


if __name__ == "__main__":
    try:
        success = test_pkt_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
