#!/usr/bin/env python3
"""
Test Tracking Script

This script tests the chapter tracking functionality with a limited dataset.
It verifies that:
1. Chapters can be fetched from scanlator sites
2. Chapters are properly inserted into the database
3. Duplicate detection works correctly
4. Error handling prevents failures from stopping the process

Usage:
    python scripts/test_tracking.py             # Test with first 1-2 mappings
    python scripts/test_tracking.py --visible   # Run with visible browser
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import and_

from api.database import SessionLocal
from api.models import Manga, Scanlator, MangaScanlator, Chapter

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


def print_separator(char="=", width=60):
    """Print a separator line."""
    logger.info(char * width)


def check_database_state():
    """Check and display current database state."""
    db = SessionLocal()

    try:
        print_separator()
        logger.info("DATABASE STATE CHECK")
        print_separator()

        # Count mangas
        manga_count = db.query(Manga).count()
        logger.info(f"Total mangas: {manga_count}")

        # Count scanlators
        scanlator_count = db.query(Scanlator).count()
        active_scanlator_count = db.query(Scanlator).filter(Scanlator.active == True).count()
        logger.info(f"Total scanlators: {scanlator_count} ({active_scanlator_count} active)")

        # Count manga-scanlator mappings
        mapping_count = db.query(MangaScanlator).count()
        verified_count = db.query(MangaScanlator).filter(
            MangaScanlator.manually_verified == True
        ).count()
        logger.info(f"Manga-scanlator mappings: {mapping_count} ({verified_count} verified)")

        # Count chapters
        chapter_count = db.query(Chapter).count()
        logger.info(f"Total chapters: {chapter_count}")

        # Show verified mappings
        logger.info("")
        logger.info("Verified manga-scanlator mappings:")

        verified_mappings = db.query(MangaScanlator).join(
            MangaScanlator.scanlator
        ).filter(
            MangaScanlator.manually_verified == True,
            Scanlator.active == True
        ).limit(5).all()

        if not verified_mappings:
            logger.warning("  No verified mappings found!")
            logger.warning("  You need to add manga sources first using scripts/add_manga_source.py")
        else:
            for idx, mapping in enumerate(verified_mappings, 1):
                manga = mapping.manga
                scanlator = mapping.scanlator

                # Count chapters for this mapping
                chapter_count = db.query(Chapter).filter(
                    Chapter.manga_scanlator_id == mapping.id
                ).count()

                logger.info(
                    f"  {idx}. {manga.title} @ {scanlator.name} "
                    f"({chapter_count} chapters)"
                )
                logger.info(f"     URL: {mapping.scanlator_manga_url}")

        print_separator()

    finally:
        db.close()


def verify_chapters_inserted(mapping_id: int, expected_min: int = 1):
    """
    Verify that chapters were inserted for a specific mapping.

    Args:
        mapping_id: The manga_scanlator mapping ID
        expected_min: Minimum number of chapters expected
    """
    db = SessionLocal()

    try:
        mapping = db.query(MangaScanlator).filter(MangaScanlator.id == mapping_id).first()

        if not mapping:
            logger.error(f"Mapping {mapping_id} not found!")
            return False

        chapters = db.query(Chapter).filter(
            Chapter.manga_scanlator_id == mapping_id
        ).order_by(Chapter.chapter_number).all()

        logger.info("")
        logger.info(f"Verification for: {mapping.manga.title} @ {mapping.scanlator.name}")
        logger.info(f"Chapters in database: {len(chapters)}")

        if len(chapters) < expected_min:
            logger.warning(f"Expected at least {expected_min} chapters, found {len(chapters)}")
            return False

        # Show first few chapters
        logger.info("First 5 chapters:")
        for chapter in chapters[:5]:
            logger.info(
                f"  Ch. {chapter.chapter_number}: {chapter.chapter_title[:50] if chapter.chapter_title else 'N/A'}"
            )
            logger.info(f"      URL: {chapter.chapter_url}")
            logger.info(f"      Detected: {chapter.detected_date}")

        if len(chapters) > 5:
            logger.info(f"  ... and {len(chapters) - 5} more")

        logger.success("Verification passed!")
        return True

    finally:
        db.close()


def test_duplicate_detection(mapping_id: int):
    """
    Test that duplicate chapters are properly detected and not inserted.

    Args:
        mapping_id: The manga_scanlator mapping ID
    """
    db = SessionLocal()

    try:
        logger.info("")
        print_separator()
        logger.info("TESTING DUPLICATE DETECTION")
        print_separator()

        mapping = db.query(MangaScanlator).filter(MangaScanlator.id == mapping_id).first()

        if not mapping:
            logger.error(f"Mapping {mapping_id} not found!")
            return False

        # Get an existing chapter
        existing_chapter = db.query(Chapter).filter(
            Chapter.manga_scanlator_id == mapping_id
        ).first()

        if not existing_chapter:
            logger.warning("No existing chapters to test duplicate detection")
            return False

        logger.info(f"Testing with existing chapter: {existing_chapter.chapter_number}")

        # Try to insert a duplicate
        try:
            duplicate_chapter = Chapter(
                manga_scanlator_id=mapping_id,
                chapter_number=existing_chapter.chapter_number,
                chapter_title="Duplicate Test",
                chapter_url="http://example.com/duplicate",
                detected_date=datetime.now(),
                read=False
            )

            db.add(duplicate_chapter)
            db.commit()

            # If we get here, the duplicate was inserted (BAD)
            logger.error("FAILED: Duplicate chapter was inserted!")
            db.rollback()
            return False

        except Exception as e:
            # This is expected - the unique constraint should prevent the duplicate
            db.rollback()
            logger.success("PASSED: Duplicate chapter was rejected as expected")
            logger.debug(f"Error (expected): {e}")
            return True

    finally:
        db.close()


async def run_test_tracking():
    """Run the tracking script in test mode."""
    logger.info("")
    print_separator()
    logger.info("RUNNING TEST TRACKING")
    print_separator()

    # Import the tracking script
    from scripts.track_chapters import ChapterTracker

    # Create tracker with limit of 1-2 mappings
    tracker = ChapterTracker(limit=2, headless=True)

    # Run tracking
    await tracker.track_all()


async def main():
    """Main entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test chapter tracking functionality"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run with visible browser for debugging"
    )
    parser.add_argument(
        "--skip-tracking",
        action="store_true",
        help="Skip the tracking test (only check database state)"
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("CHAPTER TRACKING TEST SUITE")
    logger.info("="*60)

    # Step 1: Check database state before tracking
    logger.info("\nSTEP 1: Pre-tracking database check")
    check_database_state()

    db = SessionLocal()
    verified_mappings = db.query(MangaScanlator).filter(
        MangaScanlator.manually_verified == True
    ).limit(2).all()
    db.close()

    if not verified_mappings:
        logger.error("\nNo verified mappings found! Cannot run test.")
        logger.info("Please add manga sources first:")
        logger.info("  python scripts/add_manga_source.py")
        return

    if not args.skip_tracking:
        # Step 2: Run tracking
        logger.info("\nSTEP 2: Running tracking test")
        await run_test_tracking()

        # Step 3: Verify chapters were inserted
        logger.info("\nSTEP 3: Verifying chapters were inserted")
        for mapping in verified_mappings:
            verify_chapters_inserted(mapping.id)

        # Step 4: Test duplicate detection
        logger.info("\nSTEP 4: Testing duplicate detection")
        test_duplicate_detection(verified_mappings[0].id)

        # Step 5: Run tracking again to test duplicate handling
        logger.info("\nSTEP 5: Running tracking again (should skip duplicates)")
        await run_test_tracking()

    # Final summary
    logger.info("")
    print_separator()
    logger.info("TEST SUMMARY")
    print_separator()
    check_database_state()

    logger.info("")
    logger.info("Test complete! Check the logs above for any errors.")
    print_separator()


if __name__ == "__main__":
    asyncio.run(main())
