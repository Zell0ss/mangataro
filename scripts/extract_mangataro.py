#!/usr/bin/env python3
"""
MangaTaro Extractor Script

This script processes the MangaTaro export JSON file and:
1. Downloads cover images
2. Scrapes manga pages for additional information
3. Inserts data into the database
4. Generates markdown fichas
5. Creates a scanlators checklist
"""

import json
import sys
import time
import random
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import api modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from sqlalchemy.exc import IntegrityError

from api.database import SessionLocal
from api.models import Manga, Scanlator, MangaScanlator
from api.utils import download_image, slugify, create_markdown_ficha, create_scanlators_checklist


# Configure logging
logger.add(
    "/data/mangataro/logs/extract_mangataro_{time}.log",
    rotation="500 MB",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


class MangaTaroExtractor:
    """Extract manga data from MangaTaro export and scrape additional info."""

    def __init__(self, export_file: str, test_mode: bool = False):
        """
        Initialize the extractor.

        Args:
            export_file: Path to the MangaTaro export JSON file
            test_mode: If True, only process the first manga
        """
        self.export_file = export_file
        self.test_mode = test_mode
        self.base_dir = Path(__file__).parent.parent
        self.img_dir = self.base_dir / "data" / "img"
        self.fichas_dir = self.base_dir / "docs" / "fichas"
        self.scanlators_found = []
        self.db = SessionLocal()

    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'db'):
            self.db.close()

    def load_export_data(self) -> dict:
        """Load the MangaTaro export JSON file."""
        logger.info(f"Loading export data from: {self.export_file}")
        with open(self.export_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data.get('bookmarks', []))} bookmarks")
        return data

    def scrape_manga_page(self, url: str, browser) -> dict:
        """
        Scrape a manga page for additional information.

        Args:
            url: The URL of the manga page
            browser: Playwright browser instance

        Returns:
            Dict with 'alternative_titles' and 'scanlator_group'
        """
        result = {
            'alternative_titles': None,
            'scanlator_group': None
        }

        try:
            logger.info(f"Scraping manga page: {url}")
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Wait a bit for dynamic content to load
            time.sleep(2)

            # Try multiple selectors for alternative titles
            # Look for a paragraph or div containing "/" separated titles
            alt_title_selectors = [
                'p:has-text("/")',
                'div.alternative-titles',
                'div.alt-titles',
                '.manga-info p:has-text("/")',
                '.info-section p:has-text("/")',
                'p.alt-title',
            ]

            for selector in alt_title_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        text = element.text_content().strip()
                        # Check if it looks like alternative titles (contains "/")
                        if '/' in text and len(text) < 500:
                            result['alternative_titles'] = text
                            logger.info(f"Found alternative titles: {text[:100]}...")
                            break
                except Exception as e:
                    continue

            # Try multiple selectors for scanlation group
            # Look for links or text mentioning the group
            scanlator_selectors = [
                'a[href*="scanlator"]',
                'a[href*="group"]',
                '.scanlator-name',
                '.group-name',
                'a.scanlation-group',
                '.manga-info a[href*="team"]',
                'a:has-text("Scanlation")',
            ]

            for selector in scanlator_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        text = element.text_content().strip()
                        # Clean up the text - remove chapter counts and "View Group Profile"
                        import re
                        text = re.sub(r'\d+\s+chapters?', '', text)
                        text = re.sub(r'View\s+Group\s+Profile', '', text, flags=re.IGNORECASE)
                        text = text.strip()
                        if text and len(text) < 100:
                            result['scanlator_group'] = text
                            logger.info(f"Found scanlation group: {text}")
                            break
                except Exception as e:
                    continue

            # If no scanlator found with specific selectors, try generic approach
            # Look for text patterns like "Scanlation: GroupName" or "Group: GroupName"
            if not result['scanlator_group']:
                try:
                    page_content = page.content()
                    # Try to find patterns in the HTML
                    import re
                    patterns = [
                        r'[Ss]canlation[:\s]+([A-Za-z0-9\s]+)',
                        r'[Gg]roup[:\s]+([A-Za-z0-9\s]+)',
                        r'[Tt]eam[:\s]+([A-Za-z0-9\s]+)',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, page_content)
                        if match:
                            group_name = match.group(1).strip()[:100]
                            if group_name and not any(x in group_name.lower() for x in ['<', '>', 'div', 'span', 'class']):
                                result['scanlator_group'] = group_name
                                logger.info(f"Found scanlation group via pattern: {group_name}")
                                break
                except Exception as e:
                    logger.debug(f"Pattern matching failed: {e}")

            page.close()

        except PlaywrightTimeout:
            logger.error(f"Timeout while scraping {url}")
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

        return result

    def find_or_create_scanlator(self, name: str) -> Scanlator:
        """
        Find an existing scanlator or create a new one.

        Args:
            name: The name of the scanlation group

        Returns:
            Scanlator object
        """
        if not name:
            name = "Unknown"

        # Check if scanlator already exists
        scanlator = self.db.query(Scanlator).filter(Scanlator.name == name).first()

        if scanlator:
            logger.debug(f"Found existing scanlator: {name}")
            return scanlator

        # Create new scanlator
        class_name = slugify(name).replace('-', '_')
        scanlator = Scanlator(
            name=name,
            class_name=class_name,
            active=False  # Will be manually verified later
        )
        self.db.add(scanlator)
        try:
            self.db.commit()
            logger.success(f"Created new scanlator: {name}")
        except IntegrityError:
            self.db.rollback()
            # Another thread might have created it
            scanlator = self.db.query(Scanlator).filter(Scanlator.name == name).first()

        return scanlator

    def process_manga(self, bookmark: dict, browser) -> bool:
        """
        Process a single manga bookmark.

        Args:
            bookmark: The bookmark data from the export
            browser: Playwright browser instance

        Returns:
            True if successful, False otherwise
        """
        title = bookmark.get('title')
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {title}")
        logger.info(f"{'='*60}")

        try:
            # 1. Download cover image
            cover_url = bookmark.get('cover')
            if cover_url:
                try:
                    cover_filename = download_image(cover_url, str(self.img_dir))
                except Exception as e:
                    logger.error(f"Failed to download cover: {e}")
                    cover_filename = None
            else:
                cover_filename = None

            # 2. Scrape manga page for additional info
            manga_url = bookmark.get('url')
            # Handle relative URLs
            if manga_url and manga_url.startswith('/'):
                manga_url = f"https://mangataro.org{manga_url}"
            scraped_data = self.scrape_manga_page(manga_url, browser)

            # 3. Find or create scanlator
            scanlator_name = scraped_data.get('scanlator_group') or "Unknown"
            scanlator = self.find_or_create_scanlator(scanlator_name)
            self.scanlators_found.append(scanlator_name)

            # 4. Parse date_added
            date_added_str = bookmark.get('dateAdded')
            if date_added_str:
                date_added = datetime.strptime(date_added_str, '%Y-%m-%d %H:%M:%S')
            else:
                date_added = datetime.now()

            # 5. Insert manga into database
            manga = Manga(
                mangataro_id=bookmark.get('id'),
                title=title,
                alternative_titles=scraped_data.get('alternative_titles'),
                cover_filename=cover_filename,
                mangataro_url=manga_url,
                date_added=date_added,
                last_checked=datetime.now()
            )
            self.db.add(manga)
            self.db.commit()
            self.db.refresh(manga)
            logger.success(f"Manga saved to database: {title} (ID: {manga.id})")

            # 6. Create manga-scanlator relationship
            manga_scanlator = MangaScanlator(
                manga_id=manga.id,
                scanlator_id=scanlator.id,
                scanlator_manga_url=manga_url,  # For now, use MangaTaro URL
                manually_verified=False
            )
            self.db.add(manga_scanlator)
            self.db.commit()
            logger.success(f"Linked manga to scanlator: {scanlator.name}")

            # 7. Generate markdown ficha
            try:
                create_markdown_ficha(
                    title=title,
                    alternative_titles=scraped_data.get('alternative_titles') or "",
                    cover_filename=cover_filename or "placeholder.png",
                    scanlator_group=scanlator_name,
                    mangataro_url=manga_url,
                    date_added=date_added,
                    save_dir=str(self.fichas_dir)
                )
            except Exception as e:
                logger.error(f"Failed to create markdown ficha: {e}")

            logger.success(f"Successfully processed: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to process {title}: {e}")
            self.db.rollback()
            return False

    def run(self):
        """Run the extraction process."""
        logger.info("="*60)
        logger.info("MangaTaro Extractor Started")
        logger.info(f"Test Mode: {self.test_mode}")
        logger.info("="*60)

        # Load export data
        export_data = self.load_export_data()
        bookmarks = export_data.get('bookmarks', [])

        if self.test_mode:
            logger.warning("TEST MODE: Processing only the first manga")
            bookmarks = bookmarks[:1]

        # Initialize Playwright
        with sync_playwright() as p:
            logger.info("Launching browser...")
            browser = p.chromium.launch(headless=True)

            # Process each bookmark
            total = len(bookmarks)
            successful = 0
            failed = 0

            for idx, bookmark in enumerate(bookmarks, 1):
                logger.info(f"\nProgress: {idx}/{total}")

                success = self.process_manga(bookmark, browser)

                if success:
                    successful += 1
                else:
                    failed += 1

                # Add delay between requests (2-5 seconds)
                if idx < total:
                    delay = random.uniform(2, 5)
                    logger.info(f"Waiting {delay:.1f} seconds before next request...")
                    time.sleep(delay)

            browser.close()

        # Generate scanlators checklist
        logger.info("\nGenerating scanlators checklist...")
        scanlators_path = self.base_dir / "docs" / "scanlators.md"
        create_scanlators_checklist(self.scanlators_found, str(scanlators_path))

        # Summary
        logger.info("\n" + "="*60)
        logger.info("EXTRACTION COMPLETE")
        logger.info("="*60)
        logger.info(f"Total bookmarks: {total}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Unique scanlators found: {len(set(self.scanlators_found))}")
        logger.info("="*60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract manga data from MangaTaro export')
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: only process the first manga'
    )
    parser.add_argument(
        '--export-file',
        default='/data/mangataro/mangataro-export.json',
        help='Path to the MangaTaro export JSON file'
    )

    args = parser.parse_args()

    # Run the extractor
    extractor = MangaTaroExtractor(
        export_file=args.export_file,
        test_mode=args.test
    )
    extractor.run()


if __name__ == '__main__':
    main()
