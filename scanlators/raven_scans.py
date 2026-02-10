"""
Raven Scans scanlator plugin.
Website: https://ravenscans.org/
"""

import re
from datetime import datetime
from playwright.async_api import Page
from scanlators.base import BaseScanlator
from loguru import logger


class RavenScans(BaseScanlator):
    """Scanlator plugin for Raven Scans"""

    def __init__(self, playwright_page: Page):
        super().__init__(playwright_page)
        self.name = "RavenScans"
        self.base_url = "https://ravenscans.org"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search for manga on Raven Scans.

        Args:
            titulo: Manga title to search for

        Returns:
            List of manga results with titulo, url, portada
        """
        try:
            # Construct search URL
            search_url = f"{self.base_url}/?s={titulo}"
            logger.info(f"[{self.name}] Searching: {search_url}")

            if not await self.safe_goto(search_url):
                return []

            # Wait for search results to load
            await self.page.wait_for_selector("article.item-thumb, .c-tabs-item__content", timeout=10000)

            resultados = []

            # Try to find manga results (common selectors for WordPress manga themes)
            items = await self.page.locator("article.item-thumb, .post-title a, .manga-item").all()

            for item in items:
                try:
                    # Try to get title and URL
                    link = await item.locator("a").first
                    if not link:
                        link = item

                    url = await link.get_attribute("href")
                    titulo_text = await link.text_content()

                    # Try to get cover image
                    img = await item.locator("img").first
                    portada = await img.get_attribute("src") if img else ""

                    if url and titulo_text:
                        resultados.append({
                            "titulo": titulo_text.strip(),
                            "url": url.strip(),
                            "portada": portada.strip() if portada else ""
                        })
                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing search item: {e}")
                    continue

            logger.info(f"[{self.name}] Found {len(resultados)} results")
            return resultados

        except Exception as e:
            logger.error(f"[{self.name}] Search error: {e}")
            return []

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Get all chapters from a manga page.

        Args:
            manga_url: URL of the manga page

        Returns:
            List of chapters with numero, titulo, url, fecha
        """
        try:
            logger.info(f"[{self.name}] Fetching chapters from: {manga_url}")

            if not await self.safe_goto(manga_url):
                return []

            # Wait for chapters to load (JavaScript renders them)
            # Raven Scans uses .chbox containers for chapters
            await self.page.wait_for_selector(".chbox", timeout=10000)

            capitulos = []

            # Get all chapter boxes
            items = await self.page.locator(".chbox").all()

            for item in items:
                try:
                    # Get chapter link from .eph-num div
                    link = item.locator(".eph-num a").first
                    if not link:
                        continue

                    url = await link.get_attribute("href")
                    texto = await link.text_content()

                    if not url or not texto:
                        continue

                    # Text format: "Chapter 147\nSeptember 11, 2025"
                    lines = texto.strip().split('\n')
                    chapter_line = lines[0] if lines else texto

                    # Parse chapter number
                    numero = self.parsear_numero_capitulo(chapter_line)

                    # Parse date from second line if available
                    fecha = None
                    if len(lines) > 1:
                        fecha_texto = lines[1].strip()
                        fecha = self._parse_date(fecha_texto)
                    else:
                        # Try to extract date from the full text
                        date_match = re.search(r'(\w+ \d+, \d{4})', texto)
                        if date_match:
                            fecha = self._parse_date(date_match.group(1))

                    if not fecha:
                        fecha = datetime.now()

                    capitulos.append({
                        "numero": numero,
                        "titulo": texto.strip(),
                        "url": url.strip(),
                        "fecha": fecha
                    })

                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing chapter: {e}")
                    continue

            # Sort chapters: oldest to newest
            capitulos.sort(key=lambda x: (float(x["numero"]), x["fecha"]))

            logger.info(f"[{self.name}] Found {len(capitulos)} chapters")
            return capitulos

        except Exception as e:
            logger.error(f"[{self.name}] Error fetching chapters: {e}")
            return []

    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Parse chapter number from text.

        Args:
            texto: Chapter text (e.g., "Chapter 147 September 11, 2025")

        Returns:
            Chapter number as string (e.g., "147", "147.5")
        """
        # Remove common prefixes
        texto = re.sub(r"(chapter|ch\.?|cap\.?)[\s:]*", "", texto, flags=re.IGNORECASE)

        # Extract number (including decimals like 147.5)
        # Match the first number before the date
        match = re.search(r"^(\d+(?:\.\d+)?)", texto.strip())
        if match:
            return match.group(1)

        # Fallback: try to find any number
        match = re.search(r"(\d+(?:\.\d+)?)", texto)
        return match.group(1) if match else "0"

    def _parse_date(self, fecha_texto: str) -> datetime:
        """
        Parse date from text.

        Args:
            fecha_texto: Date text (e.g., "September 11, 2025")

        Returns:
            datetime object
        """
        if not fecha_texto:
            return datetime.now()

        # Try standard format: "September 11, 2025"
        try:
            return datetime.strptime(fecha_texto, "%B %d, %Y")
        except ValueError:
            pass

        # Try short month format: "Sep 11, 2025"
        try:
            return datetime.strptime(fecha_texto, "%b %d, %Y")
        except ValueError:
            pass

        # Handle relative dates
        fecha_lower = fecha_texto.lower()

        # "X days ago"
        if "days ago" in fecha_lower or "day ago" in fecha_lower:
            match = re.search(r"(\d+)\s+days?\s+ago", fecha_lower)
            if match:
                from datetime import timedelta
                days = int(match.group(1))
                return datetime.now() - timedelta(days=days)

        # "yesterday"
        if "yesterday" in fecha_lower:
            from datetime import timedelta
            return datetime.now() - timedelta(days=1)

        # "today"
        if "today" in fecha_lower:
            return datetime.now()

        # Default to now
        logger.debug(f"[{self.name}] Could not parse date '{fecha_texto}', using current time")
        return datetime.now()
