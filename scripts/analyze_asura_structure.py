#!/usr/bin/env python3
"""
Analyze AsuraScans website structure for manga listings.
"""

import asyncio
import sys
import json
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
        await page.goto(search_url, wait_until="networkidle", timeout=30000)

        # Wait a bit more for dynamic content
        await asyncio.sleep(3)

        # Extract detailed structure
        logger.info("\n=== Analyzing page structure ===\n")

        # Get all grid contents
        grid_analysis = await page.evaluate("""
            () => {
                const grids = document.querySelectorAll('.grid');
                return Array.from(grids).map((grid, idx) => ({
                    index: idx,
                    classes: grid.className,
                    childCount: grid.children.length,
                    sampleHTML: grid.innerHTML.substring(0, 500)
                }));
            }
        """)

        for grid in grid_analysis:
            logger.info(f"Grid {grid['index']}:")
            logger.info(f"  Classes: {grid['classes']}")
            logger.info(f"  Children: {grid['childCount']}")
            logger.info(f"  Sample HTML: {grid['sampleHTML'][:200]}...")
            logger.info("")

        # Look for manga cards more broadly
        logger.info("=== Looking for manga cards ===\n")
        manga_cards = await page.evaluate("""
            () => {
                // Try various selectors
                const selectors = [
                    'a[href*="/series/"]',
                    'div[class*="card"] a',
                    '.grid a',
                    'a img[alt]'
                ];

                let allLinks = new Set();
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        const href = el.href || el.closest('a')?.href;
                        if (href && href.includes('/series/')) {
                            allLinks.add(href);
                        }
                    });
                }

                // Get details for each unique link
                return Array.from(allLinks).slice(0, 5).map(url => {
                    const link = document.querySelector(`a[href="${url}"]`);
                    if (!link) return null;

                    const titleEl = link.querySelector('h3, h2, span, .title');
                    const imgEl = link.querySelector('img');

                    return {
                        url: url,
                        title: titleEl ? titleEl.textContent.trim() : link.textContent.trim().substring(0, 100),
                        cover: imgEl ? imgEl.src : '',
                        outerHTML: link.outerHTML.substring(0, 300)
                    };
                }).filter(x => x !== null);
            }
        """)

        logger.info(f"Found {len(manga_cards)} manga series links:")
        for card in manga_cards:
            logger.info(f"\n  Title: {card['title']}")
            logger.info(f"  URL: {card['url']}")
            logger.info(f"  Cover: {card['cover'][:80]}")
            logger.info(f"  HTML: {card['outerHTML'][:150]}...")

        # Try to find the actual search results container
        logger.info("\n=== Finding search results container ===\n")
        search_results = await page.evaluate("""
            () => {
                // Look for containers that might hold search results
                const possibleContainers = [
                    'main .grid',
                    '[class*="search"] .grid',
                    '[class*="result"] .grid',
                    'main > div > .grid'
                ];

                for (const selector of possibleContainers) {
                    const container = document.querySelector(selector);
                    if (container && container.children.length > 0) {
                        return {
                            selector: selector,
                            childCount: container.children.length,
                            innerHTML: container.innerHTML.substring(0, 1000)
                        };
                    }
                }
                return null;
            }
        """)

        if search_results:
            logger.info(f"Found container: {search_results['selector']}")
            logger.info(f"Children: {search_results['childCount']}")
            logger.info(f"Content preview: {search_results['innerHTML'][:300]}...")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
