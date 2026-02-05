#!/usr/bin/env python3
"""
NetTrace Backend API Testing Suite
Tests all backend functionality including Mistral AI integration, VLSM calculation, and Cisco config generation
"""

import requests
import json
import sys
from datetime import datetime

class NetTraceAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def test_health_check(self):
        """Test /api/health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy" and data.get("service") == "NetTrace API":
                    self.log_test("Health Check", True)
                    return True
                else:
                    self.log_test("Health Check", False, f"Invalid response data: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False

    def test_root_endpoint(self):
        """Test /api root endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "NetTrace API" in data["message"]:
                    self.log_test("Root Endpoint", True)
                    return True
                else:
                    self.log_test("Root Endpoint", False, f"Invalid response: {data}")
                    return False
            else:
                self.log_test("Root Endpoint", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Exception: {str(e)}")
            return False

    def test_generate_endpoint_basic(self):
        """Test /api/generate endpoint with basic request"""
        try:
            payload = {
                "description": "Create 2 subnets with 50 hosts each from 192.168.1.0/24 with 1 router"
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                if not isinstance(data, dict):
                    self.log_test("Generate Endpoint Basic", False, "Response is not a JSON object")
                    return False
                
                if data.get("success") is True:
                    # Validate required fields
                    required_fields = ["config_json", "subnets", "cli_script"]
                    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
                    
                    if missing_fields:
                        self.log_test("Generate Endpoint Basic", False, f"Missing fields: {missing_fields}")
                        return False
                    
                    # Validate subnets
                    subnets = data.get("subnets", [])
                    if len(subnets) < 2:
                        self.log_test("Generate Endpoint Basic", False, f"Expected 2 subnets, got {len(subnets)}")
                        return False
                    
                    # Validate CLI script
                    cli_script = data.get("cli_script", "")
                    if not cli_script or len(cli_script) < 100:
                        self.log_test("Generate Endpoint Basic", False, "CLI script too short or empty")
                        return False
                    
                    self.log_test("Generate Endpoint Basic", True)
                    return True
                    
                elif data.get("success") is False:
                    error_msg = data.get("error", "Unknown error")
                    self.log_test("Generate Endpoint Basic", False, f"API returned error: {error_msg}")
                    return False
                else:
                    self.log_test("Generate Endpoint Basic", False, f"Invalid success field: {data.get('success')}")
                    return False
            else:
                self.log_test("Generate Endpoint Basic", False, f"Status code: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Generate Endpoint Basic", False, f"Exception: {str(e)}")
            return False

    def test_vlsm_calculation(self):
        """Test VLSM calculation with different subnet sizes"""
        try:
            payload = {
                "description": "Create 4 networks: 100 hosts, 50 hosts, 25 hosts, and 10 hosts using 192.168.0.0/24"
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") is True:
                    subnets = data.get("subnets", [])
                    
                    if len(subnets) != 4:
                        self.log_test("VLSM Calculation", False, f"Expected 4 subnets, got {len(subnets)}")
                        return False
                    
                    # Check if subnets have proper VLSM allocation (largest first)
                    host_counts = [subnet.get("usable_hosts", 0) for subnet in subnets]
                    
                    # Verify each subnet has enough hosts
                    expected_minimums = [100, 50, 25, 10]
                    for i, (actual, minimum) in enumerate(zip(host_counts, expected_minimums)):
                        if actual < minimum:
                            self.log_test("VLSM Calculation", False, 
                                        f"Subnet {i+1} has {actual} hosts, needs at least {minimum}")
                            return False
                    
                    # Verify subnet structure
                    for i, subnet in enumerate(subnets):
                        required_fields = ["name", "network", "mask", "gateway", "usable_range"]
                        missing = [field for field in required_fields if field not in subnet]
                        if missing:
                            self.log_test("VLSM Calculation", False, 
                                        f"Subnet {i+1} missing fields: {missing}")
                            return False
                    
                    self.log_test("VLSM Calculation", True)
                    return True
                else:
                    error_msg = data.get("error", "Unknown error")
                    self.log_test("VLSM Calculation", False, f"API error: {error_msg}")
                    return False
            else:
                self.log_test("VLSM Calculation", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("VLSM Calculation", False, f"Exception: {str(e)}")
            return False

    def test_cisco_config_generation(self):
        """Test Cisco IOS configuration generation"""
        try:
            payload = {
                "description": "Setup 2 subnets for 30 users each from 172.16.0.0/24 with OSPF routing and 1 router, 2 switches"
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") is True:
                    cli_script = data.get("cli_script", "")
                    
                    # Check for essential Cisco configuration elements
                    required_elements = [
                        "hostname",
                        "interface",
                        "ip address",
                        "no shutdown",
                        "router ospf"  # Should have OSPF since specified
                    ]
                    
                    missing_elements = []
                    for element in required_elements:
                        if element not in cli_script.lower():
                            missing_elements.append(element)
                    
                    if missing_elements:
                        self.log_test("Cisco Config Generation", False, 
                                    f"Missing elements: {missing_elements}")
                        return False
                    
                    # Check for proper structure
                    if len(cli_script) < 500:  # Should be substantial
                        self.log_test("Cisco Config Generation", False, 
                                    f"Config too short: {len(cli_script)} chars")
                        return False
                    
                    self.log_test("Cisco Config Generation", True)
                    return True
                else:
                    error_msg = data.get("error", "Unknown error")
                    self.log_test("Cisco Config Generation", False, f"API error: {error_msg}")
                    return False
            else:
                self.log_test("Cisco Config Generation", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Cisco Config Generation", False, f"Exception: {str(e)}")
            return False

    def test_mistral_integration(self):
        """Test Mistral AI integration with complex description"""
        try:
            payload = {
                "description": "I need a corporate network with a main office subnet for 200 employees, a guest network for 50 devices, a server farm for 20 servers, and a management network for 10 network devices. Use 10.0.0.0/16 as base network with RIP routing protocol."
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=45  # Longer timeout for AI processing
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") is True:
                    config_json = data.get("config_json", {})
                    
                    # Verify AI parsed the description correctly
                    if config_json.get("base_network") != "10.0.0.0/16":
                        self.log_test("Mistral Integration", False, 
                                    f"Wrong base network: {config_json.get('base_network')}")
                        return False
                    
                    if config_json.get("routing_protocol") != "RIP":
                        self.log_test("Mistral Integration", False, 
                                    f"Wrong routing protocol: {config_json.get('routing_protocol')}")
                        return False
                    
                    subnets = data.get("subnets", [])
                    if len(subnets) < 4:  # Should have at least 4 subnets
                        self.log_test("Mistral Integration", False, 
                                    f"Expected at least 4 subnets, got {len(subnets)}")
                        return False
                    
                    # Check CLI has RIP configuration
                    cli_script = data.get("cli_script", "")
                    if "router rip" not in cli_script.lower():
                        self.log_test("Mistral Integration", False, "RIP configuration not found in CLI")
                        return False
                    
                    self.log_test("Mistral Integration", True)
                    return True
                else:
                    error_msg = data.get("error", "Unknown error")
                    self.log_test("Mistral Integration", False, f"API error: {error_msg}")
                    return False
            else:
                self.log_test("Mistral Integration", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Mistral Integration", False, f"Exception: {str(e)}")
            return False

    def test_error_handling(self):
        """Test API error handling"""
        try:
            # Test with invalid/empty description
            payload = {"description": ""}
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Should return 422 for validation error or 200 with success=false
            if response.status_code == 422:
                self.log_test("Error Handling", True)
                return True
            elif response.status_code == 200:
                data = response.json()
                if data.get("success") is False and data.get("error"):
                    self.log_test("Error Handling", True)
                    return True
                else:
                    self.log_test("Error Handling", False, "Should return error for empty description")
                    return False
            else:
                self.log_test("Error Handling", False, f"Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Error Handling", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting NetTrace Backend API Tests")
        print("=" * 50)
        
        # Basic connectivity tests
        if not self.test_health_check():
            print("❌ Health check failed - stopping tests")
            return False
            
        self.test_root_endpoint()
        
        # Core functionality tests
        self.test_generate_endpoint_basic()
        self.test_vlsm_calculation()
        self.test_cisco_config_generation()
        self.test_mistral_integration()
        self.test_error_handling()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    """Main test runner"""
    tester = NetTraceAPITester()
    success = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())