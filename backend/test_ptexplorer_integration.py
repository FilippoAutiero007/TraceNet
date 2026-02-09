#!/usr/bin/env python3
"""
Test script to verify ptexplorer integration works correctly
This script tests the complete flow: XML generation -> PKT conversion
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ptexplorer_module():
    """Test that ptexplorer module can be imported and works"""
    print("=" * 60)
    print("TEST 1: Import ptexplorer module")
    print("=" * 60)
    
    try:
        from ptexplorer import PTFile
        print("✅ ptexplorer module imported successfully")
        print(f"   PTFile class available: {PTFile is not None}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import ptexplorer: {e}")
        return False


def test_xml_to_pkt_conversion():
    """Test basic XML to PKT conversion"""
    print("\n" + "=" * 60)
    print("TEST 2: XML to PKT conversion")
    print("=" * 60)
    
    try:
        from ptexplorer import PTFile
        
        # Create a minimal valid Packet Tracer XML
        test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<PACKETTRACER5 VERSION="8.2.2.0400">
  <WORKSPACE>
    <DEVICES/>
    <LINKS/>
  </WORKSPACE>
</PACKETTRACER5>"""
        
        print("Creating test PKT file from XML...")
        
        # Create temporary output path
        output_dir = Path("/tmp/tracenet_test")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "test_network.pkt"
        
        # Convert XML to PKT
        pt = PTFile()
        pt.open_xml(test_xml)
        pt.save(str(output_path))
        
        # Verify file was created
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"✅ PKT file created successfully")
            print(f"   Path: {output_path}")
            print(f"   Size: {file_size} bytes")
            
            # Try to read it back
            print("\nVerifying PKT file can be read back...")
            pt2 = PTFile()
            pt2.open(str(output_path))
            xml_content = pt2.export_xml()
            
            if xml_content and len(xml_content) > 0:
                print(f"✅ PKT file read back successfully")
                print(f"   XML size: {len(xml_content)} bytes")
                
                # Cleanup
                output_path.unlink()
                print("\n✅ Test cleanup completed")
                return True
            else:
                print("❌ Failed to read XML content from PKT file")
                return False
        else:
            print(f"❌ PKT file was not created at {output_path}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pkt_file_generator_import():
    """Test that pkt_file_generator can import ptexplorer"""
    print("\n" + "=" * 60)
    print("TEST 3: pkt_file_generator integration")
    print("=" * 60)
    
    try:
        # Add app to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        from app.services.pkt_file_generator import PTEXPLORER_AVAILABLE, build_pkt_from_xml
        
        print(f"PTEXPLORER_AVAILABLE: {PTEXPLORER_AVAILABLE}")
        
        if PTEXPLORER_AVAILABLE:
            print("✅ ptexplorer is available in pkt_file_generator")
            print(f"   build_pkt_from_xml function: {build_pkt_from_xml is not None}")
            return True
        else:
            print("❌ ptexplorer is NOT available in pkt_file_generator")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🔧" * 30)
    print("PTEXPLORER INTEGRATION TEST SUITE")
    print("🔧" * 30 + "\n")
    
    results = []
    
    # Test 1: Module import
    results.append(("Import ptexplorer module", test_ptexplorer_module()))
    
    # Test 2: XML to PKT conversion
    results.append(("XML to PKT conversion", test_xml_to_pkt_conversion()))
    
    # Test 3: pkt_file_generator integration
    results.append(("pkt_file_generator integration", test_pkt_file_generator_import()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-" * 60)
    print(f"Total: {total} tests")
    print(f"Passed: {passed} tests")
    print(f"Failed: {failed} tests")
    print("-" * 60)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
