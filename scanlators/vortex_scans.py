"""
VortexScans scanlator plugin.

Uses the VortexScans public REST API (api.vortexscans.org) for search and chapter data.
The manga detail pages are behind Cloudflare, so Playwright is used only to load the
manga page and extract the internal postId. All chapter data is fetched via httpx.
"""

import re
import asyncio
from datetime import datetime, timezone
from playwright.async_api import Page
import httpx
from loguru import logger

from scanlators.base import BaseScanlator

CHAPTERS_TAKE = 100  # Max chapters per API request


class VortexScans(BaseScanlator):
    """
    Plugin for VortexScans (vortexscans.org).

    buscar_manga: httpx → api.vortexscans.org/api/posts?search=...
    obtener_capitulos: Playwright (for postId) + httpx (for all chapters)
    """

    API_BASE = "https://api.vortexscans.org"

    def __init__(self, playwright_page: Page):
        super().__init__(playwright_page)
        self.name = "VortexScans"
        self.base_url = "https://vortexscans.org"

    def parsear_numero_capitulo(self, texto: str) -> str:
        """Parse chapter number from text. VortexScans API returns clean integers."""
        texto = str(texto).strip()
        if re.match(r'^\d+(\.\d+)?$', texto):
            return texto
        match = re.search(r'(\d+(?:\.\d+)?)', texto)
        if match:
            return match.group(1)
        logger.warning(f"[{self.name}] Could not parse chapter number from: {texto!r}")
        return "0"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """Search VortexScans for manga by title using the public REST API. Returns list of {titulo, url, portada}."""
        logger.info(f"[{self.name}] Searching for: {titulo!r}")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.API_BASE}/api/posts",
                    params={"search": titulo},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                response.raise_for_status()
                data = response.json()

            posts = data.get("posts", [])
            results = [
                {
                    "titulo": p.get("postTitle", ""),
                    "url": f"https://vortexscans.org/series/{p['slug']}",
                    "portada": p.get("featuredImage") or "",
                }
                for p in posts
                if p.get("slug")  # skip malformed entries with no slug
            ]
            logger.info(f"[{self.name}] Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[{self.name}] Error searching manga: {e}")
            return []

    def _extract_slug(self, manga_url: str) -> str:
        match = re.search(r'/series/([^/?#]+)', manga_url)
        if not match:
            raise ValueError(f"Could not extract slug from URL: {manga_url}")
        return match.group(1)

    async def _get_post_id(self, manga_url: str) -> int | None:
        post_id = None

        def handle_request(request):
            nonlocal post_id
            if 'api.vortexscans.org/api/' in request.url and 'postId=' in request.url:
                m = re.search(r'postId=(\d+)', request.url)
                if m:
                    post_id = int(m.group(1))
            elif 'api.vortexscans.org/api/' in request.url and 'targetId=' in request.url:
                m = re.search(r'targetId=(\d+)', request.url)
                if m:
                    post_id = int(m.group(1))

        self.page.on("request", handle_request)
        try:
            if not await self.safe_goto(manga_url, timeout=45000):
                logger.error(f"[{self.name}] Failed to load manga page: {manga_url}")
                return None
            # JS fires API requests ~5s after domcontentloaded; poll for up to 20s
            for _ in range(40):
                if post_id is not None:
                    break
                await asyncio.sleep(0.5)
        finally:
            self.page.remove_listener("request", handle_request)

        return post_id

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """Fetch all chapters for a manga from VortexScans. Uses Playwright to extract postId, then paginates via httpx."""
        logger.info(f"[{self.name}] Fetching chapters from: {manga_url}")

        try:
            manga_slug = self._extract_slug(manga_url)
        except ValueError as e:
            logger.error(f"[{self.name}] {e}")
            return []

        post_id = await self._get_post_id(manga_url)
        if post_id is None:
            logger.error(f"[{self.name}] Could not determine postId for {manga_url}")
            return []

        logger.debug(f"[{self.name}] postId={post_id}, slug={manga_slug!r}")

        all_chapters = []
        skip = 0
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                while True:
                    response = await client.get(
                        f"{self.API_BASE}/api/chapters",
                        params={"postId": post_id, "take": CHAPTERS_TAKE, "skip": skip},
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    response.raise_for_status()
                    data = response.json()

                    page_chapters = data.get("post", {}).get("chapters", [])
                    total = data.get("totalChapterCount", 0)
                    all_chapters.extend(page_chapters)

                    logger.debug(f"[{self.name}] Fetched {len(all_chapters)}/{total} chapters")

                    if not page_chapters or len(page_chapters) < CHAPTERS_TAKE:
                        break
                    skip += CHAPTERS_TAKE

        except Exception as e:
            logger.error(f"[{self.name}] Error fetching chapters: {e}")
            if all_chapters:
                logger.warning(f"[{self.name}] Returning {len(all_chapters)} partial results")
            else:
                return []

        capitulos = []
        for ch in all_chapters:
            number_raw = ch.get("number", 0)
            numero = self.parsear_numero_capitulo(number_raw)
            titulo = ch.get("title") or ""
            chapter_slug = ch.get("slug", "")
            if not chapter_slug:
                logger.warning(f"[{self.name}] Chapter {number_raw} has no slug, skipping")
                continue
            chapter_url = f"https://vortexscans.org/series/{manga_slug}/{chapter_slug}"

            created_at = ch.get("createdAt", "")
            try:
                fecha = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                fecha = fecha.replace(tzinfo=None)
            except (ValueError, AttributeError):
                fecha = datetime.now(timezone.utc).replace(tzinfo=None)

            capitulos.append({
                "numero": numero,
                "titulo": titulo,
                "url": chapter_url,
                "fecha": fecha,
            })

        def sort_key(c):
            try:
                return (float(c["numero"]), c["fecha"])
            except (ValueError, TypeError):
                return (0.0, c["fecha"])

        capitulos.sort(key=sort_key)

        logger.info(f"[{self.name}] Extracted {len(capitulos)} chapters")
        return capitulos
