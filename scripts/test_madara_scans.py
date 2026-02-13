#!/usr/bin/env python3
"""
Test script for MadaraScans scanlator plugin.

This script tests all three main methods of the MadaraScans plugin:
1. buscar_manga() - Search for manga
2. obtener_capitulos() - Extract chapters from a manga page
3. parsear_numero_capitulo() - Parse chapter numbers

Usage:
    python scripts/test_madara_scans.py
    python scripts/test_madara_scans.py --headless  # Run browser in headless mode
    python scripts/test_madara_scans.py --search "solo leveling"  # Custom search term
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import scanlators module
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from loguru import logger
from scanlators.madara_scans import MadaraScans


# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


async def test_buscar_manga(scanlator: MadaraScans, search_term: str = "solo leveling"):
    """
    Test the buscar_manga method.

    Args:
        scanlator: MadaraScans instance
        search_term: Term to search for (default: "solo leveling")
    """
    logger.info("="*70)
    logger.info(f"TEST 1: Searching for '{search_term}'")
    logger.info("="*70)

    try:
        resultados = await scanlator.buscar_manga(search_term)

        if not resultados:
            logger.warning(f"No results found for '{search_term}'")
            return []

        logger.success(f"Found {len(resultados)} results:")
        for idx, resultado in enumerate(resultados, 1):
            logger.info(f"\n  Result {idx}:")
            logger.info(f"    Title:  {resultado.get('titulo', 'N/A')}")
            logger.info(f"    URL:    {resultado.get('url', 'N/A')}")
            logger.info(f"    Cover:  {resultado.get('portada', 'N/A')[:80]}...")

        return resultados

    except Exception as e:
        logger.error(f"Error in test_buscar_manga: {e}")
        return []


async def test_obtener_capitulos(scanlator: MadaraScans, manga_url: str):
    """
    Test the obtener_capitulos method.

    Args:
        scanlator: MadaraScans instance
        manga_url: URL of the manga page
    """
    logger.info("\n" + "="*70)
    logger.info(f"TEST 2: Extracting chapters from manga")
    logger.info("="*70)
    logger.info(f"URL: {manga_url}")

    try:
        capitulos = await scanlator.obtener_capitulos(manga_url)

        if not capitulos:
            logger.warning("No chapters found")
            return []

        logger.success(f"Found {len(capitulos)} chapters")

        # Show first 5 chapters
        logger.info("\nFirst 5 chapters:")
        for cap in capitulos[:5]:
            logger.info(f"  Ch. {cap.get('numero', 'N/A'):>6} - {cap.get('titulo', 'N/A')[:50]}")
            logger.info(f"           URL:  {cap.get('url', 'N/A')[:70]}...")
            logger.info(f"           Date: {cap.get('fecha', 'N/A')}")

        # Show last 5 chapters
        if len(capitulos) > 5:
            logger.info("\nLast 5 chapters:")
            for cap in capitulos[-5:]:
                logger.info(f"  Ch. {cap.get('numero', 'N/A'):>6} - {cap.get('titulo', 'N/A')[:50]}")
                logger.info(f"           URL:  {cap.get('url', 'N/A')[:70]}...")
                logger.info(f"           Date: {cap.get('fecha', 'N/A')}")

        return capitulos

    except Exception as e:
        logger.error(f"Error in test_obtener_capitulos: {e}")
        return []


def test_parsear_numero_capitulo(scanlator: MadaraScans):
    """
    Test the parsear_numero_capitulo method with various inputs.

    Args:
        scanlator: MadaraScans instance
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Parsing chapter numbers")
    logger.info("="*70)

    # Test cases: (input, expected_output)
    test_cases = [
        ("Chapter 42", "42"),
        ("Ch. 42.5", "42.5"),
        ("Chapter 100: The Final Battle", "100"),
        ("Episode 5", "5"),
        ("Ch 123.5", "123.5"),
        ("Capítulo 77", "77"),
        ("chapter 1", "1"),
        ("CHAPTER 99", "99"),
        ("Ch.200", "200"),
        ("15", "15"),
        ("Chapter 1.5: Prologue", "1.5"),
    ]

    logger.info("\nTest cases:")
    all_passed = True

    for input_text, expected in test_cases:
        result = scanlator.parsear_numero_capitulo(input_text)
        passed = result == expected
        status = "PASS" if passed else "FAIL"
        status_color = "green" if passed else "red"

        if passed:
            logger.success(f"  {status}: '{input_text}' -> '{result}'")
        else:
            logger.error(f"  {status}: '{input_text}' -> '{result}' (expected '{expected}')")
            all_passed = False

    if all_passed:
        logger.success("\nAll test cases passed!")
    else:
        logger.warning("\nSome test cases failed")


async def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(description='Test MadaraScans scanlator plugin')
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window)'
    )
    parser.add_argument(
        '--search',
        default='solo leveling',
        help='Search term to use for testing (default: "solo leveling")'
    )
    parser.add_argument(
        '--manga-url',
        help='Specific manga URL to test (skips search)'
    )

    args = parser.parse_args()

    logger.info("="*70)
    logger.info("MadaraScans Plugin Test Suite")
    logger.info("="*70)
    logger.info(f"Headless mode: {args.headless}")
    logger.info(f"Search term: {args.search}")
    logger.info("="*70)

    async with async_playwright() as p:
        logger.info("\nLaunching browser...")
        browser = await p.chromium.launch(headless=args.headless)
        page = await browser.new_page()

        # Initialize scanlator
        scanlator = MadaraScans(page)
        logger.success(f"Initialized: {scanlator}")

        try:
            # Test 1: Search for manga
            if args.manga_url:
                # Skip search if URL provided
                logger.info(f"\nUsing provided manga URL: {args.manga_url}")
                manga_url = args.manga_url
                resultados = []
            else:
                resultados = await test_buscar_manga(scanlator, args.search)
                if not resultados:
                    logger.error("Search returned no results. Cannot continue with chapter extraction test.")
                    await browser.close()
                    return

                # Use the first result for chapter extraction
                manga_url = resultados[0]['url']

            # Wait a bit between tests
            await asyncio.sleep(2)

            # Test 2: Extract chapters
            if manga_url:
                capitulos = await test_obtener_capitulos(scanlator, manga_url)

            # Test 3: Parse chapter numbers (doesn't require network)
            test_parsear_numero_capitulo(scanlator)

            # Summary
            logger.info("\n" + "="*70)
            logger.info("TEST SUMMARY")
            logger.info("="*70)
            if resultados:
                logger.info(f"  Search results:  {len(resultados)} manga found")
            if 'capitulos' in locals():
                logger.info(f"  Chapters found:  {len(capitulos)} chapters")
            logger.info("  Chapter parsing: See results above")
            logger.info("="*70)

        except KeyboardInterrupt:
            logger.warning("\nTest interrupted by user")
        except Exception as e:
            logger.error(f"\nTest failed with error: {e}")
            raise
        finally:
            logger.info("\nClosing browser...")
            await browser.close()
            logger.success("Tests complete!")


if __name__ == '__main__':
    asyncio.run(main())
