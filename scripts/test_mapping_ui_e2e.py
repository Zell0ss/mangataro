#!/usr/bin/env python3
"""
End-to-End Test Script for Manga-Scanlator Mapping UI Feature
Tests all API endpoints and validates responses.
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

# Configuration
API_BASE_URL = "http://localhost:8008"
FRONTEND_URL = "http://localhost:4343"

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class TestResult:
    """Test result container"""
    def __init__(self, name: str, passed: bool, message: str, details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
        self.timestamp = datetime.now()

class E2ETestRunner:
    """End-to-end test runner for mapping UI"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.scanlator_id = None
        self.test_manga_id = None

    def log_success(self, message: str):
        """Print success message"""
        print(f"{GREEN}✓{RESET} {message}")

    def log_error(self, message: str):
        """Print error message"""
        print(f"{RED}✗{RESET} {message}")

    def log_info(self, message: str):
        """Print info message"""
        print(f"{BLUE}ℹ{RESET} {message}")

    def log_warning(self, message: str):
        """Print warning message"""
        print(f"{YELLOW}⚠{RESET} {message}")

    def add_result(self, name: str, passed: bool, message: str, details: str = ""):
        """Add test result"""
        result = TestResult(name, passed, message, details)
        self.results.append(result)

        if passed:
            self.log_success(f"{name}: {message}")
        else:
            self.log_error(f"{name}: {message}")

        if details:
            print(f"  Details: {details}")

    def test_api_health(self) -> bool:
        """Test 1: API Health Check"""
        print(f"\n{BLUE}=== Test 1: API Health Check ==={RESET}")

        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.add_result("API Health", True, "API is operational")
                    return True
                else:
                    self.add_result("API Health", False, f"Unexpected status: {data}")
                    return False
            else:
                self.add_result("API Health", False, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.add_result("API Health", False, f"Connection failed: {e}")
            return False

    def test_get_scanlators(self) -> bool:
        """Test 2: Get Scanlators Endpoint"""
        print(f"\n{BLUE}=== Test 2: Get Scanlators Endpoint ==={RESET}")

        try:
            response = requests.get(f"{API_BASE_URL}/api/scanlators/", timeout=5)

            if response.status_code == 200:
                scanlators = response.json()

                if not isinstance(scanlators, list):
                    self.add_result("Get Scanlators", False, "Response is not a list")
                    return False

                if len(scanlators) == 0:
                    self.add_result("Get Scanlators", False, "No scanlators found",
                                  "Need at least one active scanlator to test")
                    return False

                # Store first scanlator ID for later tests
                self.scanlator_id = scanlators[0]["id"]
                scanlator_name = scanlators[0]["name"]

                self.add_result("Get Scanlators", True,
                              f"Found {len(scanlators)} scanlator(s)",
                              f"Using scanlator: {scanlator_name} (ID: {self.scanlator_id})")
                return True
            else:
                self.add_result("Get Scanlators", False, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.add_result("Get Scanlators", False, f"Request failed: {e}")
            return False

    def test_get_unmapped_manga(self) -> bool:
        """Test 3: Get Unmapped Manga Endpoint"""
        print(f"\n{BLUE}=== Test 3: Get Unmapped Manga Endpoint ==={RESET}")

        if not self.scanlator_id:
            self.add_result("Get Unmapped Manga", False, "No scanlator ID available")
            return False

        try:
            url = f"{API_BASE_URL}/api/manga/unmapped?scanlator_id={self.scanlator_id}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                required_fields = ["scanlator_id", "scanlator_name", "base_url", "unmapped_manga", "count"]
                missing_fields = [f for f in required_fields if f not in data]

                if missing_fields:
                    self.add_result("Get Unmapped Manga", False,
                                  "Invalid response structure",
                                  f"Missing fields: {missing_fields}")
                    return False

                # Validate data types
                if not isinstance(data["unmapped_manga"], list):
                    self.add_result("Get Unmapped Manga", False,
                                  "unmapped_manga is not a list")
                    return False

                if data["count"] != len(data["unmapped_manga"]):
                    self.add_result("Get Unmapped Manga", False,
                                  f"Count mismatch: count={data['count']}, actual={len(data['unmapped_manga'])}")
                    return False

                # Store first manga ID for later tests
                if data["unmapped_manga"]:
                    self.test_manga_id = data["unmapped_manga"][0]["id"]
                    manga_title = data["unmapped_manga"][0]["title"]

                    self.add_result("Get Unmapped Manga", True,
                                  f"Found {data['count']} unmapped manga",
                                  f"Test manga: {manga_title} (ID: {self.test_manga_id})")
                else:
                    self.add_result("Get Unmapped Manga", True,
                                  "All manga are mapped (empty state)",
                                  "Cannot test mapping without unmapped manga")

                return True
            else:
                self.add_result("Get Unmapped Manga", False,
                              f"HTTP {response.status_code}",
                              response.text)
                return False

        except Exception as e:
            self.add_result("Get Unmapped Manga", False, f"Request failed: {e}")
            return False

    def test_invalid_scanlator_id(self) -> bool:
        """Test 4: Get Unmapped with Invalid Scanlator ID"""
        print(f"\n{BLUE}=== Test 4: Invalid Scanlator ID Handling ==={RESET}")

        try:
            # Use a non-existent scanlator ID
            url = f"{API_BASE_URL}/api/manga/unmapped?scanlator_id=99999"
            response = requests.get(url, timeout=5)

            # Should return 404 or 422
            if response.status_code in [404, 422]:
                self.add_result("Invalid Scanlator ID", True,
                              f"Correctly returned HTTP {response.status_code}",
                              "API properly validates scanlator ID")
                return True
            else:
                self.add_result("Invalid Scanlator ID", False,
                              f"Unexpected status: HTTP {response.status_code}",
                              "Expected 404 or 422 for invalid scanlator ID")
                return False

        except Exception as e:
            self.add_result("Invalid Scanlator ID", False, f"Request failed: {e}")
            return False

    def test_missing_scanlator_param(self) -> bool:
        """Test 5: Get Unmapped without Scanlator ID Parameter"""
        print(f"\n{BLUE}=== Test 5: Missing Scanlator ID Parameter ==={RESET}")

        try:
            url = f"{API_BASE_URL}/api/manga/unmapped"
            response = requests.get(url, timeout=5)

            # Should return 422 (validation error)
            if response.status_code == 422:
                self.add_result("Missing Scanlator Param", True,
                              "Correctly returned HTTP 422",
                              "API properly validates required parameters")
                return True
            else:
                self.add_result("Missing Scanlator Param", False,
                              f"Unexpected status: HTTP {response.status_code}",
                              "Expected 422 for missing required parameter")
                return False

        except Exception as e:
            self.add_result("Missing Scanlator Param", False, f"Request failed: {e}")
            return False

    def test_frontend_page_loads(self) -> bool:
        """Test 6: Frontend Admin Page Loads"""
        print(f"\n{BLUE}=== Test 6: Frontend Admin Page ==={RESET}")

        try:
            response = requests.get(f"{FRONTEND_URL}/admin/map-sources", timeout=5)

            if response.status_code == 200:
                html = response.text

                # Check for key elements in HTML
                checks = [
                    ("Title tag", "Map Manga Sources" in html),
                    ("Scanlator dropdown", 'id="scanlator-select"' in html),
                    ("Alpine.js data", "x-data" in html),
                    ("API integration", "addMapping" in html),
                    ("Layout", "max-w-4xl" in html),
                ]

                failed_checks = [name for name, result in checks if not result]

                if failed_checks:
                    self.add_result("Frontend Page", False,
                                  "HTML missing expected elements",
                                  f"Missing: {', '.join(failed_checks)}")
                    return False

                self.add_result("Frontend Page", True,
                              "Page loads with all expected elements",
                              f"HTML size: {len(html)} bytes")
                return True
            else:
                self.add_result("Frontend Page", False,
                              f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.add_result("Frontend Page", False, f"Request failed: {e}")
            return False

    def test_post_mapping_validation(self) -> bool:
        """Test 7: POST Mapping with Invalid Data"""
        print(f"\n{BLUE}=== Test 7: POST Mapping Validation ==={RESET}")

        try:
            # Test with missing required fields
            url = f"{API_BASE_URL}/api/tracking/manga-scanlators"
            invalid_payload = {
                "manga_id": 1,
                # Missing scanlator_id, scanlator_manga_url, manually_verified
            }

            response = requests.post(url, json=invalid_payload, timeout=5)

            # Should return 422 (validation error)
            if response.status_code == 422:
                self.add_result("POST Validation", True,
                              "Correctly rejected invalid payload",
                              "API validates required fields")
                return True
            else:
                self.add_result("POST Validation", False,
                              f"Unexpected status: HTTP {response.status_code}",
                              "Expected 422 for missing required fields")
                return False

        except Exception as e:
            self.add_result("POST Validation", False, f"Request failed: {e}")
            return False

    def test_url_validation_in_component(self) -> bool:
        """Test 8: URL Validation Logic (Code Review)"""
        print(f"\n{BLUE}=== Test 8: URL Validation Logic ==={RESET}")

        self.log_info("Testing URL validation patterns...")

        # Read the frontend page to verify validation logic
        try:
            with open("/data/mangataro/frontend/src/pages/admin/map-sources.astro", "r") as f:
                content = f.read()

            validation_checks = [
                ("HTTP/HTTPS check", "http:" in content and "https:" in content),
                ("URL constructor", "new URL" in content),
                ("Base URL matching", "baseUrl" in content and "includes" in content),
                ("Error messages", 'this.error = ' in content),
                ("isValid flag", "isValid" in content),
            ]

            failed_checks = [name for name, result in validation_checks if not result]

            if failed_checks:
                self.add_result("URL Validation Logic", False,
                              "Validation logic incomplete",
                              f"Missing: {', '.join(failed_checks)}")
                return False

            self.add_result("URL Validation Logic", True,
                          "All validation checks present in code",
                          "Protocol, format, and domain validation implemented")
            return True

        except Exception as e:
            self.add_result("URL Validation Logic", False, f"Could not read file: {e}")
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}")
        print(f"Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%\n")

        if failed > 0:
            print(f"{RED}Failed Tests:{RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}: {result.message}")

        print()
        return failed == 0

    def run_all_tests(self):
        """Run all test scenarios"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}MANGA-SCANLATOR MAPPING UI - E2E TEST SUITE{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API: {API_BASE_URL}")
        print(f"Frontend: {FRONTEND_URL}")

        # Run tests in sequence
        tests = [
            self.test_api_health,
            self.test_get_scanlators,
            self.test_get_unmapped_manga,
            self.test_invalid_scanlator_id,
            self.test_missing_scanlator_param,
            self.test_frontend_page_loads,
            self.test_post_mapping_validation,
            self.test_url_validation_in_component,
        ]

        for test_func in tests:
            test_func()

        # Print summary
        success = self.print_summary()

        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        return success

def main():
    """Main entry point"""
    runner = E2ETestRunner()
    success = runner.run_all_tests()

    if not success:
        print(f"{RED}Some tests failed. See details above.{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}All tests passed!{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
