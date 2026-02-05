#!/usr/bin/env python3
"""
Test script to verify the FastAPI base setup.
This script checks that all components are properly configured.
"""

import sys
import requests
import time
import subprocess
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_endpoint(url, expected_status=200, description=""):
    """Test an endpoint and return success status"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == expected_status:
            print(f"{GREEN}✓{RESET} {description}: {url}")
            return True
        else:
            print(f"{RED}✗{RESET} {description}: {url} (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"{RED}✗{RESET} {description}: {url} (Error: {e})")
        return False

def check_file(path, description=""):
    """Check if a file exists"""
    if Path(path).exists():
        print(f"{GREEN}✓{RESET} {description}: {path}")
        return True
    else:
        print(f"{RED}✗{RESET} {description}: {path} (Not found)")
        return False

def main():
    print("=" * 70)
    print("Manga Tracker API - Setup Verification")
    print("=" * 70)

    results = []

    # Check file structure
    print("\n1. Checking File Structure...")
    results.append(check_file("/data/mangataro/api/main.py", "Main application"))
    results.append(check_file("/data/mangataro/api/schemas.py", "Pydantic schemas"))
    results.append(check_file("/data/mangataro/api/dependencies.py", "Dependencies"))
    results.append(check_file("/data/mangataro/api/routers/__init__.py", "Routers package"))
    results.append(check_file("/data/mangataro/api/routers/manga.py", "Manga router"))
    results.append(check_file("/data/mangataro/api/routers/scanlators.py", "Scanlators router"))
    results.append(check_file("/data/mangataro/api/routers/tracking.py", "Tracking router"))
    results.append(check_file("/data/mangataro/scripts/run_api.sh", "Run script"))
    results.append(check_file("/data/mangataro/docs/api_guide.md", "API documentation"))

    # Check if API is running
    print("\n2. Checking API Availability...")
    api_running = test_endpoint("http://localhost:8008/", description="Root endpoint")
    results.append(api_running)

    if api_running:
        results.append(test_endpoint("http://localhost:8008/health", description="Health endpoint"))
        results.append(test_endpoint("http://localhost:8008/docs", description="Swagger UI"))
        results.append(test_endpoint("http://localhost:8008/redoc", description="ReDoc"))
        results.append(test_endpoint("http://localhost:8008/openapi.json", description="OpenAPI spec"))

        # Test root endpoint response
        print("\n3. Checking Endpoint Responses...")
        try:
            response = requests.get("http://localhost:8008/")
            data = response.json()
            if data.get("status") == "ok" and data.get("message") == "Manga Tracker API":
                print(f"{GREEN}✓{RESET} Root endpoint returns correct data")
                results.append(True)
            else:
                print(f"{RED}✗{RESET} Root endpoint returns unexpected data")
                results.append(False)
        except Exception as e:
            print(f"{RED}✗{RESET} Error testing root endpoint: {e}")
            results.append(False)

        # Test health endpoint response
        try:
            response = requests.get("http://localhost:8008/health")
            data = response.json()
            if data.get("status") == "healthy":
                print(f"{GREEN}✓{RESET} Health endpoint returns correct data")
                results.append(True)
            else:
                print(f"{RED}✗{RESET} Health endpoint returns unexpected data")
                results.append(False)
        except Exception as e:
            print(f"{RED}✗{RESET} Error testing health endpoint: {e}")
            results.append(False)
    else:
        print(f"{YELLOW}!{RESET} API is not running. Start it with: ./scripts/run_api.sh")
        print(f"{YELLOW}!{RESET} Skipping endpoint tests...")

    # Summary
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")

    if passed == total:
        print(f"{GREEN}All checks passed! FastAPI setup is complete.{RESET}")
        return 0
    else:
        print(f"{YELLOW}Some checks failed. Review the output above.{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
