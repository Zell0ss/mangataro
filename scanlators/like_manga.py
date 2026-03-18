"""
LikeManga scanlator plugin.
Website: https://likemanga.ink/
"""

import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from playwright.async_api import Page
from scanlators.base import BaseScanlator
from loguru import logger


class LikeManga(BaseScanlator):
    """Scanlator plugin for LikeManga (likemanga.ink)."""

    def __init__(self, playwright_page: Page):
        super().__init__(playwright_page)
        self.name = "LikeManga"
        self.base_url = "https://likemanga.ink"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search for manga on LikeManga.

        Search URL: /?act=search&f[status]=all&f[sortby]=lastest-chap&f[keyword]={titulo}
        Results rendered in HTML — no AJAX needed.

        Returns:
            List of dicts with titulo, url, portada
        """
        search_url = f"{self.base_url}/?act=search&f[status]=all&f[sortby]=lastest-chap&f[keyword]={quote_plus(titulo)}"
        logger.info(f"[{self.name}] Searching: {search_url}")

        try:
            if not await self.safe_goto(search_url):
                return []

            resultados = []
            items = await self.page.locator(".card.card-manga, .item-manga, .manga-item").all()

            if not items:
                # Fallback: links matching /{slug}-{4+digits}/ (manga detail pages)
                # e.g. /solo-leveling-ragnarok-28849/  — NOT chapter sub-paths
                links = await self.page.locator("a").all()
                seen: set[str] = set()
                for link in links:
                    href = await link.get_attribute("href") or ""
                    if not re.search(r"/[a-z0-9-]+-\d{4,}/$", href):
                        continue
                    if "chapter" in href or href in seen:
                        continue
                    titulo_text = (await link.text_content() or "").strip()
                    if not titulo_text:
                        continue
                    seen.add(href)
                    url = href if href.startswith("http") else self.base_url + href
                    img = link.locator("img")
                    portada = await img.first.get_attribute("src") if await img.count() > 0 else ""
                    if portada and not portada.startswith("http"):
                        portada = self.base_url + "/" + portada.lstrip("/")
                    resultados.append({"titulo": titulo_text, "url": url, "portada": portada or ""})
                logger.info(f"[{self.name}] Found {len(resultados)} results (fallback)")
                return resultados

            for item in items:
                try:
                    link = item.locator("a").first
                    href = await link.get_attribute("href") or ""
                    url = href if href.startswith("http") else self.base_url + href
                    titulo_text = (await item.locator("p.title-manga, .card-title, a").first.text_content() or "").strip()
                    img = item.locator("img")
                    portada = await img.first.get_attribute("src") if await img.count() > 0 else ""
                    if portada and not portada.startswith("http"):
                        portada = self.base_url + "/" + portada.lstrip("/")
                    if url and titulo_text:
                        resultados.append({"titulo": titulo_text, "url": url, "portada": portada or ""})
                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing search item: {e}")

            logger.info(f"[{self.name}] Found {len(resultados)} results")
            return resultados

        except Exception as e:
            logger.error(f"[{self.name}] Search error: {e}")
            return []

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Get all chapters from a manga page.

        Chapter links are in the static HTML — no AJAX needed.
        URL pattern: /{slug}-{id}/chapter-{num}-{chapter_id}/
        Date class: .chapter-release-date  text: "January 7, 2026"

        Returns:
            List of dicts with numero, titulo, url, fecha
        """
        logger.info(f"[{self.name}] Fetching chapters from: {manga_url}")

        try:
            if not await self.safe_goto(manga_url):
                return []

            # Structure: <li class="wp-manga-chapter">
            #              <a href="/{slug}/chapter-N-{id}/">Chapter N</a>
            #              <span class="chapter-release-date"><i>January 7, 2026</i></span>
            #            </li>
            items = await self.page.locator("li.wp-manga-chapter").all()
            logger.debug(f"[{self.name}] Chapter items found: {len(items)}")

            capitulos = []
            seen_numeros: set[str] = set()

            for item in items:
                try:
                    link = item.locator("a").first
                    href = await link.get_attribute("href") or ""
                    if not href or "chapter" not in href:
                        continue

                    url = href if href.startswith("http") else self.base_url + href
                    texto = (await link.text_content() or "").strip()

                    numero = self.parsear_numero_capitulo(texto)
                    if numero in seen_numeros:
                        continue
                    seen_numeros.add(numero)

                    date_span = item.locator(".chapter-release-date")
                    fecha_texto = (await date_span.text_content() or "").strip() if await date_span.count() > 0 else ""
                    fecha = self._parse_date(fecha_texto) if fecha_texto else datetime.now()

                    capitulos.append({
                        "numero": numero,
                        "titulo": texto,
                        "url": url,
                        "fecha": fecha,
                    })

                except Exception as e:
                    logger.debug(f"[{self.name}] Error parsing chapter item: {e}")

            capitulos.sort(key=lambda x: float(x["numero"]) if x["numero"].replace(".", "", 1).isdigit() else 0)

            logger.info(f"[{self.name}] Found {len(capitulos)} chapters")
            return capitulos

        except Exception as e:
            logger.error(f"[{self.name}] Error fetching chapters: {e}")
            return []

    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Parse chapter number from text or URL fragment.

        Examples:
            "Chapter 68" → "68"
            "Chapter 0"  → "0"
            "Ch. 12.5"   → "12.5"
        """
        clean = re.sub(r"(chapter|ch\.?|cap\.?)[\s:]*", "", texto, flags=re.IGNORECASE).strip()
        match = re.search(r"^(\d+(?:\.\d+)?)", clean)
        if match:
            return match.group(1)
        match = re.search(r"(\d+(?:\.\d+)?)", texto)
        return match.group(1) if match else "0"

    def _parse_date(self, fecha_texto: str) -> datetime:
        """
        Parse date from LikeManga text: "January 7, 2026" or relative formats.
        """
        if not fecha_texto:
            return datetime.now()

        for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(fecha_texto, fmt)
            except ValueError:
                pass

        lower = fecha_texto.lower()
        match = re.search(r"(\d+)\s+days?\s+ago", lower)
        if match:
            return datetime.now() - timedelta(days=int(match.group(1)))
        if "yesterday" in lower:
            return datetime.now() - timedelta(days=1)
        if "today" in lower or "just now" in lower:
            return datetime.now()

        logger.debug(f"[{self.name}] Could not parse date '{fecha_texto}', using now")
        return datetime.now()
