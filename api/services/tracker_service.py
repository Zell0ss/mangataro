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

        # Get scanlator plugin using class_name (not display name)
        plugin_class = get_scanlator_by_name(scanlator.class_name)
        if not plugin_class:
            raise ValueError(f"No plugin found for class_name: {scanlator.class_name}")

        page = await browser.new_page()
        plugin = plugin_class(page)

        try:
            # Fetch chapters using the correct Spanish method name
            chapters = await plugin.obtener_capitulos(mapping.scanlator_manga_url)

            # Insert new chapters
            for chapter_data in chapters:
                # Map Spanish field names to English for database
                # Plugin returns: numero, titulo, url, fecha
                # Check if chapter already exists
                existing = db.query(Chapter).filter(
                    and_(
                        Chapter.manga_scanlator_id == mapping.id,
                        Chapter.chapter_number == chapter_data["numero"]
                    )
                ).first()

                if not existing:
                    chapter = Chapter(
                        manga_scanlator_id=mapping.id,
                        chapter_number=chapter_data["numero"],
                        chapter_title=chapter_data.get("titulo"),
                        chapter_url=chapter_data["url"],
                        published_date=chapter_data.get("fecha"),
                        detected_date=datetime.utcnow(),
                        read=False
                    )
                    db.add(chapter)
                    db.commit()

                    job.new_chapters_found += 1
                    job.chapters_data.append({
                        "manga_title": manga.title,
                        "chapter_number": chapter_data["numero"],
                        "title": chapter_data.get("titulo"),
                        "url": chapter_data["url"],
                        "scanlator_name": scanlator.name,
                        "detected_date": datetime.utcnow()
                    })

                    logger.info(f"New chapter: {manga.title} #{chapter_data['numero']}")

        finally:
            await page.close()


# Singleton instance
_tracker_service = TrackerService()


def get_tracker_service() -> TrackerService:
    """Get the tracker service singleton."""
    return _tracker_service
