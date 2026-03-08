#!/usr/bin/env python3
"""
Test script for MangaDex scanlator plugin.

Tests all three main methods using the live MangaDex API.
No browser required.

Usage:
    python scripts/test_manga_dex.py
    python scripts/test_manga_dex.py --search "bromance book club"
    python scripts/test_manga_dex.py --manga-url "https://mangadex.org/title/UUID/slug"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from loguru import logger
from scanlators.manga_dex import MangaDex

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


async def test_parsear_numero_capitulo(scanlator: MangaDex):
    logger.info("=" * 60)
    logger.info("TEST: parsear_numero_capitulo")
    logger.info("=" * 60)
    cases = [
        ("42", "42"),
        ("42.5", "42.5"),
        ("1", "1"),
        ("100", "100"),
        ("  7  ", "7"),
        ("Chapter 5", "5"),
    ]
    all_passed = True
    for text, expected in cases:
        result = scanlator.parsear_numero_capitulo(text)
        passed = result == expected
        if passed:
            logger.success(f"  PASS: '{text}' -> '{result}'")
        else:
            logger.error(f"  FAIL: '{text}' -> '{result}' (expected '{expected}')")
            all_passed = False
    return all_passed


async def test_buscar_manga(scanlator: MangaDex, search_term: str):
    logger.info("=" * 60)
    logger.info(f"TEST: buscar_manga('{search_term}')")
    logger.info("=" * 60)
    results = await scanlator.buscar_manga(search_term)
    if not results:
        logger.warning("No results found")
        return []
    logger.success(f"Found {len(results)} results:")
    for r in results[:5]:
        logger.info(f"  Title: {r['titulo']}")
        logger.info(f"  URL:   {r['url']}")
        logger.info(f"  Cover: {r['portada'][:80]}")
        logger.info("")
    return results


async def test_obtener_capitulos(scanlator: MangaDex, manga_url: str):
    logger.info("=" * 60)
    logger.info(f"TEST: obtener_capitulos")
    logger.info(f"  URL: {manga_url}")
    logger.info("=" * 60)
    capitulos = await scanlator.obtener_capitulos(manga_url)
    if not capitulos:
        logger.warning("No chapters found")
        return []
    logger.success(f"Found {len(capitulos)} chapters")
    logger.info("First 3:")
    for ch in capitulos[:3]:
        logger.info(f"  Ch.{ch['numero']:>6}  {ch['titulo'][:40]}  {ch['fecha']}  {ch['url']}")
    logger.info("Last 3:")
    for ch in capitulos[-3:]:
        logger.info(f"  Ch.{ch['numero']:>6}  {ch['titulo'][:40]}  {ch['fecha']}  {ch['url']}")
    return capitulos


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", default="bromance book club")
    parser.add_argument("--manga-url")
    args = parser.parse_args()

    async with async_playwright() as p:
        # MangaDex plugin doesn't use Playwright, but interface requires a page
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        scanlator = MangaDex(page)
        logger.success(f"Initialized: {scanlator}")

        try:
            # Test 1: parsear_numero_capitulo (no network)
            await test_parsear_numero_capitulo(scanlator)

            # Test 2: buscar_manga
            results = await test_buscar_manga(scanlator, args.search)

            # Test 3: obtener_capitulos
            manga_url = args.manga_url or (results[0]["url"] if results else None)
            if manga_url:
                await test_obtener_capitulos(scanlator, manga_url)
            else:
                logger.warning("No manga URL available for chapter test")

        finally:
            await browser.close()
            logger.success("Done!")


if __name__ == "__main__":
    asyncio.run(main())
