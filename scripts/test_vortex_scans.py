#!/usr/bin/env python3
"""
Test script for VortexScans scanlator plugin.

Tests all three main methods against the live VortexScans site.

Usage:
    python scripts/test_vortex_scans.py
    python scripts/test_vortex_scans.py --search "rankers return"
    python scripts/test_vortex_scans.py --manga-url "https://vortexscans.org/series/rankers-return-c6f3k3os"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from loguru import logger
from scanlators.vortex_scans import VortexScans

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


async def test_parsear_numero_capitulo(scanlator: VortexScans):
    logger.info("=" * 60)
    logger.info("TEST: parsear_numero_capitulo")
    logger.info("=" * 60)
    cases = [
        ("233", "233"),
        ("42.5", "42.5"),
        ("1", "1"),
        ("Chapter 5", "5"),
        ("  10  ", "10"),
    ]
    all_passed = True
    for text, expected in cases:
        result = scanlator.parsear_numero_capitulo(text)
        passed = result == expected
        status = "PASS" if passed else "FAIL"
        msg = f"  {status}: '{text}' -> '{result}'"
        if not passed:
            msg += f" (expected '{expected}')"
            all_passed = False
        logger.info(msg)
    return all_passed


async def test_buscar_manga(scanlator: VortexScans, search_term: str):
    logger.info("=" * 60)
    logger.info(f"TEST: buscar_manga('{search_term}')")
    logger.info("=" * 60)
    results = await scanlator.buscar_manga(search_term)
    if not results:
        logger.warning("No results found")
        return []
    logger.success(f"Found {len(results)} results:")
    for r in results[:5]:
        logger.info(f"  Title:  {r['titulo']}")
        logger.info(f"  URL:    {r['url']}")
        logger.info(f"  Cover:  {r['portada'][:80]}")
        logger.info("")
    return results


async def test_obtener_capitulos(scanlator: VortexScans, manga_url: str):
    logger.info("=" * 60)
    logger.info("TEST: obtener_capitulos")
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
    parser.add_argument("--search", default="rankers return")
    parser.add_argument("--manga-url", default=None)
    args = parser.parse_args()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        scanlator = VortexScans(page)
        logger.success(f"Initialized: {scanlator}")

        try:
            # Test 1: parsear_numero_capitulo (no network)
            await test_parsear_numero_capitulo(scanlator)

            # Test 2: buscar_manga (httpx only)
            results = await test_buscar_manga(scanlator, args.search)

            # Test 3: obtener_capitulos (Playwright + httpx)
            manga_url = (
                args.manga_url
                or (results[0]["url"] if results else None)
                or "https://vortexscans.org/series/rankers-return-c6f3k3os"
            )
            await test_obtener_capitulos(scanlator, manga_url)

        finally:
            await browser.close()
            logger.success("Done!")


if __name__ == "__main__":
    asyncio.run(main())
