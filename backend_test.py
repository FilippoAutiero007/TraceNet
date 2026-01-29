#!/usr/bin/env python3
"""
NetTrace Backend API Testing Suite
Tests all API endpoints and functionality
"""

import requests
import sys
import json
from datetime import datetime

class NetTraceAPITester:
    def __init__(self, base_url="https://ae3b09ff-0c74-4b9a-b93d-e3b6cb1b32d4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout}s")
            self.failed_tests.append({'name': name, 'error': 'Timeout'})
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({'name': name, 'error': str(e)})
            return False, {}

    def test_health_endpoint(self):
        """Test GET /api/health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        
        if success:
            # Verify response structure
            if isinstance(response, dict) and 'status' in response:
                if response['status'] == 'healthy':
                    print("   ✅ Health status is 'healthy'")
                    return True
                else:
                    print(f"   ⚠️  Health status is '{response.get('status')}', expected 'healthy'")
            else:
                print("   ⚠️  Invalid health response structure")
        
        return success

    def test_generate_endpoint_simple(self):
        """Test POST /api/generate with simple description"""
        test_description = "Create 2 subnets with 30 hosts each from 192.168.1.0/24"
        
        success, response = self.run_test(
            "Generate Network - Simple",
            "POST",
            "api/generate",
            200,
            data={"description": test_description},
            timeout=60  # Longer timeout for AI processing
        )
        
        if success and isinstance(response, dict):
            # Verify response structure
            required_fields = ['success', 'config_json', 'subnets', 'cli_script']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
                return False
            
            if response.get('success'):
                print("   ✅ Generation successful")
                
                # Check config_json
                config = response.get('config_json')
                if config and 'base_network' in config:
                    print(f"   ✅ Base network: {config['base_network']}")
                
                # Check subnets
                subnets = response.get('subnets')
                if subnets and len(subnets) > 0:
                    print(f"   ✅ Generated {len(subnets)} subnets")
                    for i, subnet in enumerate(subnets[:2]):  # Show first 2
                        print(f"      Subnet {i+1}: {subnet.get('name')} - {subnet.get('network')}")
                
                # Check CLI script
                cli_script = response.get('cli_script')
                if cli_script and len(cli_script) > 100:
                    print(f"   ✅ CLI script generated ({len(cli_script)} characters)")
                
                return True
            else:
                error = response.get('error', 'Unknown error')
                print(f"   ❌ Generation failed: {error}")
                return False
        
        return success

    def test_generate_endpoint_complex(self):
        """Test POST /api/generate with complex description"""
        test_description = "I need 4 networks: 100 hosts, 50 hosts, 25 hosts, and 10 hosts using 10.0.0.0/16 with OSPF routing and 2 routers and 3 switches"
        
        success, response = self.run_test(
            "Generate Network - Complex",
            "POST",
            "api/generate",
            200,
            data={"description": test_description},
            timeout=60
        )
        
        if success and isinstance(response, dict) and response.get('success'):
            config = response.get('config_json', {})
            
            # Check routing protocol
            routing = config.get('routing_protocol')
            if routing and routing.upper() == 'OSPF':
                print("   ✅ OSPF routing protocol detected")
            
            # Check devices
            devices = config.get('devices', {})
            if devices.get('routers') >= 2:
                print(f"   ✅ Routers: {devices.get('routers')}")
            if devices.get('switches') >= 3:
                print(f"   ✅ Switches: {devices.get('switches')}")
            
            # Check subnets count
            subnets = response.get('subnets', [])
            if len(subnets) >= 4:
                print(f"   ✅ Generated {len(subnets)} subnets as requested")
            
            return True
        
        return success

    def test_generate_endpoint_invalid(self):
        """Test POST /api/generate with invalid input"""
        success, response = self.run_test(
            "Generate Network - Invalid Input",
            "POST",
            "api/generate",
            200,  # API returns 200 with success=false for validation errors
            data={"description": "xyz"}  # Too short/invalid
        )
        
        if success and isinstance(response, dict):
            if not response.get('success') and 'error' in response:
                print("   ✅ Properly handled invalid input")
                return True
        
        return False

    def test_root_endpoint(self):
        """Test GET /api endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "api",
            200
        )
        return success

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"📊 TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"   - {test['name']}: {test.get('error', f\"Expected {test.get('expected')}, got {test.get('actual')}\")}")
        
        return self.tests_passed == self.tests_run

def main():
    print("🚀 Starting NetTrace Backend API Tests")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = NetTraceAPITester()
    
    # Run all tests
    tests = [
        tester.test_health_endpoint,
        tester.test_root_endpoint,
        tester.test_generate_endpoint_simple,
        tester.test_generate_endpoint_complex,
        tester.test_generate_endpoint_invalid
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            tester.failed_tests.append({'name': test.__name__, 'error': f'Crashed: {e}'})
    
    # Print summary
    all_passed = tester.print_summary()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())