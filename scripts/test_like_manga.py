"""
Test script for LikeManga scanlator plugin.
Usage: python scripts/test_like_manga.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from scanlators.like_manga import LikeManga


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        plugin = LikeManga(page)

        print("=== TEST 1: buscar_manga('solo leveling') ===")
        results = await plugin.buscar_manga("solo leveling")
        print(f"Results: {len(results)}")
        for r in results[:5]:
            print(f"  {r['titulo']}")
            print(f"    url: {r['url']}")
            print(f"    portada: {r['portada'][:60]}...")

        print("\n=== TEST 2: obtener_capitulos (Solo Leveling: Ragnarok) ===")
        url = "https://likemanga.ink/solo-leveling-ragnarok-28849/"
        chapters = await plugin.obtener_capitulos(url)
        print(f"Chapters found: {len(chapters)}")
        if chapters:
            print(f"  First: #{chapters[0]['numero']} — {chapters[0]['titulo']} ({chapters[0]['fecha'].strftime('%Y-%m-%d')})")
            print(f"  Last:  #{chapters[-1]['numero']} — {chapters[-1]['titulo']} ({chapters[-1]['fecha'].strftime('%Y-%m-%d')})")
            print(f"  URL sample: {chapters[-1]['url']}")

        await browser.close()


asyncio.run(main())
