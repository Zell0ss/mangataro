#!/usr/bin/env python3
"""
Chapter Tracking Script

This script checks all scanlator sites for new manga chapters using the plugin architecture.
It queries the database for all active manga-scanlator mappings and fetches chapters from
their respective websites, inserting new ones into the database.

Usage:
    python scripts/track_chapters.py                    # Track all active mappings
    python scripts/track_chapters.py --manga-id 5       # Track specific manga
    python scripts/track_chapters.py --scanlator-id 2   # Track specific scanlator
    python scripts/track_chapters.py --limit 5          # Process only first 5 mappings
    python scripts/track_chapters.py --visible          # Run with visible browser
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from playwright.async_api import async_playwright, Browser, Page
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_

from api.database import SessionLocal
from api.models import Manga, Scanlator, MangaScanlator, Chapter, ScrapingError
from scanlators import get_scanlator_by_name

# Load environment variables
load_dotenv()

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "/data/mangataro/logs/track_chapters_{time}.log",
    rotation="500 MB",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


class ChapterTracker:
    """Tracks new chapters across all manga-scanlator mappings."""

    def __init__(
        self,
        manga_id: int = None,
        scanlator_id: int = None,
        limit: int = None,
        headless: bool = True
    ):
        """
        Initialize the chapter tracker.

        Args:
            manga_id: Optional manga ID to filter by
            scanlator_id: Optional scanlator ID to filter by
            limit: Optional limit on number of mappings to process
            headless: Run browser in headless mode
        """
        self.manga_id = manga_id
        self.scanlator_id = scanlator_id
        self.limit = limit
        self.headless = headless
        self.db = SessionLocal()

        # Statistics
        self.stats = {
            "mappings_checked": 0,
            "new_chapters_found": 0,
            "errors": 0,
            "manga_updates": {}  # manga_title -> chapter_count
        }

        # Delays from env
        self.delay_min = float(os.getenv("SCRAPING_DELAY_MIN", "2"))
        self.delay_max = float(os.getenv("SCRAPING_DELAY_MAX", "5"))

    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'db'):
            self.db.close()

    async def track_manga_scanlator(
        self,
        mapping: MangaScanlator,
        page: Page
    ) -> int:
        """
        Track a single manga-scanlator pair.

        Args:
            mapping: MangaScanlator database object
            page: Playwright page instance

        Returns:
            Count of new chapters found
        """
        manga = mapping.manga
        scanlator = mapping.scanlator
        manga_url = mapping.scanlator_manga_url

        logger.info(f"Processing: {manga.title} @ {scanlator.name}")
        logger.debug(f"URL: {manga_url}")

        try:
            # Load the appropriate scanlator plugin
            plugin_class = get_scanlator_by_name(scanlator.class_name)

            if not plugin_class:
                raise ValueError(f"Plugin not found: {scanlator.class_name}")

            # Instantiate plugin
            plugin = plugin_class(page)
            logger.debug(f"Loaded plugin: {scanlator.class_name}")

            # Fetch chapters from website
            chapters_from_site = await plugin.obtener_capitulos(manga_url)

            if not chapters_from_site:
                logger.warning(f"No chapters found for {manga.title}")
                return 0

            logger.info(f"Found {len(chapters_from_site)} chapters on site")

            # Process each chapter
            new_chapters_count = 0

            for chapter_data in chapters_from_site:
                numero = chapter_data.get("numero", "0")
                titulo = chapter_data.get("titulo", "")
                url = chapter_data.get("url", "")
                fecha = chapter_data.get("fecha")

                if not numero or not url:
                    logger.warning(f"Skipping chapter with missing data: {chapter_data}")
                    continue

                # Check if chapter already exists in database
                existing = self.db.query(Chapter).filter(
                    and_(
                        Chapter.manga_scanlator_id == mapping.id,
                        Chapter.chapter_number == numero
                    )
                ).first()

                if existing:
                    logger.debug(f"Chapter {numero} already exists (ID: {existing.id})")
                    continue

                # Insert new chapter
                try:
                    new_chapter = Chapter(
                        manga_scanlator_id=mapping.id,
                        chapter_number=numero,
                        chapter_title=titulo,
                        chapter_url=url,
                        published_date=fecha,
                        detected_date=datetime.now(),
                        read=False
                    )

                    self.db.add(new_chapter)
                    self.db.commit()
                    self.db.refresh(new_chapter)

                    logger.success(
                        f"New chapter inserted: {manga.title} - Ch. {numero} (ID: {new_chapter.id})"
                    )
                    new_chapters_count += 1

                except IntegrityError as e:
                    # Handle unique constraint violation (race condition)
                    self.db.rollback()
                    logger.warning(f"Chapter {numero} already exists (race condition)")
                    continue

            # Update last_checked timestamp for manga
            manga.last_checked = datetime.now()
            self.db.commit()

            return new_chapters_count

        except Exception as e:
            logger.error(f"Error tracking {manga.title} @ {scanlator.name}: {e}")
            self.db.rollback()

            # Log error to database
            try:
                error_record = ScrapingError(
                    manga_scanlator_id=mapping.id,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    timestamp=datetime.now(),
                    resolved=False
                )
                self.db.add(error_record)
                self.db.commit()
            except Exception as log_error:
                logger.error(f"Failed to log error to database: {log_error}")
                self.db.rollback()

            raise

    async def track_all(self):
        """Track all active manga-scanlator mappings."""
        logger.info("="*60)
        logger.info("CHAPTER TRACKING STARTED")
        logger.info("="*60)

        # Build query for active mappings
        query = self.db.query(MangaScanlator).join(
            MangaScanlator.scanlator
        ).filter(
            MangaScanlator.manually_verified == True,
            Scanlator.active == True
        )

        # Apply filters
        if self.manga_id:
            query = query.filter(MangaScanlator.manga_id == self.manga_id)
            logger.info(f"Filtering by manga_id: {self.manga_id}")

        if self.scanlator_id:
            query = query.filter(MangaScanlator.scanlator_id == self.scanlator_id)
            logger.info(f"Filtering by scanlator_id: {self.scanlator_id}")

        # Apply limit
        if self.limit:
            query = query.limit(self.limit)
            logger.info(f"Limiting to first {self.limit} mappings")

        # Get all mappings
        mappings = query.all()

        if not mappings:
            logger.warning("No active manga-scanlator mappings found!")
            return

        total = len(mappings)
        logger.info(f"Found {total} manga-scanlator mapping(s) to track")
        logger.info("")

        # Initialize Playwright
        async with async_playwright() as p:
            logger.info(f"Launching browser (headless={self.headless})...")
            browser = await p.chromium.launch(headless=self.headless)

            # Create a reusable page
            page = await browser.new_page()

            # Set user agent from env
            user_agent = os.getenv(
                "USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            await page.set_extra_http_headers({"User-Agent": user_agent})

            # Process each mapping
            for idx, mapping in enumerate(mappings, 1):
                logger.info(f"\n[{idx}/{total}] " + "="*50)

                try:
                    new_count = await self.track_manga_scanlator(mapping, page)

                    self.stats["mappings_checked"] += 1
                    self.stats["new_chapters_found"] += new_count

                    if new_count > 0:
                        manga_title = mapping.manga.title
                        self.stats["manga_updates"][manga_title] = (
                            self.stats["manga_updates"].get(manga_title, 0) + new_count
                        )

                except Exception as e:
                    self.stats["errors"] += 1
                    logger.error(f"Failed to process mapping {mapping.id}: {e}")
                    # Continue to next mapping

                # Add delay between requests (except for last one)
                if idx < total:
                    import random
                    delay = random.uniform(self.delay_min, self.delay_max)
                    logger.info(f"Waiting {delay:.1f} seconds before next request...")
                    await asyncio.sleep(delay)

            await page.close()
            await browser.close()

        logger.info("\n" + "="*60)
        self._print_summary()

    def _print_summary(self):
        """Print summary report."""
        logger.info("TRACKING COMPLETE!")
        logger.info("="*60)
        logger.info(f"Manga-scanlator pairs checked: {self.stats['mappings_checked']}")
        logger.info(f"New chapters found: {self.stats['new_chapters_found']}")
        logger.info(f"Errors: {self.stats['errors']}")

        # Top updates
        if self.stats["manga_updates"]:
            logger.info("")
            logger.info("Top updates:")
            # Sort by chapter count (descending)
            sorted_updates = sorted(
                self.stats["manga_updates"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for manga_title, count in sorted_updates[:10]:  # Top 10
                logger.info(f"  - {manga_title}: {count} new chapter(s)")

        logger.info("="*60)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Track new manga chapters across all scanlator sites"
    )
    parser.add_argument(
        "--manga-id",
        type=int,
        help="Track only specific manga by ID"
    )
    parser.add_argument(
        "--scanlator-id",
        type=int,
        help="Track only specific scanlator by ID"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process only first N mappings (for testing)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default)"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run with visible browser for debugging"
    )

    args = parser.parse_args()

    # Handle headless flag
    headless = args.headless and not args.visible

    # Create tracker
    tracker = ChapterTracker(
        manga_id=args.manga_id,
        scanlator_id=args.scanlator_id,
        limit=args.limit,
        headless=headless
    )

    # Run tracking
    await tracker.track_all()


if __name__ == "__main__":
    asyncio.run(main())
