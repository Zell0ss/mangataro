#!/usr/bin/env python3
"""
Manual Tracking Test Script

This script mimics the n8n workflow for testing chapter tracking.
Useful for debugging when adding new scanlators or testing tracking jobs.

Usage:
    python test_tracking.py                           # Track all verified manga
    python test_tracking.py --manga-id 60             # Track specific manga
    python test_tracking.py --scanlator-id 3          # Track specific scanlator
    python test_tracking.py --no-notify               # Don't send notifications
    python test_tracking.py --manga-id 60 --verbose   # Show detailed progress
"""

import argparse
import requests
import time
import sys
from typing import Optional, Dict, Any
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class TrackingTester:
    """Test harness for chapter tracking API"""

    def __init__(self, api_url: str = "http://localhost:8008", verbose: bool = False):
        self.api_url = api_url
        self.verbose = verbose

    def log(self, message: str, color: str = ""):
        """Print colored log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if color:
            print(f"{Colors.CYAN}[{timestamp}]{Colors.END} {color}{message}{Colors.END}")
        else:
            print(f"{Colors.CYAN}[{timestamp}]{Colors.END} {message}")

    def log_error(self, message: str):
        """Print error message"""
        self.log(f"❌ ERROR: {message}", Colors.RED)

    def log_success(self, message: str):
        """Print success message"""
        self.log(f"✅ {message}", Colors.GREEN)

    def log_info(self, message: str):
        """Print info message"""
        self.log(f"ℹ️  {message}", Colors.BLUE)

    def log_warning(self, message: str):
        """Print warning message"""
        self.log(f"⚠️  {message}", Colors.YELLOW)

    def check_api_health(self) -> bool:
        """Check if API is running"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_success("API is healthy and responding")
                return True
            else:
                self.log_error(f"API returned status code {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.log_error(f"Cannot connect to API at {self.api_url}")
            self.log_info("Make sure the API is running: uvicorn api.main:app --reload")
            return False
        except Exception as e:
            self.log_error(f"Health check failed: {e}")
            return False

    def trigger_tracking(
        self,
        manga_id: Optional[int] = None,
        scanlator_id: Optional[int] = None,
        notify: bool = True
    ) -> Optional[str]:
        """
        Trigger a tracking job.

        Returns:
            Job ID if successful, None otherwise
        """
        endpoint = f"{self.api_url}/api/tracking/trigger"
        payload = {
            "manga_id": manga_id,
            "scanlator_id": scanlator_id,
            "notify": notify
        }

        # Build description of what we're tracking
        tracking_desc = []
        if manga_id:
            tracking_desc.append(f"manga_id={manga_id}")
        if scanlator_id:
            tracking_desc.append(f"scanlator_id={scanlator_id}")
        if not tracking_desc:
            tracking_desc.append("all verified manga")

        self.log(f"🚀 Triggering tracking job ({', '.join(tracking_desc)})...", Colors.BOLD)
        if not notify:
            self.log_info("Notifications disabled for this run")

        try:
            response = requests.post(endpoint, json=payload, timeout=10)

            if response.status_code == 202:
                data = response.json()
                job_id = data.get("job_id")
                self.log_success(f"Tracking job triggered successfully")
                self.log_info(f"Job ID: {job_id}")
                return job_id
            else:
                self.log_error(f"Failed to trigger tracking: {response.status_code}")
                self.log_error(f"Response: {response.text}")
                return None

        except Exception as e:
            self.log_error(f"Failed to trigger tracking: {e}")
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a job"""
        endpoint = f"{self.api_url}/api/tracking/jobs/{job_id}"

        try:
            response = requests.get(endpoint, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                self.log_error(f"Job {job_id} not found")
                return None
            else:
                self.log_error(f"Failed to get job status: {response.status_code}")
                return None

        except Exception as e:
            self.log_error(f"Failed to get job status: {e}")
            return None

    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 10,
        max_wait: int = 600
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for job to complete, polling at regular intervals.

        Args:
            job_id: The job ID to monitor
            poll_interval: Seconds between polls (default: 10)
            max_wait: Maximum seconds to wait (default: 600 = 10 minutes)

        Returns:
            Final job status or None if timeout/error
        """
        self.log(f"⏳ Waiting for job to complete (polling every {poll_interval}s)...", Colors.BOLD)

        start_time = time.time()
        attempt = 0

        while True:
            elapsed = int(time.time() - start_time)

            # Check timeout
            if elapsed > max_wait:
                self.log_error(f"Job timed out after {max_wait}s")
                return None

            # Get status
            status = self.get_job_status(job_id)
            if status is None:
                return None

            attempt += 1
            job_status = status.get("status", "unknown")
            processed = status.get("processed_mappings", 0)
            total = status.get("total_mappings", 0)
            new_chapters = status.get("new_chapters_found", 0)

            # Progress indicator
            if total > 0:
                progress = f"{processed}/{total}"
                percentage = int((processed / total) * 100)
                progress_bar = "█" * (percentage // 5) + "░" * (20 - percentage // 5)
                self.log(
                    f"📊 Status: {job_status} | Progress: {progress} [{progress_bar}] {percentage}%",
                    Colors.CYAN
                )
            else:
                self.log(f"📊 Status: {job_status}", Colors.CYAN)

            if self.verbose and new_chapters > 0:
                self.log_info(f"New chapters found so far: {new_chapters}")

            # Check if done
            if job_status == "completed":
                self.log_success(f"Job completed successfully in {elapsed}s")
                return status
            elif job_status == "failed":
                self.log_error("Job failed")
                return status

            # Wait before next poll
            if self.verbose:
                self.log(f"⏸️  Waiting {poll_interval}s before next poll...", Colors.CYAN)
            time.sleep(poll_interval)

    def display_results(self, final_status: Dict[str, Any]):
        """Display final job results in a nice format"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}📋 TRACKING JOB RESULTS{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

        # Job info
        job_id = final_status.get("job_id", "unknown")
        status = final_status.get("status", "unknown")
        started_at = final_status.get("started_at", "N/A")
        completed_at = final_status.get("completed_at", "N/A")

        print(f"{Colors.CYAN}Job ID:{Colors.END}         {job_id}")
        print(f"{Colors.CYAN}Status:{Colors.END}         {status}")
        print(f"{Colors.CYAN}Started At:{Colors.END}     {started_at}")
        print(f"{Colors.CYAN}Completed At:{Colors.END}   {completed_at}")
        print()

        # Statistics
        total = final_status.get("total_mappings", 0)
        processed = final_status.get("processed_mappings", 0)
        new_chapters = final_status.get("new_chapters_found", 0)

        print(f"{Colors.CYAN}Mappings Processed:{Colors.END}  {processed}/{total}")

        if new_chapters > 0:
            print(f"{Colors.GREEN}New Chapters Found:{Colors.END}  {new_chapters} 🎉")
        else:
            print(f"{Colors.YELLOW}New Chapters Found:{Colors.END}  0 (No new chapters)")
        print()

        # Errors
        errors = final_status.get("errors", [])
        if errors:
            print(f"{Colors.RED}Errors ({len(errors)}):{Colors.END}")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
            print()
        else:
            print(f"{Colors.GREEN}Errors:{Colors.END} None ✅\n")

        # Summary
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

        if status == "completed" and new_chapters > 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✨ Success! Found {new_chapters} new chapter(s){Colors.END}\n")
        elif status == "completed":
            print(f"{Colors.YELLOW}{Colors.BOLD}✅ Completed - No new chapters found{Colors.END}\n")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ Job failed - See errors above{Colors.END}\n")

    def run(
        self,
        manga_id: Optional[int] = None,
        scanlator_id: Optional[int] = None,
        notify: bool = True,
        poll_interval: int = 10,
        max_wait: int = 600
    ):
        """
        Run the complete tracking test workflow.

        This mimics the n8n workflow:
        1. Check API health
        2. Trigger tracking job
        3. Poll for completion
        4. Display results
        """
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
        print("  MANGATARO TRACKING TEST SCRIPT")
        print(f"{'='*60}{Colors.END}\n")

        # Step 1: Health check
        if not self.check_api_health():
            sys.exit(1)

        print()

        # Step 2: Trigger tracking
        job_id = self.trigger_tracking(manga_id, scanlator_id, notify)
        if not job_id:
            sys.exit(1)

        print()

        # Step 3: Wait for completion
        final_status = self.wait_for_completion(job_id, poll_interval, max_wait)
        if not final_status:
            sys.exit(1)

        # Step 4: Display results
        self.display_results(final_status)

        # Exit code based on result
        if final_status.get("status") == "completed":
            sys.exit(0)
        else:
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Test chapter tracking by calling the same API endpoints as n8n workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_tracking.py                           # Track all verified manga
  python test_tracking.py --manga-id 60             # Track specific manga
  python test_tracking.py --scanlator-id 3          # Track specific scanlator
  python test_tracking.py --no-notify               # Don't send notifications
  python test_tracking.py --manga-id 60 --verbose   # Show detailed progress
  python test_tracking.py --api-url http://192.168.1.100:8008  # Custom API URL
        """
    )

    parser.add_argument(
        "--manga-id",
        type=int,
        help="Track only this manga ID"
    )

    parser.add_argument(
        "--scanlator-id",
        type=int,
        help="Track only this scanlator ID"
    )

    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Disable Discord notifications for this run"
    )

    parser.add_argument(
        "--api-url",
        default="http://localhost:8008",
        help="API base URL (default: http://localhost:8008)"
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between status polls (default: 10)"
    )

    parser.add_argument(
        "--max-wait",
        type=int,
        default=600,
        help="Maximum seconds to wait for job completion (default: 600)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress information"
    )

    args = parser.parse_args()

    # Create tester instance
    tester = TrackingTester(api_url=args.api_url, verbose=args.verbose)

    # Run the test
    tester.run(
        manga_id=args.manga_id,
        scanlator_id=args.scanlator_id,
        notify=not args.no_notify,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait
    )


if __name__ == "__main__":
    main()
