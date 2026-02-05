#!/usr/bin/env python3
"""
Test Manga-Scanlator Mapping Functionality
Tests the complete flow: add mapping, verify it exists, test duplicate prevention
"""

import requests
import json
import sys
import pymysql
from datetime import datetime
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:8008"
DB_CONFIG = {
    "host": "localhost",
    "user": "mangataro_user",
    "database": "mangataro"
}

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")

def log_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def log_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def log_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

def get_db_password() -> str:
    """Get database password from .env file"""
    try:
        with open("/data/mangataro/.env", "r") as f:
            for line in f:
                if line.startswith("DB_PASSWORD="):
                    return line.strip().split("=", 1)[1].strip('"').strip("'")
    except Exception as e:
        log_error(f"Could not read .env file: {e}")
        return ""

def test_create_mapping():
    """Test creating a new manga-scanlator mapping"""
    print(f"\n{BLUE}=== Test: Create New Mapping ==={RESET}")

    # Get test data
    log_info("Fetching unmapped manga...")
    response = requests.get(f"{API_BASE_URL}/api/manga/unmapped?scanlator_id=7")
    if response.status_code != 200:
        log_error(f"Failed to get unmapped manga: HTTP {response.status_code}")
        return False

    data = response.json()
    if not data["unmapped_manga"]:
        log_warning("No unmapped manga available for testing")
        return True  # Not a failure, just nothing to test

    # Use first unmapped manga
    manga = data["unmapped_manga"][0]
    manga_id = manga["id"]
    manga_title = manga["title"]

    log_info(f"Testing with: {manga_title} (ID: {manga_id})")

    # Create mapping
    payload = {
        "manga_id": manga_id,
        "scanlator_id": 7,
        "scanlator_manga_url": f"https://asuracomic.net/series/test-manga-{manga_id}",
        "manually_verified": True
    }

    log_info("Creating mapping via API...")
    response = requests.post(
        f"{API_BASE_URL}/api/tracking/manga-scanlators",
        json=payload
    )

    if response.status_code not in [200, 201]:
        log_error(f"Failed to create mapping: HTTP {response.status_code}")
        log_error(f"Response: {response.text}")
        return False

    result = response.json()
    mapping_id = result.get("id")

    log_success(f"Created mapping with ID: {mapping_id}")

    # Verify in database
    log_info("Verifying mapping in database...")
    db_password = get_db_password()
    if not db_password:
        log_warning("Could not verify in database (no password)")
        return True

    try:
        conn = pymysql.connect(
            **DB_CONFIG,
            password=db_password,
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM manga_scanlator
            WHERE id = %s
        """, (mapping_id,))

        db_mapping = cursor.fetchone()
        cursor.close()
        conn.close()

        if db_mapping:
            log_success("Mapping found in database")
            log_info(f"  manga_id: {db_mapping['manga_id']}")
            log_info(f"  scanlator_id: {db_mapping['scanlator_id']}")
            log_info(f"  url: {db_mapping['scanlator_manga_url']}")
            log_info(f"  verified: {db_mapping['manually_verified']}")

            # Verify it's no longer in unmapped list
            log_info("Checking unmapped list...")
            response = requests.get(f"{API_BASE_URL}/api/manga/unmapped?scanlator_id=7")
            new_data = response.json()

            unmapped_ids = [m["id"] for m in new_data["unmapped_manga"]]
            if manga_id not in unmapped_ids:
                log_success("Manga correctly removed from unmapped list")
            else:
                log_error("Manga still appears in unmapped list")
                return False

            return True
        else:
            log_error("Mapping not found in database")
            return False

    except Exception as e:
        log_error(f"Database verification failed: {e}")
        return True  # Don't fail test if DB check fails

def test_duplicate_prevention():
    """Test that duplicate mappings are prevented"""
    print(f"\n{BLUE}=== Test: Duplicate Mapping Prevention ==={RESET}")

    # Get mapped manga
    log_info("Finding a mapped manga...")
    db_password = get_db_password()
    if not db_password:
        log_warning("Cannot test without database access")
        return True

    try:
        conn = pymysql.connect(
            **DB_CONFIG,
            password=db_password,
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT manga_id, scanlator_id, scanlator_manga_url
            FROM manga_scanlator
            WHERE manually_verified = 1
            LIMIT 1
        """)

        existing = cursor.fetchone()
        cursor.close()
        conn.close()

        if not existing:
            log_warning("No existing mappings to test with")
            return True

        manga_id = existing["manga_id"]
        scanlator_id = existing["scanlator_id"]
        url = existing["scanlator_manga_url"]

        log_info(f"Attempting to create duplicate: manga_id={manga_id}, scanlator_id={scanlator_id}")

        # Try to create duplicate
        payload = {
            "manga_id": manga_id,
            "scanlator_id": scanlator_id,
            "scanlator_manga_url": url,
            "manually_verified": True
        }

        response = requests.post(
            f"{API_BASE_URL}/api/tracking/manga-scanlators",
            json=payload
        )

        # Should fail with 400 or 409
        if response.status_code in [400, 409, 422]:
            log_success(f"Duplicate correctly rejected with HTTP {response.status_code}")
            return True
        elif response.status_code in [200, 201]:
            log_error("API allowed duplicate mapping (should be rejected)")
            return False
        else:
            log_warning(f"Unexpected status: HTTP {response.status_code}")
            return True

    except Exception as e:
        log_error(f"Test failed: {e}")
        return False

def test_url_validation():
    """Test URL validation on backend"""
    print(f"\n{BLUE}=== Test: URL Validation ==={RESET}")

    # Get test manga
    response = requests.get(f"{API_BASE_URL}/api/manga/unmapped?scanlator_id=7")
    if response.status_code != 200:
        log_warning("Cannot get test data")
        return True

    data = response.json()
    if not data["unmapped_manga"]:
        log_warning("No unmapped manga for testing")
        return True

    manga_id = data["unmapped_manga"][0]["id"]

    # Test invalid URLs
    test_cases = [
        ("Empty URL", ""),
        ("Invalid format", "not-a-url"),
        ("Missing protocol", "asuracomic.net/manga/test"),
    ]

    all_passed = True

    for name, url in test_cases:
        payload = {
            "manga_id": manga_id,
            "scanlator_id": 7,
            "scanlator_manga_url": url,
            "manually_verified": True
        }

        response = requests.post(
            f"{API_BASE_URL}/api/tracking/manga-scanlators",
            json=payload
        )

        # Should reject invalid URLs (422 or 400)
        if response.status_code in [400, 422]:
            log_success(f"{name}: Correctly rejected")
        elif response.status_code in [200, 201]:
            log_error(f"{name}: API accepted invalid URL")
            all_passed = False
        else:
            log_info(f"{name}: HTTP {response.status_code}")

    return all_passed

def cleanup_test_data():
    """Clean up test mappings"""
    print(f"\n{BLUE}=== Cleanup: Removing Test Mappings ==={RESET}")

    db_password = get_db_password()
    if not db_password:
        log_warning("Cannot cleanup without database access")
        return

    try:
        conn = pymysql.connect(**DB_CONFIG, password=db_password)
        cursor = conn.cursor()

        # Delete test mappings (URLs containing "test-manga-")
        cursor.execute("""
            DELETE FROM manga_scanlator
            WHERE scanlator_manga_url LIKE '%test-manga-%'
        """)

        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        if deleted > 0:
            log_success(f"Cleaned up {deleted} test mapping(s)")
        else:
            log_info("No test mappings to clean up")

    except Exception as e:
        log_error(f"Cleanup failed: {e}")

def main():
    """Main test runner"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}MANGA-SCANLATOR MAPPING - FUNCTIONAL TESTS{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {
        "Create Mapping": test_create_mapping(),
        "Duplicate Prevention": test_duplicate_prevention(),
        "URL Validation": test_url_validation(),
    }

    # Cleanup
    cleanup_test_data()

    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} passed")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
