
import sys
import os
import shutil
import logging

# Configure logging to show info
logging.basicConfig(level=logging.INFO)

# Ensure backend directory is in path
sys.path.append(os.getcwd())

try:
    from app.services.pkt_file_generator import save_pkt_file
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

from unittest.mock import patch, MagicMock

# Sample mock data
class MockSubnet:
    def __init__(self):
        self.gateway = "192.168.1.1"
        self.mask = "255.255.255.0"
        self.network = "192.168.1.0/24"
        self.usable_hosts = 10
        self.name = "TestSubnet"

MOCK_DATA = {
    "subnets": [MockSubnet()],
    "config": {"XML_VERSION": "8.2.2.0400"}
}

def run_test():
    output_dir = "test_output_manual"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        
    print("▶️ Starting Manual Test...")
    
    # Mocking to avoid actual docker call if not present, and to return predictable data
    # Test 1: Simulate pka2xml success
    with patch("app.services.pkt_file_generator.encode_with_pka2xml") as mock_pka:
        mock_pka.return_value = b"MOCK_AES_ENCRIPTED_CONTENT_LARGER_THAN_1KB" * 10 
        
        # We need to set env to use external
        with patch.dict(os.environ, {"PKT_ENCODING": "external_pka2xml"}):
             # Also mock shutil.which to say pka2xml exists
             with patch("shutil.which") as mock_which:
                 mock_which.return_value = "/usr/bin/pka2xml"
                 
                 result = save_pkt_file(MOCK_DATA["subnets"], MOCK_DATA["config"], output_dir)
                 
                 print(f"   Result: {result}")
                 
                 if not result["success"]:
                     print("❌ Test 1 Failed: Success flag is False")
                     return False
                 if result["encoding_used"] != "external_pka2xml":
                     print(f"❌ Test 1 Failed: Expected external_pka2xml, got {result['encoding_used']}")
                     return False
                 if result["file_size"] < 100:
                     print("❌ Test 1 Failed: File size too small")
                     return False
                 print("✅ Test 1 Passed (pka2xml path)")

    # Test 2: Simulate pka2xml failure -> Fallback
    with patch("app.services.pkt_file_generator.encode_with_pka2xml") as mock_pka:
        mock_pka.side_effect = Exception("Docker Error")
        
        with patch.dict(os.environ, {"PKT_ENCODING": "external_pka2xml"}):
             with patch("shutil.which") as mock_which:
                 mock_which.return_value = "/usr/bin/pka2xml"
                 
                 result = save_pkt_file(MOCK_DATA["subnets"], MOCK_DATA["config"], output_dir)
                 
                 # Should succeed via fallback
                 if not result["success"]:
                     print(f"❌ Test 2 Failed: Should have succeeded via fallback. Error: {result.get('error')}")
                     return False
                 
                 if result["encoding_used"] != "legacy_xor_fallback":
                     print(f"❌ Test 2 Failed: Expected fallback, got {result['encoding_used']}")
                     return False
                     
                 print("✅ Test 2 Passed (Fallback Logic)")

    return True

if __name__ == "__main__":
    if run_test():
        print("🎉 ALL MANUAL TESTS PASSED")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED")
        sys.exit(1)
