"""
AsuraScans scanlator plugin.

Plugin for AsuraScans (asuracomic.net) - Popular English manga/manhwa scanlation site.
Known for translating Korean manhwa and Chinese manhua.
"""

import re
from datetime import datetime, timedelta
from playwright.async_api import Page
from loguru import logger

from scanlators.base import BaseScanlator


class AsuraScans(BaseScanlator):
    """
    Plugin for AsuraScans (asuracomic.net).

    AsuraScans is a popular scanlation group known for high-quality
    translations of Korean manhwa and Chinese manhua.
    """

    def __init__(self, playwright_page: Page):
        """Initialize the AsuraScans scanlator plugin."""
        super().__init__(playwright_page)

        self.name = "Asura Scans"
        self.base_url = "https://asuracomic.net"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search for manga by title on AsuraScans.

        Args:
            titulo: The manga title to search for

        Returns:
            List of manga results with titulo, url, and portada
        """
        logger.info(f"[{self.name}] Searching for: {titulo}")

        # AsuraScans search URL pattern
        search_url = f"{self.base_url}/series?name={titulo}"

        # Navigate to search page
        if not await self.safe_goto(search_url):
            logger.error(f"[{self.name}] Failed to load search page")
            return []

        try:
            # Wait for search results to load
            # AsuraScans uses a grid layout for manga listings
            await self.page.wait_for_selector(".grid", timeout=10000)

            # Wait a bit more for dynamic content
            import asyncio
            await asyncio.sleep(2)

            # Extract search results using JavaScript evaluation
            # AsuraScans uses grid with direct anchor tags containing series info
            resultados = await self.page.evaluate("""
                () => {
                    // Find the main grid containing search results (usually the 3rd grid)
                    const grids = document.querySelectorAll('.grid');
                    let searchGrid = null;

                    // Look for grid with manga links (contains 'series/' in href)
                    for (const grid of grids) {
                        const seriesLinks = grid.querySelectorAll('a[href*="series/"]');
                        if (seriesLinks.length > 0) {
                            searchGrid = grid;
                            break;
                        }
                    }

                    if (!searchGrid) {
                        return [];
                    }

                    // Extract all series links from the grid
                    const items = searchGrid.querySelectorAll('a[href*="series/"]');
                    return Array.from(items).map(item => {
                        // Get the title from h3 or span element
                        // Try to find the main title, skipping genre tags like "MANHWA", "MANGA", etc.
                        const titleElements = item.querySelectorAll('h3, span[class*="font"], span[class*="text"]');
                        let titulo = '';

                        for (const el of titleElements) {
                            const text = el.textContent.trim();
                            // Skip common genre tags
                            if (text && !['MANHWA', 'MANGA', 'MANHUA', 'WEBTOON'].includes(text.toUpperCase()) && text.length > 2) {
                                titulo = text;
                                break;
                            }
                        }

                        // Fallback: get from link's direct text or any span
                        if (!titulo) {
                            const spans = item.querySelectorAll('span');
                            for (const span of spans) {
                                const text = span.textContent.trim();
                                if (text && text.length > 3 && text.length < 100 && !['MANHWA', 'MANGA', 'MANHUA'].includes(text.toUpperCase())) {
                                    titulo = text;
                                    break;
                                }
                            }
                        }

                        // Get the URL (make it absolute)
                        let url = item.href;
                        if (url && !url.startsWith('http')) {
                            url = window.location.origin + '/' + url.replace(/^\//, '');
                        }

                        // Get cover image
                        const imgElement = item.querySelector('img');
                        const portada = imgElement ? (imgElement.src || imgElement.dataset.src || imgElement.getAttribute('src') || '') : '';

                        // Only return if we have at least a title and URL
                        if (titulo && url && url.includes('series/')) {
                            return { titulo, url, portada };
                        }
                        return null;
                    }).filter(item => item !== null);
                }
            """)

            logger.info(f"[{self.name}] Found {len(resultados)} results for '{titulo}'")
            return resultados

        except Exception as e:
            logger.error(f"[{self.name}] Error searching for manga: {e}")
            return []

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Extract chapters from a manga page on AsuraScans.

        Args:
            manga_url: Full URL to the manga's page

        Returns:
            List of chapters with numero, titulo, url, and fecha
        """
        logger.info(f"[{self.name}] Extracting chapters from: {manga_url}")

        # Navigate to manga page
        if not await self.safe_goto(manga_url):
            logger.error(f"[{self.name}] Failed to load manga page")
            return []

        try:
            # Wait for chapter list to load
            await self.page.wait_for_selector('a[href*="/chapter"]', timeout=10000)

            # Click on "All" tab to show all chapters (not just weekly/monthly)
            try:
                # Look for tab with text "All"
                all_tab = self.page.locator('[role="tab"]:has-text("All"), button:has-text("All")').first
                if await all_tab.count() > 0:
                    logger.debug(f"[{self.name}] Clicking 'All' tab to show all chapters")
                    await all_tab.click()
                    # Wait a bit for chapters to load
                    import asyncio
                    await asyncio.sleep(2)
            except Exception as e:
                logger.debug(f"[{self.name}] Could not find/click 'All' tab: {e}")

            # Extract chapters using JavaScript
            capitulos_raw = await self.page.evaluate("""
                () => {
                    // Get all chapter links
                    const chapterLinks = document.querySelectorAll('a[href*="/chapter"]');

                    // Use a Set to track unique chapters (avoid duplicates)
                    const seen = new Set();
                    const chapters = [];

                    for (const link of chapterLinks) {
                        const url = link.href;

                        // Skip duplicates
                        if (seen.has(url)) continue;
                        seen.add(url);

                        // Get chapter title from h3 or text content
                        const titleElement = link.querySelector('h3, span[class*="text"]');
                        let texto = titleElement ? titleElement.textContent.trim() : link.textContent.trim();

                        // Clean up text (remove extra whitespace)
                        texto = texto.replace(/\\s+/g, ' ').trim();

                        // Try to find date information
                        // Look for date patterns in the link
                        let fecha_texto = '';
                        const allText = link.textContent;
                        const dateMatch = allText.match(/(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2}(?:st|nd|rd|th)?\\s+\\d{4}|\\d+\\s+(?:second|minute|hour|day|week|month|year)s?\\s+ago/i);
                        if (dateMatch) {
                            fecha_texto = dateMatch[0];
                        }

                        if (texto && url) {
                            chapters.push({ texto, url, fecha_texto });
                        }
                    }

                    return chapters;
                }
            """)

            # Process and normalize chapters
            capitulos = []
            for cap in capitulos_raw:
                # Parse chapter number
                numero = self.parsear_numero_capitulo(cap["texto"])

                # Parse date
                fecha = self._parse_date(cap.get("fecha_texto", ""))

                capitulos.append({
                    "numero": numero,
                    "titulo": cap["texto"],
                    "url": cap["url"],
                    "fecha": fecha
                })

            # Sort chapters from oldest to newest
            # Use numeric sorting for chapter numbers when possible
            def sort_key(x):
                try:
                    return (float(x["numero"]), x["fecha"])
                except ValueError:
                    return (0, x["fecha"])

            capitulos.sort(key=sort_key)

            logger.info(f"[{self.name}] Extracted {len(capitulos)} chapters")
            return capitulos

        except Exception as e:
            logger.error(f"[{self.name}] Error extracting chapters: {e}")
            return []

    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Parse chapter number from text.

        Handles various formats used by AsuraScans:
        - "Chapter 42"
        - "Ch. 42.5"
        - "Episode 100"
        - "Chapter 42: Title Here"
        - "First Chapter" -> "1"

        Args:
            texto: Raw text containing the chapter number

        Returns:
            Normalized chapter number as string (e.g., "42", "42.5")
        """
        # Handle special cases
        texto_lower = texto.lower()

        # Handle "First Chapter" -> "1"
        if "first" in texto_lower:
            return "1"

        # Remove common prefixes like "Chapter", "Ch.", "Episode", "Ep.", etc.
        texto_clean = re.sub(
            r'^(chapter|ch\.?|episode|ep\.?|cap\.?|capítulo)\s*',
            '',
            texto_lower,
            flags=re.IGNORECASE
        )

        # Extract first number (including decimals)
        # Matches patterns like: 42, 42.5, 123, etc.
        match = re.search(r'(\d+(?:\.\d+)?)', texto_clean)
        if match:
            return match.group(1)

        # Fallback: if no number found, return "0"
        logger.warning(f"[{self.name}] Could not parse chapter number from: {texto}")
        return "0"

    def _parse_date(self, fecha_texto: str) -> datetime:
        """
        Parse date from various formats used by AsuraScans.

        Handles formats like:
        - "2 days ago"
        - "1 week ago"
        - "Jan 15, 2026"
        - "2026-01-15"
        - "Yesterday"

        Args:
            fecha_texto: Raw date text

        Returns:
            datetime object (defaults to now if parsing fails)
        """
        if not fecha_texto:
            return datetime.now()

        fecha_texto = fecha_texto.strip().lower()

        try:
            # Handle relative dates: "X days ago", "X weeks ago", etc.
            if "ago" in fecha_texto:
                # Match patterns like "2 days ago", "1 week ago"
                match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', fecha_texto)
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2)

                    if unit == "second":
                        return datetime.now() - timedelta(seconds=amount)
                    elif unit == "minute":
                        return datetime.now() - timedelta(minutes=amount)
                    elif unit == "hour":
                        return datetime.now() - timedelta(hours=amount)
                    elif unit == "day":
                        return datetime.now() - timedelta(days=amount)
                    elif unit == "week":
                        return datetime.now() - timedelta(weeks=amount)
                    elif unit == "month":
                        return datetime.now() - timedelta(days=amount * 30)
                    elif unit == "year":
                        return datetime.now() - timedelta(days=amount * 365)

            # Handle "yesterday"
            if "yesterday" in fecha_texto:
                return datetime.now() - timedelta(days=1)

            # Handle "today"
            if "today" in fecha_texto:
                return datetime.now()

            # Try standard date formats
            date_formats = [
                "%b %d, %Y",        # Jan 15, 2026
                "%B %d, %Y",        # January 15, 2026
                "%Y-%m-%d",         # 2026-01-15
                "%d/%m/%Y",         # 15/01/2026
                "%m/%d/%Y",         # 01/15/2026
            ]

            for fmt in date_formats:
                try:
                    return datetime.strptime(fecha_texto, fmt)
                except ValueError:
                    continue

        except Exception as e:
            logger.debug(f"[{self.name}] Error parsing date '{fecha_texto}': {e}")

        # Fallback to current datetime
        return datetime.now()
