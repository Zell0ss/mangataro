"""
MadaraScans scanlator plugin.

Plugin for MadaraScans (madarascans.com) - English/Spanish manga and manhwa
scanlation site with dynamic chapter loading.
"""

import re
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import Page
from loguru import logger

from scanlators.base import BaseScanlator


class MadaraScans(BaseScanlator):
    """
    Plugin for MadaraScans (madarascans.com).

    MadaraScans is a scanlation group serving English and Spanish readers
    with manga and manhwa translations.
    """

    def __init__(self, playwright_page: Page):
        """Initialize the MadaraScans scanlator plugin."""
        super().__init__(playwright_page)

        self.name = "Madara Scans"
        self.base_url = "https://madarascans.com"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search for manga by title on MadaraScans.

        Args:
            titulo: The manga title to search for

        Returns:
            List of manga results with titulo, url, and portada
        """
        logger.info(f"[{self.name}] Searching for: {titulo}")

        # WordPress search URL
        search_url = f"{self.base_url}/?s={titulo}"

        if not await self.safe_goto(search_url):
            logger.error(f"[{self.name}] Failed to load search page")
            return []

        try:
            # Wait for search results
            await self.page.wait_for_selector('a[href*="/series/"]', timeout=10000)
            await asyncio.sleep(1)  # Allow dynamic content to settle

            # Extract manga entries
            resultados = await self.page.evaluate("""
                () => {
                    const items = document.querySelectorAll('a[href*="/series/"]');
                    const seen = new Set();
                    const results = [];

                    for (const item of items) {
                        const url = item.href;
                        if (seen.has(url)) continue;
                        seen.add(url);

                        // Extract title (from headings or spans)
                        const titleEl = item.querySelector('h1, h2, h3, h4, .title, .manga-title');
                        const titulo = titleEl ? titleEl.textContent.trim() : item.textContent.trim();

                        // Extract cover image
                        const imgEl = item.querySelector('img');
                        const portada = imgEl ? (imgEl.src || imgEl.dataset.src || '') : '';

                        if (titulo && url) {
                            results.push({ titulo, url, portada });
                        }
                    }

                    return results;
                }
            """)

            logger.info(f"[{self.name}] Found {len(resultados)} results for '{titulo}'")
            return resultados

        except Exception as e:
            logger.error(f"[{self.name}] Error searching for manga: {e}")
            return []

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Extract chapters from a manga page on MadaraScans.

        This implementation clicks the "Load More" button repeatedly until
        all chapters are loaded before extracting.

        Args:
            manga_url: Full URL to the manga's page

        Returns:
            List of chapters with numero, titulo, url, and fecha
        """
        # TODO: Implement in next task
        pass

    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Parse chapter number from text.

        Handles formats like:
        - "Chapter 42" → "42"
        - "Ch. 42.5" → "42.5"
        - "Chapter 1: Title" → "1"

        Args:
            texto: Raw text containing the chapter number

        Returns:
            Normalized chapter number as string
        """
        # TODO: Implement in next task
        pass

    def _parse_date(self, fecha_texto: str) -> datetime:
        """
        Parse date from various formats used by MadaraScans.

        Handles:
        - "2 days ago", "1 week ago"
        - "Jan 15, 2026"
        - "2026-01-15"
        - "yesterday", "today"

        Args:
            fecha_texto: Raw date text

        Returns:
            datetime object (defaults to now if parsing fails)
        """
        # TODO: Implement in next task
        pass
