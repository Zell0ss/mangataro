#!/usr/bin/env python3
"""
Debug script to inspect AsuraScans website structure.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


async def main():
    async with async_playwright() as p:
        logger.info("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Test the search URL
        search_term = "solo leveling"
        search_url = f"https://asuracomic.net/series?name={search_term}"

        logger.info(f"Navigating to: {search_url}")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

        # Wait for page to load
        await asyncio.sleep(5)

        # Take a screenshot
        await page.screenshot(path="/data/mangataro/debug_search.png")
        logger.info("Screenshot saved to debug_search.png")

        # Get page content
        content = await page.content()
        logger.info(f"Page content length: {len(content)} characters")

        # Try to find any grid or manga containers
        logger.info("\nLooking for grid elements...")
        grid_elements = await page.query_selector_all(".grid")
        logger.info(f"Found {len(grid_elements)} .grid elements")

        # Look for any links
        logger.info("\nLooking for links...")
        links = await page.query_selector_all("a")
        logger.info(f"Found {len(links)} links total")

        # Look for manga-related elements
        logger.info("\nLooking for manga-related elements...")
        manga_selectors = [".manga", ".series", "[class*='manga']", "[class*='series']", "article", "div.card"]
        for selector in manga_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                logger.info(f"  {selector}: {len(elements)} elements")

        # Print HTML structure of first few elements
        logger.info("\nHTML structure analysis...")
        html_structure = await page.evaluate("""
            () => {
                const mainContent = document.querySelector('main, .main-content, #content, .container');
                if (mainContent) {
                    return mainContent.innerHTML.substring(0, 2000);
                }
                return document.body.innerHTML.substring(0, 2000);
            }
        """)
        logger.info("Main content structure:")
        logger.info(html_structure)

        # Wait before closing
        logger.info("\nWaiting 10 seconds before closing (check the browser window)...")
        await asyncio.sleep(10)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
