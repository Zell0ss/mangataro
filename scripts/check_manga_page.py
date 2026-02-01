#!/usr/bin/env python3
"""
Check structure of a manga page on AsuraScans.
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

        # Use a known manga page
        manga_url = "https://asuracomic.net/series/solo-leveling-ragnarok-55b73268"

        logger.info(f"Navigating to: {manga_url}")
        await page.goto(manga_url, wait_until="domcontentloaded", timeout=30000)

        # Wait a bit more
        await asyncio.sleep(3)

        # Look for chapter links
        logger.info("\n=== Looking for chapter links ===\n")
        chapter_analysis = await page.evaluate("""
            () => {
                // Try various selectors for chapter links
                const selectors = [
                    'a[href*="/chapter"]',
                    'a[href*="chapter-"]',
                    'div[class*="chapter"] a',
                    '.chapter-list a',
                    'a[class*="chapter"]'
                ];

                let allChapters = [];
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        allChapters.push({
                            selector: selector,
                            count: elements.length,
                            samples: Array.from(elements).slice(0, 3).map(el => ({
                                href: el.href,
                                text: el.textContent.trim().substring(0, 100),
                                html: el.outerHTML.substring(0, 200)
                            }))
                        });
                    }
                }

                return allChapters;
            }
        """)

        for result in chapter_analysis:
            logger.info(f"Selector: {result['selector']}")
            logger.info(f"Count: {result['count']}")
            logger.info("Samples:")
            for sample in result['samples']:
                logger.info(f"  - {sample['text']}")
                logger.info(f"    URL: {sample['href']}")
                logger.info(f"    HTML: {sample['html'][:150]}...")
            logger.info("")

        # Check if there are tabs or sections
        logger.info("=== Checking for tabs/sections ===\n")
        tabs_info = await page.evaluate("""
            () => {
                const tabs = document.querySelectorAll('[role="tab"], button[class*="tab"]');
                return Array.from(tabs).map(tab => ({
                    text: tab.textContent.trim(),
                    ariaSelected: tab.getAttribute('aria-selected'),
                    dataState: tab.getAttribute('data-state')
                }));
            }
        """)

        if tabs_info:
            logger.info("Found tabs:")
            for tab in tabs_info:
                logger.info(f"  - {tab['text']} (selected: {tab['ariaSelected']}, state: {tab['dataState']})")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
