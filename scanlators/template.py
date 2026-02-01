"""
Template for creating new scanlator plugins.

Copy this file and rename it to match your scanlator (e.g., manhuaplus.py, asurascans.py).
Then implement the three abstract methods with site-specific logic.

Steps to create a new scanlator plugin:
1. Copy this file to scanlators/yourscanlator.py
2. Rename the class from TemplateScanlator to YourScanlatorScanlator
3. Set self.name and self.base_url in __init__
4. Implement buscar_manga() - search for manga on the site
5. Implement obtener_capitulos() - extract chapters from manga page
6. Implement parsear_numero_capitulo() - normalize chapter numbers
7. Test your plugin with the test script
"""

import re
from datetime import datetime
from playwright.async_api import Page
from loguru import logger

from scanlators.base import BaseScanlator


class TemplateScanlator(BaseScanlator):
    """
    Template scanlator plugin.

    Replace this docstring with information about the scanlator site.
    Example: "Plugin for ManhuaPlus (manhuaplus.com) - English manga scanlation site."
    """

    def __init__(self, playwright_page: Page):
        """Initialize the Template scanlator plugin."""
        super().__init__(playwright_page)

        # TODO: Set these to match the scanlator site
        self.name = "Template Scanlator"
        self.base_url = "https://example.com"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search for manga by title.

        Implementation guide:
        1. Navigate to the search page or use search API
        2. Enter the search term and submit
        3. Wait for results to load
        4. Extract each result's title, URL, and cover image
        5. Return list of candidates

        Typical patterns:
        - Search URL: f"{self.base_url}/search?q={titulo}"
        - Result selector: ".manga-item" or ".search-result"
        - Title selector: ".manga-title" or "h3 a"
        - URL selector: "a.manga-link" (get href attribute)
        - Cover selector: "img.manga-cover" (get src attribute)
        """
        logger.info(f"[{self.name}] Searching for: {titulo}")

        # TODO: Construct search URL
        search_url = f"{self.base_url}/search?q={titulo}"

        # Navigate to search page
        if not await self.safe_goto(search_url):
            logger.error(f"[{self.name}] Failed to load search page")
            return []

        try:
            # TODO: Wait for results to load (adjust selector to match site)
            # await self.page.wait_for_selector(".search-results", timeout=10000)

            # TODO: Extract search results
            # Example using evaluate:
            # resultados = await self.page.evaluate("""
            #     () => {
            #         const items = document.querySelectorAll('.manga-item');
            #         return Array.from(items).map(item => ({
            #             titulo: item.querySelector('.manga-title')?.textContent.trim(),
            #             url: item.querySelector('a')?.href,
            #             portada: item.querySelector('img')?.src
            #         }));
            #     }
            # """)

            # Example using locators (preferred method):
            # items = await self.page.locator(".manga-item").all()
            # resultados = []
            # for item in items:
            #     titulo = await item.locator(".manga-title").text_content()
            #     url = await item.locator("a").get_attribute("href")
            #     portada = await item.locator("img").get_attribute("src")
            #     resultados.append({
            #         "titulo": titulo.strip(),
            #         "url": url,
            #         "portada": portada
            #     })

            resultados = []  # TODO: Replace with actual extraction

            logger.info(f"[{self.name}] Found {len(resultados)} results for '{titulo}'")
            return resultados

        except Exception as e:
            logger.error(f"[{self.name}] Error searching for manga: {e}")
            return []

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Extract chapters from a manga page.

        Implementation guide:
        1. Navigate to the manga page
        2. Wait for chapter list to load
        3. Extract each chapter's number, title, URL, and date
        4. Parse chapter numbers using parsear_numero_capitulo()
        5. Parse dates into datetime objects
        6. Sort chapters from oldest to newest
        7. Return list of chapters

        Typical patterns:
        - Chapter list selector: ".chapter-list", "#chapters", ".episode-list"
        - Chapter item selector: ".chapter-item", "li.chapter", "tr.chapter"
        - Chapter title selector: ".chapter-title", "a.chapter-link"
        - Chapter URL: "a" element's href attribute
        - Date selector: ".chapter-date", "span.date", "time"
        - Date formats: "Jan 15, 2026", "2026-01-15", "15/01/2026", "2 days ago"
        """
        logger.info(f"[{self.name}] Extracting chapters from: {manga_url}")

        # Navigate to manga page
        if not await self.safe_goto(manga_url):
            logger.error(f"[{self.name}] Failed to load manga page")
            return []

        try:
            # TODO: Wait for chapter list to load (adjust selector to match site)
            # await self.page.wait_for_selector(".chapter-list", timeout=10000)

            # TODO: Extract chapters
            # Example using evaluate:
            # capitulos_raw = await self.page.evaluate("""
            #     () => {
            #         const items = document.querySelectorAll('.chapter-item');
            #         return Array.from(items).map(item => ({
            #             texto: item.querySelector('.chapter-title')?.textContent.trim(),
            #             url: item.querySelector('a')?.href,
            #             fecha_texto: item.querySelector('.chapter-date')?.textContent.trim()
            #         }));
            #     }
            # """)

            # Example using locators (preferred method):
            # items = await self.page.locator(".chapter-item").all()
            # capitulos_raw = []
            # for item in items:
            #     texto = await item.locator(".chapter-title").text_content()
            #     url = await item.locator("a").get_attribute("href")
            #     fecha_texto = await item.locator(".chapter-date").text_content()
            #     capitulos_raw.append({
            #         "texto": texto.strip(),
            #         "url": url,
            #         "fecha_texto": fecha_texto.strip()
            #     })

            capitulos_raw = []  # TODO: Replace with actual extraction

            # Process and normalize chapters
            capitulos = []
            for cap in capitulos_raw:
                # Parse chapter number
                numero = self.parsear_numero_capitulo(cap["texto"])

                # TODO: Parse date - implement based on site's date format
                # Examples:
                # fecha = self._parse_date(cap["fecha_texto"])
                # Or use datetime.now() if no date available
                fecha = datetime.now()

                capitulos.append({
                    "numero": numero,
                    "titulo": cap["texto"],
                    "url": cap["url"],
                    "fecha": fecha
                })

            # Sort chapters from oldest to newest
            capitulos.sort(key=lambda x: (float(x["numero"]) if x["numero"].replace(".", "").isdigit() else 0, x["fecha"]))

            logger.info(f"[{self.name}] Extracted {len(capitulos)} chapters")
            return capitulos

        except Exception as e:
            logger.error(f"[{self.name}] Error extracting chapters: {e}")
            return []

    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Parse chapter number from text.

        Implementation guide:
        1. Remove common prefixes: "Chapter", "Ch.", "Cap.", "Episode", etc.
        2. Extract numeric part (including decimals)
        3. Handle special cases: "Chapter 42.5", "Ch. 123", "Episode 1"
        4. Return normalized number as string

        Common patterns:
        - "Chapter 42" -> "42"
        - "Ch. 42.5" -> "42.5"
        - "Capítulo 123" -> "123"
        - "Episode 5" -> "5"
        - "Vol. 2 Ch. 15" -> "15"
        """
        # TODO: Implement based on site's chapter numbering format

        # Example implementation:
        # Remove common prefixes
        texto = texto.lower()
        texto = re.sub(r"(chapter|ch\.?|cap\.?|capítulo|episode|ep\.?)\s*", "", texto, flags=re.IGNORECASE)

        # Extract first number (including decimals)
        match = re.search(r"(\d+(?:\.\d+)?)", texto)
        if match:
            return match.group(1)

        # Fallback: return original text if no number found
        return texto.strip()

    def _parse_date(self, fecha_texto: str) -> datetime:
        """
        Helper method to parse dates from various formats.

        Add this method if the site has dates. Implement based on the site's date format.

        Common date formats:
        - "Jan 15, 2026" -> strptime("%b %d, %Y")
        - "2026-01-15" -> strptime("%Y-%m-%d")
        - "15/01/2026" -> strptime("%d/%m/%Y")
        - "2 days ago" -> calculate from current date
        - "Yesterday" -> calculate from current date
        """
        # TODO: Implement date parsing based on site format

        # Example for "Jan 15, 2026" format:
        # try:
        #     return datetime.strptime(fecha_texto, "%b %d, %Y")
        # except ValueError:
        #     return datetime.now()

        # Example for "X days ago" format:
        # match = re.search(r"(\d+)\s+days?\s+ago", fecha_texto, re.IGNORECASE)
        # if match:
        #     days = int(match.group(1))
        #     return datetime.now() - timedelta(days=days)

        # Example for "Yesterday":
        # if "yesterday" in fecha_texto.lower():
        #     return datetime.now() - timedelta(days=1)

        return datetime.now()
