"""
MangaDex scanlator plugin.

Uses the MangaDex public REST API (api.mangadex.org) — no browser scraping needed.
Fetches English-language chapters from all scanlation groups.
"""

import re
import asyncio
from datetime import datetime, timezone
from playwright.async_api import Page
import httpx
from loguru import logger

from scanlators.base import BaseScanlator


class MangaDex(BaseScanlator):
    """
    Plugin for MangaDex (mangadex.org).

    Uses the MangaDex public REST API. The playwright_page argument is accepted
    for interface compatibility but is never used — all calls go through httpx.
    """

    API_BASE = "https://api.mangadex.org"
    CHAPTERS_LIMIT = 100  # Max per request (MangaDex API limit for non-feed endpoints)

    def __init__(self, playwright_page: Page):
        super().__init__(playwright_page)
        self.name = "MangaDex"
        self.base_url = "https://mangadex.org"

    def _extract_uuid(self, manga_url: str) -> str:
        """
        Extract the manga UUID from a MangaDex URL.

        URL format: https://mangadex.org/title/{uuid}/optional-slug
        """
        match = re.search(r'/title/([0-9a-f-]{36})', manga_url)
        if not match:
            raise ValueError(f"Could not extract UUID from URL: {manga_url}")
        return match.group(1)

    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Parse chapter number from text.

        MangaDex already returns clean numbers (e.g. "42", "42.5").
        This handles edge cases and strips whitespace.
        """
        texto = texto.strip()
        # If it's already a clean number, return it
        if re.match(r'^\d+(\.\d+)?$', texto):
            return texto
        # Otherwise extract the first number
        match = re.search(r'(\d+(?:\.\d+)?)', texto)
        if match:
            return match.group(1)
        logger.warning(f"[{self.name}] Could not parse chapter number from: {texto}")
        return "0"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search MangaDex for manga by title.

        Returns list of {titulo, url, portada}.
        """
        logger.info(f"[{self.name}] Searching for: {titulo}")
        params = {
            "title": titulo,
            "availableTranslatedLanguage[]": "en",
            "limit": 10,
            "includes[]": "cover_art",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{self.API_BASE}/manga", params=params)
                response.raise_for_status()
                data = response.json()

            results = []
            for manga in data.get("data", []):
                manga_id = manga["id"]
                attrs = manga["attributes"]

                # Get title (prefer English)
                title = (
                    attrs.get("title", {}).get("en")
                    or next(iter(attrs.get("title", {}).values()), "Unknown")
                )

                # Get cover image from relationships
                portada = ""
                for rel in manga.get("relationships", []):
                    if rel["type"] == "cover_art":
                        filename = rel.get("attributes", {}).get("fileName", "")
                        if filename:
                            portada = f"https://uploads.mangadex.org/covers/{manga_id}/{filename}"
                        break

                results.append({
                    "titulo": title,
                    "url": f"https://mangadex.org/title/{manga_id}",
                    "portada": portada,
                })

            logger.info(f"[{self.name}] Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[{self.name}] Error searching manga: {e}")
            return []

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Fetch all English chapters for a manga from MangaDex.

        Args:
            manga_url: MangaDex manga URL (e.g. https://mangadex.org/title/{uuid}/...)

        Returns:
            List of chapters sorted oldest → newest.
        """
        logger.info(f"[{self.name}] Fetching chapters from: {manga_url}")

        try:
            manga_uuid = self._extract_uuid(manga_url)
        except ValueError as e:
            logger.error(f"[{self.name}] {e}")
            return []

        all_chapters = []
        offset = 0

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                while True:
                    params = {
                        "manga": manga_uuid,
                        "translatedLanguage[]": "en",
                        "order[chapter]": "asc",
                        "limit": self.CHAPTERS_LIMIT,
                        "offset": offset,
                    }
                    response = await client.get(f"{self.API_BASE}/chapter", params=params)
                    response.raise_for_status()
                    data = response.json()

                    chapters = data.get("data", [])
                    total = data.get("total", 0)
                    all_chapters.extend(chapters)

                    logger.debug(f"[{self.name}] Fetched {len(all_chapters)}/{total} chapters")

                    # Paginate if needed
                    offset += len(chapters)
                    if offset >= total or not chapters:
                        break

                    await asyncio.sleep(0.5)  # Courtesy delay between paginated requests

        except Exception as e:
            logger.error(f"[{self.name}] Error fetching chapters: {e}")
            if all_chapters:
                logger.warning(f"[{self.name}] Returning {len(all_chapters)} partial results due to error")
            else:
                return []

        # Map to plugin format
        capitulos = []
        for ch in all_chapters:
            attrs = ch["attributes"]
            numero_raw = attrs.get("chapter") or "0"
            numero = self.parsear_numero_capitulo(numero_raw)
            titulo = attrs.get("title") or ""
            chapter_url = f"https://mangadex.org/chapter/{ch['id']}"

            # Parse ISO 8601 date from publishAt
            publish_at = attrs.get("publishAt", "")
            try:
                fecha = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
                # Convert to naive UTC for consistency with other plugins
                fecha = fecha.replace(tzinfo=None)
            except (ValueError, AttributeError):
                fecha = datetime.now(timezone.utc).replace(tzinfo=None)

            capitulos.append({
                "numero": numero,
                "titulo": titulo,
                "url": chapter_url,
                "fecha": fecha,
            })

        logger.info(f"[{self.name}] Extracted {len(capitulos)} chapters")
        return capitulos
