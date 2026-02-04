# MangaTaro Remaining Tasks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the MangaTaro project by adding advanced tracking API endpoints, n8n automation workflows, and comprehensive documentation.

**Architecture:** Extend the existing FastAPI backend with tracking trigger endpoints and status monitoring, create n8n workflows for scheduled tracking and notifications, and write user/developer documentation.

**Tech Stack:** FastAPI, n8n, Discord webhooks, Python asyncio, systemd (optional)

---

## Prerequisites

**Verify environment is ready:**

```bash
# Check API is accessible
curl http://localhost:8008/health

# Check frontend is running
curl http://localhost:4343/

# Verify database has data
mysql -u mangataro_user -p -e "SELECT COUNT(*) FROM mangataro.mangas;"

# Check tracking script works
python scripts/track_chapters.py --limit 1 --visible
```

**Expected:** API responds, frontend loads, database has 94 manga, tracking script executes successfully.

---

## Task 9: Advanced Tracking API (2-3 hours)

**Goal:** Add API endpoints to trigger tracking runs, monitor status, and support webhook notifications.

**Files:**
- Modify: `api/routers/tracking.py`
- Modify: `api/schemas.py`
- Create: `api/services/tracker_service.py`
- Create: `api/services/notification_service.py`
- Modify: `requirements.txt`

---

### Step 9.1: Add notification service dependencies

**Action:** Add httpx and Discord webhook support to requirements.

**File:** `requirements.txt`

```text
# Add after existing packages
httpx==0.27.0
python-dotenv==1.0.1  # Already present, verify
```

**Command:**

```bash
pip install httpx==0.27.0
```

**Expected:** Package installed successfully.

---

### Step 9.2: Create notification service

**Action:** Create a service to send Discord/email notifications.

**File:** `api/services/notification_service.py` (create new)

```python
"""
Notification Service

Sends notifications for new chapters via Discord webhooks or email.
"""

import os
import httpx
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime


class NotificationService:
    """Handles notifications for new chapters."""

    def __init__(self):
        self.notification_type = os.getenv("NOTIFICATION_TYPE", "discord")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    async def notify_new_chapters(self, chapters: List[Dict]) -> bool:
        """
        Send notification for new chapters.

        Args:
            chapters: List of chapter dictionaries with manga_title, chapter_number, url

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not chapters:
            logger.info("No new chapters to notify")
            return True

        if self.notification_type == "discord":
            return await self._notify_discord(chapters)
        else:
            logger.warning(f"Notification type '{self.notification_type}' not implemented")
            return False

    async def _notify_discord(self, chapters: List[Dict]) -> bool:
        """Send Discord webhook notification."""
        if not self.discord_webhook_url:
            logger.warning("Discord webhook URL not configured, skipping notification")
            return False

        # Build embed message
        embeds = []

        for chapter in chapters[:10]:  # Limit to 10 chapters per notification
            embed = {
                "title": f"{chapter['manga_title']} - Chapter {chapter['chapter_number']}",
                "url": chapter.get("url", ""),
                "description": chapter.get("title", "New chapter available"),
                "color": 0x00ff00,  # Green
                "timestamp": chapter.get("detected_date", datetime.utcnow()).isoformat(),
                "footer": {
                    "text": f"Scanlator: {chapter.get('scanlator_name', 'Unknown')}"
                }
            }
            embeds.append(embed)

        # Add summary if more than 10 chapters
        if len(chapters) > 10:
            embeds.append({
                "title": "📚 And more...",
                "description": f"{len(chapters) - 10} additional chapters detected",
                "color": 0x0099ff
            })

        payload = {
            "content": f"🆕 **{len(chapters)} new chapter(s) detected!**",
            "embeds": embeds
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.discord_webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"Discord notification sent for {len(chapters)} chapters")
                return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False


# Singleton instance
_notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get the notification service singleton."""
    return _notification_service
```

**Commit:**

```bash
git add requirements.txt api/services/notification_service.py
git commit -m "feat(api): add notification service for Discord webhooks"
```

---

### Step 9.3: Create tracker service with background job support

**Action:** Create a service that wraps track_chapters.py as an async background job.

**File:** `api/services/tracker_service.py` (create new)

```python
"""
Tracker Service

Manages background tracking jobs and provides status monitoring.
"""

import asyncio
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload

from api.database import SessionLocal
from api.models import Manga, Scanlator, MangaScanlator, Chapter
from scanlators import get_scanlator_by_name
from playwright.async_api import async_playwright


class TrackingJob:
    """Represents a running or completed tracking job."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = "pending"  # pending, running, completed, failed
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.total_mappings = 0
        self.processed_mappings = 0
        self.new_chapters_found = 0
        self.errors: List[str] = []
        self.chapters_data: List[Dict] = []  # Store chapter data for notifications


class TrackerService:
    """Service for managing chapter tracking jobs."""

    def __init__(self):
        self.jobs: Dict[str, TrackingJob] = {}
        self._lock = asyncio.Lock()

    async def trigger_tracking(
        self,
        manga_id: Optional[int] = None,
        scanlator_id: Optional[int] = None,
        notify: bool = True
    ) -> str:
        """
        Trigger a tracking job.

        Args:
            manga_id: Optional manga ID to filter
            scanlator_id: Optional scanlator ID to filter
            notify: Whether to send notifications for new chapters

        Returns:
            Job ID for tracking the job status
        """
        job_id = str(uuid.uuid4())
        job = TrackingJob(job_id)

        async with self._lock:
            self.jobs[job_id] = job

        # Run tracking in background
        asyncio.create_task(self._run_tracking_job(job, manga_id, scanlator_id, notify))

        logger.info(f"Tracking job {job_id} queued (manga_id={manga_id}, scanlator_id={scanlator_id})")
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a tracking job."""
        async with self._lock:
            job = self.jobs.get(job_id)

            if not job:
                return None

            return {
                "job_id": job.job_id,
                "status": job.status,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "total_mappings": job.total_mappings,
                "processed_mappings": job.processed_mappings,
                "new_chapters_found": job.new_chapters_found,
                "errors": job.errors
            }

    async def list_jobs(self, limit: int = 20) -> List[Dict]:
        """List recent tracking jobs."""
        async with self._lock:
            jobs = sorted(
                self.jobs.values(),
                key=lambda j: j.started_at or datetime.min,
                reverse=True
            )[:limit]

            return [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "new_chapters_found": job.new_chapters_found
                }
                for job in jobs
            ]

    async def _run_tracking_job(
        self,
        job: TrackingJob,
        manga_id: Optional[int],
        scanlator_id: Optional[int],
        notify: bool
    ):
        """Execute the tracking job."""
        job.status = "running"
        job.started_at = datetime.utcnow()

        db = SessionLocal()

        try:
            # Get manga-scanlator mappings
            query = db.query(MangaScanlator).options(
                joinedload(MangaScanlator.manga),
                joinedload(MangaScanlator.scanlator)
            ).filter(MangaScanlator.manually_verified == True)

            if manga_id:
                query = query.filter(MangaScanlator.manga_id == manga_id)
            if scanlator_id:
                query = query.filter(MangaScanlator.scanlator_id == scanlator_id)

            mappings = query.all()
            job.total_mappings = len(mappings)

            logger.info(f"Job {job.job_id}: Processing {job.total_mappings} mappings")

            # Process each mapping
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                for mapping in mappings:
                    try:
                        await self._process_mapping(job, mapping, browser, db)
                        job.processed_mappings += 1
                    except Exception as e:
                        error_msg = f"Error processing mapping {mapping.id}: {str(e)}"
                        logger.error(error_msg)
                        job.errors.append(error_msg)

                await browser.close()

            job.status = "completed"
            logger.info(f"Job {job.job_id}: Completed. Found {job.new_chapters_found} new chapters")

            # Send notifications if enabled
            if notify and job.new_chapters_found > 0:
                from api.services.notification_service import get_notification_service
                notification_service = get_notification_service()
                await notification_service.notify_new_chapters(job.chapters_data)

        except Exception as e:
            job.status = "failed"
            error_msg = f"Job failed: {str(e)}"
            logger.error(error_msg)
            job.errors.append(error_msg)

        finally:
            job.completed_at = datetime.utcnow()
            db.close()

    async def _process_mapping(self, job: TrackingJob, mapping, browser, db):
        """Process a single manga-scanlator mapping."""
        manga = mapping.manga
        scanlator = mapping.scanlator

        logger.info(f"Tracking {manga.title} on {scanlator.name}")

        # Get scanlator plugin
        plugin_class = get_scanlator_by_name(scanlator.name)
        if not plugin_class:
            raise ValueError(f"No plugin found for {scanlator.name}")

        plugin = plugin_class()
        page = await browser.new_page()

        try:
            # Fetch chapters
            chapters = await plugin.get_chapters(page, mapping.scanlator_manga_url)

            # Insert new chapters
            for chapter_data in chapters:
                # Check if chapter already exists
                existing = db.query(Chapter).filter(
                    and_(
                        Chapter.manga_scanlator_id == mapping.id,
                        Chapter.chapter_number == chapter_data["chapter_number"]
                    )
                ).first()

                if not existing:
                    chapter = Chapter(
                        manga_scanlator_id=mapping.id,
                        chapter_number=chapter_data["chapter_number"],
                        title=chapter_data.get("title"),
                        url=chapter_data["url"],
                        release_date=chapter_data.get("release_date"),
                        detected_date=datetime.utcnow(),
                        read=False
                    )
                    db.add(chapter)
                    db.commit()

                    job.new_chapters_found += 1
                    job.chapters_data.append({
                        "manga_title": manga.title,
                        "chapter_number": chapter_data["chapter_number"],
                        "title": chapter_data.get("title"),
                        "url": chapter_data["url"],
                        "scanlator_name": scanlator.name,
                        "detected_date": datetime.utcnow()
                    })

                    logger.info(f"New chapter: {manga.title} #{chapter_data['chapter_number']}")

        finally:
            await page.close()


# Singleton instance
_tracker_service = TrackerService()


def get_tracker_service() -> TrackerService:
    """Get the tracker service singleton."""
    return _tracker_service
```

**Commit:**

```bash
git add api/services/tracker_service.py
git commit -m "feat(api): add tracker service for background tracking jobs"
```

---

### Step 9.4: Add tracking schemas to schemas.py

**Action:** Add Pydantic models for tracking API responses.

**File:** `api/schemas.py`

Add at the end of the file:

```python
# Tracking job schemas
class TrackingJobTrigger(BaseModel):
    """Request to trigger a tracking job."""
    manga_id: Optional[int] = None
    scanlator_id: Optional[int] = None
    notify: bool = True


class TrackingJobStatus(BaseModel):
    """Status of a tracking job."""
    job_id: str
    status: str  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_mappings: int
    processed_mappings: int
    new_chapters_found: int
    errors: List[str]


class TrackingJobSummary(BaseModel):
    """Summary of a tracking job."""
    job_id: str
    status: str
    started_at: Optional[str] = None
    new_chapters_found: int
```

**Commit:**

```bash
git add api/schemas.py
git commit -m "feat(api): add tracking job schemas"
```

---

### Step 9.5: Add tracking trigger endpoints to tracking router

**Action:** Add new endpoints to trigger tracking and monitor jobs.

**File:** `api/routers/tracking.py`

Add at the end of the file:

```python
from api.services.tracker_service import get_tracker_service
from api.services.notification_service import get_notification_service


@router.post("/trigger", response_model=schemas.TrackingJobSummary, status_code=202)
async def trigger_tracking(request: schemas.TrackingJobTrigger):
    """
    Trigger a chapter tracking job.

    - **manga_id**: Optional manga ID to track (tracks all if not specified)
    - **scanlator_id**: Optional scanlator ID to track (tracks all if not specified)
    - **notify**: Whether to send notifications for new chapters (default: true)

    Returns a job ID that can be used to monitor the tracking progress.
    """
    tracker_service = get_tracker_service()

    job_id = await tracker_service.trigger_tracking(
        manga_id=request.manga_id,
        scanlator_id=request.scanlator_id,
        notify=request.notify
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "started_at": None,
        "new_chapters_found": 0
    }


@router.get("/jobs/{job_id}", response_model=schemas.TrackingJobStatus)
async def get_job_status(job_id: str):
    """
    Get the status of a tracking job.

    - **job_id**: The ID of the tracking job
    """
    tracker_service = get_tracker_service()

    status = await tracker_service.get_job_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return status


@router.get("/jobs", response_model=List[schemas.TrackingJobSummary])
async def list_jobs(limit: int = Query(20, ge=1, le=100)):
    """
    List recent tracking jobs.

    - **limit**: Maximum number of jobs to return (default: 20)
    """
    tracker_service = get_tracker_service()

    jobs = await tracker_service.list_jobs(limit=limit)

    return jobs


@router.post("/test-notification", status_code=200)
async def test_notification():
    """
    Send a test notification to verify webhook configuration.
    """
    notification_service = get_notification_service()

    test_chapters = [
        {
            "manga_title": "Test Manga",
            "chapter_number": "123",
            "title": "Test Chapter",
            "url": "https://example.com/test",
            "scanlator_name": "Test Scanlator",
            "detected_date": datetime.utcnow()
        }
    ]

    success = await notification_service.notify_new_chapters(test_chapters)

    if success:
        return {"message": "Test notification sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test notification")
```

**Commit:**

```bash
git add api/routers/tracking.py
git commit -m "feat(api): add tracking trigger and job monitoring endpoints"
```

---

### Step 9.6: Test the new tracking API endpoints

**Action:** Start the API and test the new endpoints.

**Commands:**

```bash
# In terminal 1: Start API
uvicorn api.main:app --reload

# In terminal 2: Test endpoints
# Trigger tracking job
curl -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"manga_id": null, "scanlator_id": null, "notify": false}'

# Get job status (replace JOB_ID with actual ID from previous response)
curl http://localhost:8008/api/tracking/jobs/JOB_ID

# List recent jobs
curl http://localhost:8008/api/tracking/jobs

# Test notification (if Discord webhook configured)
curl -X POST http://localhost:8008/api/tracking/test-notification
```

**Expected:**
- Trigger returns 202 with job_id
- Job status shows progress/completion
- Jobs list shows recent tracking runs
- Test notification sends to Discord (if configured)

**Commit:**

```bash
git add -A
git commit -m "test(api): verify tracking trigger and monitoring endpoints work"
```

---

## Task 13: n8n Workflow Automation (2-3 hours)

**Goal:** Create n8n workflows for scheduled chapter tracking and notifications.

**Files:**
- Create: `n8n/workflows/scheduled_tracking.json`
- Create: `n8n/workflows/discord_notifications.json`
- Create: `n8n/README.md`
- Update: `docs/api_guide.md` (add webhook info)

**Note:** This assumes n8n is installed. If not installed, see n8n/README.md for setup instructions.

---

### Step 13.1: Create n8n directory and README

**Action:** Create n8n directory with setup instructions.

**File:** `n8n/README.md` (create new)

```markdown
# n8n Workflow Automation

This directory contains n8n workflows for automating MangaTaro chapter tracking and notifications.

## Installation

### Option 1: Docker (Recommended)

```bash
docker run -d --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

### Option 2: npm

```bash
npm install -g n8n
n8n start
```

Access n8n at: http://localhost:5678

## Workflows

### 1. Scheduled Chapter Tracking

**File:** `scheduled_tracking.json`

**Purpose:** Runs chapter tracking daily and sends notifications for new chapters.

**Schedule:** Every day at 9:00 AM and 9:00 PM

**Steps:**
1. Trigger on schedule (cron: `0 9,21 * * *`)
2. HTTP Request: POST to `/api/tracking/trigger`
3. Wait 30 seconds
4. HTTP Request: GET job status
5. Loop until job completes
6. Log results

**Setup:**
1. Import workflow from `scheduled_tracking.json`
2. Update "MangaTaro API Base URL" to `http://localhost:8008`
3. Activate workflow

### 2. Discord Notifications Webhook

**File:** `discord_notifications.json`

**Purpose:** Receives webhook notifications and forwards to Discord with rich formatting.

**Trigger:** Webhook `/webhook/manga-updates`

**Steps:**
1. Receive webhook with chapter data
2. Format Discord message with embeds
3. Send to Discord webhook
4. Log notification

**Setup:**
1. Import workflow from `discord_notifications.json`
2. Update Discord webhook URL in "Send to Discord" node
3. Activate workflow
4. Note the webhook URL (shown in Webhook node)

## Configuration

### Environment Variables

Add to `.env`:

```bash
# n8n Webhook (if using webhook-based notifications)
N8N_WEBHOOK_URL=http://localhost:5678/webhook/manga-updates
```

## Testing

### Test Scheduled Tracking

```bash
# Manually execute the workflow in n8n UI
# Or trigger via API:
curl -X POST http://localhost:5678/webhook/trigger-tracking
```

### Test Discord Notifications

```bash
# Send test notification via API
curl -X POST http://localhost:8008/api/tracking/test-notification
```

## Troubleshooting

**Issue:** Workflows not executing

**Solution:**
- Check n8n is running: `docker ps | grep n8n`
- Check workflow is activated (toggle in n8n UI)
- Check logs: `docker logs n8n`

**Issue:** Notifications not sending

**Solution:**
- Verify Discord webhook URL is correct
- Test webhook: `curl -X POST DISCORD_WEBHOOK_URL -H "Content-Type: application/json" -d '{"content":"test"}'`
- Check n8n execution logs

## Advanced: Systemd Service

To run n8n as a system service:

```bash
sudo cp ../systemd/n8n.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable n8n
sudo systemctl start n8n
```
```

**Commit:**

```bash
mkdir -p n8n/workflows
git add n8n/README.md
git commit -m "docs(n8n): add n8n setup and workflow documentation"
```

---

### Step 13.2: Create scheduled tracking workflow

**Action:** Create n8n workflow JSON for scheduled tracking.

**File:** `n8n/workflows/scheduled_tracking.json` (create new)

```json
{
  "name": "MangaTaro - Scheduled Chapter Tracking",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "cronExpression",
              "expression": "0 9,21 * * *"
            }
          ]
        }
      },
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "http://localhost:8008/api/tracking/trigger",
        "method": "POST",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "notify",
              "value": "=true"
            }
          ]
        },
        "options": {}
      },
      "name": "Trigger Tracking",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "amount": 30,
        "unit": "seconds"
      },
      "name": "Wait 30s",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1,
      "position": [650, 300],
      "webhookId": "wait-for-tracking"
    },
    {
      "parameters": {
        "url": "=http://localhost:8008/api/tracking/jobs/{{ $json.job_id }}",
        "options": {}
      },
      "name": "Check Job Status",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [850, 300]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.status }}",
              "operation": "equals",
              "value2": "completed"
            }
          ]
        }
      },
      "name": "Job Complete?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [1050, 300]
    },
    {
      "parameters": {
        "amount": 10,
        "unit": "seconds"
      },
      "name": "Wait 10s More",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1,
      "position": [850, 450],
      "webhookId": "wait-retry"
    },
    {
      "parameters": {
        "message": "=Tracking completed!\nNew chapters: {{ $json.new_chapters_found }}\nProcessed: {{ $json.processed_mappings }}/{{ $json.total_mappings }}",
        "additionalFields": {}
      },
      "name": "Log Results",
      "type": "n8n-nodes-base.discord",
      "typeVersion": 1,
      "position": [1250, 300]
    }
  ],
  "connections": {
    "Schedule Trigger": {
      "main": [[{"node": "Trigger Tracking", "type": "main", "index": 0}]]
    },
    "Trigger Tracking": {
      "main": [[{"node": "Wait 30s", "type": "main", "index": 0}]]
    },
    "Wait 30s": {
      "main": [[{"node": "Check Job Status", "type": "main", "index": 0}]]
    },
    "Check Job Status": {
      "main": [[{"node": "Job Complete?", "type": "main", "index": 0}]]
    },
    "Job Complete?": {
      "main": [
        [{"node": "Log Results", "type": "main", "index": 0}],
        [{"node": "Wait 10s More", "type": "main", "index": 0}]
      ]
    },
    "Wait 10s More": {
      "main": [[{"node": "Check Job Status", "type": "main", "index": 0}]]
    }
  },
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Commit:**

```bash
git add n8n/workflows/scheduled_tracking.json
git commit -m "feat(n8n): add scheduled chapter tracking workflow"
```

---

### Step 13.3: Create simplified cron-based automation script

**Action:** Since n8n requires manual setup, create a simple cron script alternative.

**File:** `scripts/run_scheduled_tracking.sh` (create new)

```bash
#!/bin/bash

# Scheduled Chapter Tracking Script
# Run this via cron for automated chapter tracking
#
# Example crontab entry (daily at 9 AM and 9 PM):
# 0 9,21 * * * /data/mangataro/scripts/run_scheduled_tracking.sh

set -e

# Configuration
API_URL="http://localhost:8008"
LOG_DIR="/data/mangataro/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/scheduled_tracking_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

echo "=== MangaTaro Scheduled Tracking ===" | tee -a "$LOG_FILE"
echo "Started at: $(date)" | tee -a "$LOG_FILE"

# Trigger tracking
echo "Triggering tracking job..." | tee -a "$LOG_FILE"
RESPONSE=$(curl -s -X POST "$API_URL/api/tracking/trigger" \
  -H "Content-Type: application/json" \
  -d '{"notify": true}')

JOB_ID=$(echo "$RESPONSE" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
  echo "ERROR: Failed to trigger tracking job" | tee -a "$LOG_FILE"
  echo "Response: $RESPONSE" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Job ID: $JOB_ID" | tee -a "$LOG_FILE"

# Poll for completion (max 10 minutes)
MAX_ATTEMPTS=60
ATTEMPT=0
STATUS="pending"

while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ] && [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ]; do
  sleep 10
  ATTEMPT=$((ATTEMPT + 1))

  STATUS_RESPONSE=$(curl -s "$API_URL/api/tracking/jobs/$JOB_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)

  echo "Attempt $ATTEMPT: Status = $STATUS" | tee -a "$LOG_FILE"
done

# Get final status
FINAL_STATUS=$(curl -s "$API_URL/api/tracking/jobs/$JOB_ID")
echo "=== Final Status ===" | tee -a "$LOG_FILE"
echo "$FINAL_STATUS" | tee -a "$LOG_FILE"

NEW_CHAPTERS=$(echo "$FINAL_STATUS" | grep -o '"new_chapters_found":[0-9]*' | cut -d':' -f2)

echo "Completed at: $(date)" | tee -a "$LOG_FILE"
echo "New chapters found: $NEW_CHAPTERS" | tee -a "$LOG_FILE"

if [ "$STATUS" = "completed" ]; then
  echo "SUCCESS: Tracking completed successfully" | tee -a "$LOG_FILE"
  exit 0
else
  echo "ERROR: Tracking failed or timed out" | tee -a "$LOG_FILE"
  exit 1
fi
```

**Commands:**

```bash
chmod +x scripts/run_scheduled_tracking.sh

# Test the script
./scripts/run_scheduled_tracking.sh
```

**Expected:** Script triggers tracking and polls until completion.

**File:** `scripts/setup_cron.sh` (create new)

```bash
#!/bin/bash

# Setup cron job for scheduled tracking

SCRIPT_PATH="/data/mangataro/scripts/run_scheduled_tracking.sh"
CRON_SCHEDULE="0 9,21 * * *"  # 9 AM and 9 PM daily

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
  echo "Cron job already exists"
  exit 0
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $SCRIPT_PATH") | crontab -

echo "Cron job added successfully!"
echo "Schedule: Daily at 9:00 AM and 9:00 PM"
echo "Command: $SCRIPT_PATH"
echo ""
echo "To view cron jobs: crontab -l"
echo "To remove cron job: crontab -e (then delete the line)"
```

**Commands:**

```bash
chmod +x scripts/setup_cron.sh

# Setup cron (optional)
./scripts/setup_cron.sh
```

**Commit:**

```bash
git add scripts/run_scheduled_tracking.sh scripts/setup_cron.sh
git commit -m "feat(automation): add cron-based scheduled tracking scripts"
```

---

## Task 14: Project Documentation (1-2 hours)

**Goal:** Create comprehensive documentation for users and developers.

**Files:**
- Create: `docs/USER_GUIDE.md`
- Create: `docs/SETUP.md`
- Update: `docs/api_guide.md`
- Create: `docs/DEPLOYMENT.md`
- Update: `README.md`

---

### Step 14.1: Create user guide

**Action:** Write user guide for the web interface.

**File:** `docs/USER_GUIDE.md` (create new)

```markdown
# MangaTaro User Guide

Complete guide to using the MangaTaro manga tracking system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Web Interface](#web-interface)
3. [Managing Manga](#managing-manga)
4. [Tracking Chapters](#tracking-chapters)
5. [Notifications](#notifications)
6. [CLI Tools](#cli-tools)

---

## Quick Start

### Access the Web UI

1. Ensure the API is running: `uvicorn api.main:app --reload`
2. Ensure the frontend is running: `cd frontend && npm run dev`
3. Open your browser: http://localhost:4343

### Daily Workflow

1. Visit the **Homepage** to see unread chapter updates
2. Click "Mark as Read" on chapters you've read
3. Browse your **Library** to discover new manga
4. Click on any manga to see all available chapters

---

## Web Interface

### Homepage (Updates Feed)

**URL:** http://localhost:4343/

**Features:**
- Shows unread chapters across all tracked manga
- Sorted by detection date (newest first)
- Mark chapters as read with one click
- Links directly to scanlator websites

**Filters:**
- Search by manga title
- Filter by reading status (All, Unread, Read)

### Library Page

**URL:** http://localhost:4343/library

**Features:**
- Grid view of all manga in your collection
- Cover images with titles
- Reading status indicators
- Search and filters

**Actions:**
- Click on any manga card to view details
- Use search bar to find manga by title
- Filter by status or genre (if implemented)

### Manga Detail Page

**URL:** http://localhost:4343/manga/{id}

**Features:**
- Manga information (title, cover, description)
- List of all scanlators tracking this manga
- Complete chapter list with read/unread status
- Bulk actions (mark all as read)

**Actions:**
- Mark individual chapters as read/unread
- Click chapter links to read on scanlator site
- View scanlator information

---

## Managing Manga

### Adding Manga Sources

To track chapters for a manga, you need to map it to a scanlator URL.

**Using CLI Tool:**

```bash
python scripts/add_manga_source.py
```

Follow the interactive prompts:
1. Select manga from your collection
2. Select scanlator (or add new)
3. Enter the manga URL on the scanlator site
4. Verify the mapping

**Using API:**

```bash
curl -X POST http://localhost:8008/api/tracking/manga-scanlators \
  -H "Content-Type: application/json" \
  -d '{
    "manga_id": 60,
    "scanlator_id": 3,
    "scanlator_manga_url": "https://asura-scans.com/manga/solo-leveling",
    "manually_verified": true
  }'
```

### Viewing Tracked Manga

**API Endpoint:**

```bash
curl http://localhost:8008/api/manga/{manga_id}
```

Shows manga details with all linked scanlators.

---

## Tracking Chapters

### Manual Tracking

Run tracking manually for all verified manga:

```bash
python scripts/track_chapters.py
```

**Options:**
- `--limit N`: Process only first N manga
- `--visible`: Run with visible browser (for debugging)
- `--manga-id ID`: Track specific manga only
- `--scanlator-id ID`: Track specific scanlator only

**Example:**

```bash
# Track all manga
python scripts/track_chapters.py

# Track specific manga with visible browser
python scripts/track_chapters.py --manga-id 60 --visible

# Track first 5 manga only
python scripts/track_chapters.py --limit 5
```

### Automated Tracking

**Option 1: Cron Job (Recommended)**

Setup automated tracking:

```bash
./scripts/setup_cron.sh
```

This runs tracking daily at 9 AM and 9 PM.

**Option 2: API Trigger**

Trigger tracking via API:

```bash
# Trigger tracking
curl -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"notify": true}'

# Check job status
curl http://localhost:8008/api/tracking/jobs/{job_id}

# List recent jobs
curl http://localhost:8008/api/tracking/jobs
```

**Option 3: n8n Workflow**

See `n8n/README.md` for n8n workflow setup.

---

## Notifications

### Discord Notifications

Get notified when new chapters are detected.

**Setup:**

1. Create a Discord webhook:
   - Go to Server Settings > Integrations > Webhooks
   - Click "New Webhook"
   - Copy the webhook URL

2. Add to `.env`:
   ```bash
   NOTIFICATION_TYPE=discord
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE
   ```

3. Restart the API:
   ```bash
   uvicorn api.main:app --reload
   ```

4. Test notification:
   ```bash
   curl -X POST http://localhost:8008/api/tracking/test-notification
   ```

**What You'll Receive:**

- Notification when new chapters are detected
- Rich embed with manga title, chapter number, and link
- Up to 10 chapters per notification
- Summary if more than 10 chapters

---

## CLI Tools

### Extract from MangaTaro

**Purpose:** Import your manga collection from MangaTaro export.

```bash
python scripts/extract_mangataro.py
```

**Output:**
- Manga imported to database
- Cover images downloaded
- Markdown fichas created

### Add Manga Source

**Purpose:** Map manga to scanlator URLs for tracking.

```bash
python scripts/add_manga_source.py
```

**Interactive CLI** guides you through the process.

### Track Chapters

**Purpose:** Check scanlator sites for new chapters.

```bash
python scripts/track_chapters.py
```

See [Tracking Chapters](#tracking-chapters) for details.

### Test Scanlator Plugin

**Purpose:** Verify scanlator plugin works correctly.

```bash
python scripts/test_asura_scans.py
```

**Tests:**
- Search functionality
- Chapter extraction
- Manga page parsing

---

## Tips & Tricks

### Keyboard Shortcuts

- `/` - Focus search bar
- `Esc` - Clear search
- `Enter` - Submit search

### Performance

- Use `--limit` flag when testing tracking
- Run tracking during off-peak hours
- Use headless mode for faster tracking

### Troubleshooting

**Chapters not appearing:**
- Verify manga-scanlator mapping exists
- Check `manually_verified` is `true`
- Run tracking with `--visible` to debug

**Notifications not working:**
- Test with `/api/tracking/test-notification`
- Verify Discord webhook URL is correct
- Check API logs for errors

**Frontend not loading:**
- Ensure API is running on port 8008
- Check CORS settings in `.env`
- Verify frontend .env has correct API URL

---

## Next Steps

- Set up automated tracking (cron or n8n)
- Configure Discord notifications
- Add more manga-scanlator mappings
- Explore the API documentation

For API details, see `docs/api_guide.md`.

For setup instructions, see `docs/SETUP.md`.
```

**Commit:**

```bash
git add docs/USER_GUIDE.md
git commit -m "docs: add comprehensive user guide"
```

---

### Step 14.2: Create setup guide

**Action:** Write setup instructions for new installations.

**File:** `docs/SETUP.md` (create new)

```markdown
# MangaTaro Setup Guide

Complete installation and setup instructions for MangaTaro.

## Prerequisites

- Python 3.10+
- Node.js 18+
- MariaDB/MySQL 10.6+
- Git

---

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd mangataro
```

### 2. Database Setup

**Create database and user:**

```bash
mysql -u root -p

CREATE DATABASE mangataro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mangataro_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON mangataro.* TO 'mangataro_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Import schema:**

```bash
mysql -u mangataro_user -p mangataro < scripts/create_db.sql
```

### 3. Python Environment

**Create virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Install Playwright browsers:**

```bash
playwright install chromium
```

### 4. Configuration

**Copy environment template:**

```bash
cp .env.example .env
```

**Edit `.env`:**

```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mangataro
DB_USER=mangataro_user
DB_PASSWORD=your_secure_password_here

# API
API_HOST=0.0.0.0
API_PORT=8008
API_DEBUG=false
CORS_ORIGINS=http://localhost:3000,http://localhost:4343

# Scraping
PLAYWRIGHT_TIMEOUT=30000
SCRAPING_DELAY_MIN=2
SCRAPING_DELAY_MAX=5

# Notifications (optional)
NOTIFICATION_TYPE=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK
```

### 5. Frontend Setup

**Install dependencies:**

```bash
cd frontend
npm install
```

**Configure frontend:**

```bash
cp .env.example .env
```

Edit `frontend/.env`:

```bash
PUBLIC_API_URL=http://localhost:8008
```

**Build frontend (optional):**

```bash
npm run build
```

---

## Running the Application

### Development Mode

**Terminal 1 - API:**

```bash
cd /data/mangataro
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8008
```

**Terminal 2 - Frontend:**

```bash
cd /data/mangataro/frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:4343
- API Docs: http://localhost:8008/docs

### Production Mode

See `docs/DEPLOYMENT.md` for systemd service setup.

---

## Initial Data Import

### Import from MangaTaro

If you have a MangaTaro export:

```bash
python scripts/extract_mangataro.py
```

This imports:
- Manga metadata
- Cover images
- Scanlator information

### Add Tracking Sources

Map manga to scanlator URLs:

```bash
python scripts/add_manga_source.py
```

Follow the interactive prompts.

---

## Verify Installation

### Test Database Connection

```bash
mysql -u mangataro_user -p mangataro -e "SELECT COUNT(*) FROM mangas;"
```

### Test API

```bash
curl http://localhost:8008/health
```

Expected: `{"status":"healthy","api":"operational"}`

### Test Tracking

```bash
python scripts/track_chapters.py --limit 1 --visible
```

Expected: Browser opens, fetches chapters, inserts into database.

### Test Frontend

```bash
curl http://localhost:4343/
```

Expected: HTML response with page content.

---

## Optional Setup

### Discord Notifications

1. Create Discord webhook (Server Settings > Integrations > Webhooks)
2. Add to `.env`:
   ```
   NOTIFICATION_TYPE=discord
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```
3. Test:
   ```bash
   curl -X POST http://localhost:8008/api/tracking/test-notification
   ```

### Automated Tracking

**Option 1: Cron**

```bash
./scripts/setup_cron.sh
```

**Option 2: Systemd Timer**

See `docs/DEPLOYMENT.md`.

**Option 3: n8n**

See `n8n/README.md`.

---

## Troubleshooting

### Database Connection Failed

- Verify credentials in `.env`
- Check MariaDB is running: `sudo systemctl status mariadb`
- Test connection: `mysql -u mangataro_user -p`

### API Won't Start

- Check port 8008 is available: `lsof -i :8008`
- Verify virtual environment is activated
- Check logs for errors

### Playwright Errors

- Install browsers: `playwright install chromium`
- Check system dependencies: `playwright install-deps`

### Frontend Build Errors

- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (should be 18+)

---

## Next Steps

1. Import your manga collection
2. Add scanlator mappings
3. Run initial chapter tracking
4. Set up Discord notifications
5. Configure automated tracking
6. Explore the API documentation

See `docs/USER_GUIDE.md` for usage instructions.
```

**Commit:**

```bash
git add docs/SETUP.md
git commit -m "docs: add setup and installation guide"
```

---

### Step 14.3: Create deployment guide

**Action:** Write deployment guide for production setup.

**File:** `docs/DEPLOYMENT.md` (create new - content truncated for brevity)

```markdown
# MangaTaro Deployment Guide

Production deployment instructions for MangaTaro.

## Systemd Services

### API Service

**File:** `/etc/systemd/system/mangataro-api.service`

```ini
[Unit]
Description=MangaTaro API
After=network.target mariadb.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/data/mangataro
Environment="PATH=/data/mangataro/.venv/bin"
ExecStart=/data/mangataro/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8008
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable mangataro-api
sudo systemctl start mangataro-api
sudo systemctl status mangataro-api
```

### Frontend Service

**File:** `/etc/systemd/system/mangataro-frontend.service`

```ini
[Unit]
Description=MangaTaro Frontend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/data/mangataro/frontend
ExecStart=/usr/bin/npm run dev
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**For production, use:**

```bash
npm run build
npm run preview
```

Or serve with nginx (see below).

---

## Nginx Reverse Proxy

**File:** `/etc/nginx/sites-available/mangataro`

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:4343;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8008/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API docs
    location /docs {
        proxy_pass http://localhost:8008/docs;
    }
}
```

**Enable:**

```bash
sudo ln -s /etc/nginx/sites-available/mangataro /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Automated Tracking

### Systemd Timer

**File:** `/etc/systemd/system/mangataro-tracking.service`

```ini
[Unit]
Description=MangaTaro Chapter Tracking
After=network.target mangataro-api.service

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/data/mangataro
Environment="PATH=/data/mangataro/.venv/bin"
ExecStart=/data/mangataro/scripts/run_scheduled_tracking.sh
```

**File:** `/etc/systemd/system/mangataro-tracking.timer`

```ini
[Unit]
Description=Run MangaTaro tracking twice daily

[Timer]
OnCalendar=09:00
OnCalendar=21:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable mangataro-tracking.timer
sudo systemctl start mangataro-tracking.timer
sudo systemctl list-timers
```

---

## Security

### Environment Variables

- Never commit `.env` to version control
- Use strong database passwords
- Restrict API access with firewall rules

### CORS

Update `.env` with production domains:

```bash
CORS_ORIGINS=https://your-domain.com
```

### Database

- Use non-root user
- Enable SSL connections
- Regular backups

---

## Monitoring

### Logs

```bash
# API logs
sudo journalctl -u mangataro-api -f

# Frontend logs
sudo journalctl -u mangataro-frontend -f

# Tracking logs
ls -lah /data/mangataro/logs/
```

### Health Checks

```bash
# API health
curl http://localhost:8008/health

# Database
mysql -u mangataro_user -p -e "SELECT COUNT(*) FROM mangataro.chapters;"
```

---

## Backup

### Database Backup

```bash
mysqldump -u mangataro_user -p mangataro > backup_$(date +%Y%m%d).sql
```

### Automated Backups

Add to cron:

```bash
0 2 * * * mysqldump -u mangataro_user -pPASSWORD mangataro | gzip > /backups/mangataro_$(date +\%Y\%m\%d).sql.gz
```

---

## Updates

### Pull Latest Changes

```bash
cd /data/mangataro
git pull
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install
```

### Restart Services

```bash
sudo systemctl restart mangataro-api
sudo systemctl restart mangataro-frontend
```

---

For setup instructions, see `docs/SETUP.md`.
For usage guide, see `docs/USER_GUIDE.md`.
```

**Commit:**

```bash
git add docs/DEPLOYMENT.md
git commit -m "docs: add deployment guide with systemd and nginx config"
```

---

### Step 14.4: Update main README

**Action:** Update the main README with project overview and links.

**File:** `README.md`

Update to include:

```markdown
# MangaTaro - Manga Chapter Tracker

Track manga chapters across multiple scanlation groups after MangaTaro shutdown.

## Features

- 📚 Import manga collection from MangaTaro
- 🔍 Automatic chapter tracking via scanlator plugins
- 🌐 Modern web interface with Astro + TailwindCSS
- 🔔 Discord notifications for new chapters
- 📊 REST API with OpenAPI documentation
- ⚡ Automated tracking via cron/n8n
- 🧩 Extensible scanlator plugin architecture

## Quick Start

```bash
# Setup (see docs/SETUP.md for details)
cp .env.example .env
# Edit .env with your database credentials

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Run API
uvicorn api.main:app --reload

# Run frontend (new terminal)
cd frontend && npm run dev

# Access at http://localhost:4343
```

## Documentation

- **[Setup Guide](docs/SETUP.md)** - Installation and configuration
- **[User Guide](docs/USER_GUIDE.md)** - How to use the system
- **[API Guide](docs/api_guide.md)** - API documentation
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment

## Architecture

- **Backend:** FastAPI + SQLAlchemy + MariaDB
- **Frontend:** Astro + TailwindCSS + Alpine.js
- **Scraping:** Playwright + Plugin Architecture
- **Automation:** n8n / Cron

## Status

✅ Phase 1: Data Extraction (100%)
✅ Phase 2: Tracking System (100%)
✅ Phase 3: API (100%)
✅ Phase 4: Frontend (100%)
✅ Phase 5: Automation (100%)
✅ Phase 6: Documentation (100%)

**Project Status:** Production Ready 🎉

## License

MIT

## Support

For issues and questions, see the documentation or open an issue.
```

**Commit:**

```bash
git add README.md
git commit -m "docs: update main README with project overview and documentation links"
```

---

## Final Steps

### Step 15.1: Update TOMORROW.md

**Action:** Mark all tasks as complete.

**File:** `TOMORROW.md`

Update status to:

```markdown
**Status:** 14/14 tasks complete (100%)
**MangaTaro closes in:** 13 days

All phases complete! System is production ready.
```

**Commit:**

```bash
git add TOMORROW.md
git commit -m "docs: mark all tasks complete - project finished!"
```

---

### Step 15.2: Final verification

**Action:** Test the complete system end-to-end.

**Commands:**

```bash
# 1. Start services
uvicorn api.main:app --reload &
cd frontend && npm run dev &

# 2. Test API
curl http://localhost:8008/health
curl http://localhost:8008/api/manga/?limit=5

# 3. Test tracking trigger
curl -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"notify": false}'

# 4. Test frontend
curl http://localhost:4343/ | grep -i "manga"

# 5. Test notification (if configured)
curl -X POST http://localhost:8008/api/tracking/test-notification
```

**Expected:** All endpoints respond correctly, frontend loads, tracking triggers successfully.

---

## Execution Options

Plan complete and saved to `docs/plans/2026-02-03-remaining-tasks-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach would you prefer?**
