#!/usr/bin/env python3
"""
Example usage of the scanlator plugin system.

This script demonstrates how to:
1. Import and discover scanlator plugins
2. Instantiate a scanlator with Playwright
3. Search for manga
4. Extract chapters from a manga page
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright
from loguru import logger
from scanlators import get_scanlator_classes, list_scanlators


async def example_usage():
    """Example of using the scanlator plugin system."""

    # Step 1: Discover available scanlators
    logger.info("=" * 60)
    logger.info("Scanlator Plugin System - Usage Example")
    logger.info("=" * 60)

    scanlator_classes = get_scanlator_classes()
    scanlator_names = list_scanlators()

    logger.info(f"\nDiscovered {len(scanlator_names)} scanlator(s): {scanlator_names}")

    if not scanlator_names:
        logger.warning("No scanlator plugins found. Create one by copying scanlators/template.py")
        return

    # Step 2: Select a scanlator (for this example, we'll use the first one)
    scanlator_name = scanlator_names[0]
    scanlator_class = scanlator_classes[scanlator_name]

    logger.info(f"\nUsing scanlator: {scanlator_name}")

    # Step 3: Launch Playwright and create a browser context
    async with async_playwright() as playwright:
        # Launch browser (headless=False to see the browser)
        browser = await playwright.chromium.launch(headless=True)

        # Create a new browser context
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # Create a new page
        page = await context.new_page()

        # Step 4: Instantiate the scanlator with the page
        scanlator = scanlator_class(page)

        logger.info(f"\nScanlator Info:")
        logger.info(f"  Name: {scanlator.name}")
        logger.info(f"  Base URL: {scanlator.base_url}")

        # Step 5: Example - Search for manga
        search_term = "One Piece"
        logger.info(f"\n[Example 1] Searching for '{search_term}'...")

        try:
            results = await scanlator.buscar_manga(search_term)
            logger.info(f"Found {len(results)} result(s)")

            for i, result in enumerate(results[:5], 1):  # Show first 5 results
                logger.info(f"  {i}. {result.get('titulo', 'N/A')}")
                logger.info(f"     URL: {result.get('url', 'N/A')}")
                logger.info(f"     Cover: {result.get('portada', 'N/A')[:60]}...")

        except Exception as e:
            logger.error(f"Error searching for manga: {e}")

        # Step 6: Example - Extract chapters from a manga page
        # Note: Replace with an actual manga URL from your scanlator
        manga_url = "https://example.com/manga/one-piece"  # Replace with real URL

        logger.info(f"\n[Example 2] Extracting chapters from: {manga_url}")

        try:
            chapters = await scanlator.obtener_capitulos(manga_url)
            logger.info(f"Found {len(chapters)} chapter(s)")

            for i, chapter in enumerate(chapters[:5], 1):  # Show first 5 chapters
                logger.info(f"  {i}. Chapter {chapter.get('numero', 'N/A')}: {chapter.get('titulo', 'N/A')}")
                logger.info(f"     URL: {chapter.get('url', 'N/A')}")
                logger.info(f"     Date: {chapter.get('fecha', 'N/A')}")

        except Exception as e:
            logger.error(f"Error extracting chapters: {e}")

        # Step 7: Example - Parse chapter numbers
        logger.info(f"\n[Example 3] Testing chapter number parsing...")

        test_cases = [
            "Chapter 42",
            "Ch. 42.5",
            "Capítulo 123",
            "Episode 5",
            "Vol. 2 Ch. 15"
        ]

        for test_text in test_cases:
            parsed = scanlator.parsear_numero_capitulo(test_text)
            logger.info(f"  '{test_text}' -> '{parsed}'")

        # Clean up
        await context.close()
        await browser.close()

    logger.info("\n" + "=" * 60)
    logger.info("Example complete!")
    logger.info("=" * 60)


async def main():
    """Main entry point."""
    # Configure logger
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    try:
        await example_usage()
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
