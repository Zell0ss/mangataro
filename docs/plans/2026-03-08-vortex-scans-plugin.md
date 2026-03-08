# VortexScans Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `VortexScans` scanlator plugin that searches manga and fetches chapters from vortexscans.org using their public REST API.

**Architecture:** VortexScans exposes a public REST API at `api.vortexscans.org` (not behind Cloudflare). `buscar_manga` uses httpx directly against this API. `obtener_capitulos` requires Playwright to load the manga page (passes Cloudflare), intercepts the outgoing `/api/chapters?postId=...` network request to extract the internal post ID, then uses httpx to paginate all chapters from the API.

**Tech Stack:** Python, httpx (already installed), Playwright (existing), loguru (existing), FastAPI/SQLAlchemy (DB insert only)

---

## Context: Plugin Architecture

Plugins live in `scanlators/`. Auto-discovery finds all `BaseScanlator` subclasses by class name. See `scanlators/base.py` for the abstract interface and `scanlators/manga_dex.py` for a reference plugin that also uses httpx.

**CRITICAL:** Always use `scanlator.class_name` (not `scanlator.name`) for plugin lookup. The DB `class_name` field must match the Python class name exactly — `VortexScans`.

```python
# Plugin interface (all three methods required)
class VortexScans(BaseScanlator):
    def __init__(self, playwright_page: Page): ...
    async def buscar_manga(self, titulo: str) -> list[dict]: ...      # [{titulo, url, portada}]
    async def obtener_capitulos(self, manga_url: str) -> list[dict]:  # [{numero, titulo, url, fecha}]
    def parsear_numero_capitulo(self, texto: str) -> str: ...
```

## Context: API Facts (discovered by live testing)

**Search API** (httpx, no Cloudflare):
```
GET https://api.vortexscans.org/api/posts?search={titulo}
→ { "posts": [{id, slug, postTitle, featuredImage, ...}], "totalCount": N }
```
- Returns up to 10 posts; search is fuzzy
- `slug` is used to build the manga URL: `https://vortexscans.org/series/{slug}`
- `featuredImage` is a full URL or empty string

**Chapters API** (httpx, no Cloudflare — but needs postId):
```
GET https://api.vortexscans.org/api/chapters?postId={id}&take=100&skip={offset}
→ {
    "post": {
      "chapters": [{id, slug, number, title, mangaPostId, createdAt, isLocked, mangaPost: {slug}}]
    },
    "totalChapterCount": N
  }
```
- `take` controls page size (max observed: 100); `skip` is the offset
- `chapter.slug` is like `"chapter-233"` or `"chapter-1-8mi19zhy"`
- Chapter URL = `https://vortexscans.org/series/{manga_slug}/{chapter.slug}`
- `chapter.createdAt` is ISO 8601: `"2026-03-06T16:21:57.846Z"`
- `chapter.number` is already a clean integer (233, 232, ...)
- Some chapters are locked (`isLocked: true`) — include them anyway (tracker records their existence)

**Getting postId:**
When Playwright loads `https://vortexscans.org/series/{slug}`, the page makes a request to `api.vortexscans.org/api/chapters?postId={id}`. Intercept this outgoing request to extract the postId.

---

## Task 1: Implement the VortexScans plugin

**Files:**
- Create: `scanlators/vortex_scans.py`

**Step 1: Create the plugin file**

Create `/data/mangataro/scanlators/vortex_scans.py` with the full implementation:

```python
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
        """
        Parse chapter number from text.

        VortexScans API returns clean integers (233, 232, ...).
        This handles edge cases and strips whitespace.

        Examples:
            "233" → "233"
            "42.5" → "42.5"
            "Chapter 5" → "5"
        """
        texto = str(texto).strip()
        # If it's already a clean number, return it
        if re.match(r'^\d+(\.\d+)?$', texto):
            return texto
        # Extract first number (e.g. from "Chapter 42")
        match = re.search(r'(\d+(?:\.\d+)?)', texto)
        if match:
            return match.group(1)
        logger.warning(f"[{self.name}] Could not parse chapter number from: {texto!r}")
        return "0"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search VortexScans for manga by title using the public REST API.

        Args:
            titulo: The manga title to search for

        Returns:
            List of {titulo, url, portada} dicts.
        """
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
                    "titulo": p["postTitle"],
                    "url": f"https://vortexscans.org/series/{p['slug']}",
                    "portada": p.get("featuredImage") or "",
                }
                for p in posts
            ]
            logger.info(f"[{self.name}] Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[{self.name}] Error searching manga: {e}")
            return []

    def _extract_slug(self, manga_url: str) -> str:
        """
        Extract the series slug from a VortexScans manga URL.

        URL format: https://vortexscans.org/series/{slug}
        """
        match = re.search(r'/series/([^/?#]+)', manga_url)
        if not match:
            raise ValueError(f"Could not extract slug from URL: {manga_url}")
        return match.group(1)

    async def _get_post_id(self, manga_url: str) -> int | None:
        """
        Load the manga page with Playwright and intercept the outgoing
        /api/chapters?postId=... request to extract the internal post ID.

        Returns the postId integer, or None if not found.
        """
        post_id = None

        def handle_request(request):
            nonlocal post_id
            if 'api.vortexscans.org/api/chapters' in request.url and 'postId=' in request.url:
                m = re.search(r'postId=(\d+)', request.url)
                if m:
                    post_id = int(m.group(1))

        self.page.on("request", handle_request)
        try:
            await self.safe_goto(manga_url, timeout=30000)
            # Wait for the page's JavaScript to make the API call (up to 10s)
            for _ in range(20):
                if post_id is not None:
                    break
                await asyncio.sleep(0.5)
        finally:
            self.page.remove_listener("request", handle_request)

        return post_id

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Fetch all chapters for a manga from VortexScans.

        Uses Playwright to load the manga page (passes Cloudflare) and extract
        the internal postId, then paginates the chapter API with httpx.

        Args:
            manga_url: VortexScans manga URL (https://vortexscans.org/series/{slug})

        Returns:
            List of chapters sorted oldest → newest.
        """
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

        # Paginate all chapters via httpx
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

                    page_chapters = data["post"]["chapters"]
                    total = data["totalChapterCount"]
                    all_chapters.extend(page_chapters)

                    logger.debug(f"[{self.name}] Fetched {len(all_chapters)}/{total} chapters")

                    if len(page_chapters) < CHAPTERS_TAKE:
                        break
                    skip += CHAPTERS_TAKE

        except Exception as e:
            logger.error(f"[{self.name}] Error fetching chapters: {e}")
            if all_chapters:
                logger.warning(f"[{self.name}] Returning {len(all_chapters)} partial results")
            else:
                return []

        # Map to plugin format
        capitulos = []
        for ch in all_chapters:
            numero = self.parsear_numero_capitulo(ch["number"])
            titulo = ch.get("title") or ""
            chapter_url = f"https://vortexscans.org/series/{manga_slug}/{ch['slug']}"

            # Parse ISO 8601 date from createdAt
            created_at = ch.get("createdAt", "")
            try:
                fecha = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                fecha = fecha.replace(tzinfo=None)  # naive UTC, consistent with other plugins
            except (ValueError, AttributeError):
                fecha = datetime.now(timezone.utc).replace(tzinfo=None)

            capitulos.append({
                "numero": numero,
                "titulo": titulo,
                "url": chapter_url,
                "fecha": fecha,
            })

        # Sort oldest → newest
        def sort_key(c):
            try:
                return (float(c["numero"]), c["fecha"])
            except (ValueError, TypeError):
                return (0.0, c["fecha"])

        capitulos.sort(key=sort_key)

        logger.info(f"[{self.name}] Extracted {len(capitulos)} chapters")
        return capitulos
```

**Step 2: Verify the plugin is discovered**

```bash
cd /data/mangataro
source .venv/bin/activate
python3 -c "
from scanlators import get_scanlator_by_name
cls = get_scanlator_by_name('VortexScans')
print('Found:', cls)
assert cls is not None, 'Plugin not found!'
print('OK')
"
```

Expected output:
```
Found: <class 'scanlators.vortex_scans.VortexScans'>
OK
```

**Step 3: Commit**

```bash
git add scanlators/vortex_scans.py
git commit -m "feat: add VortexScans scanlator plugin"
```

---

## Task 2: Create the test script and verify live

**Files:**
- Create: `scripts/test_vortex_scans.py`

**Step 1: Create the test script**

Create `/data/mangataro/scripts/test_vortex_scans.py`:

```python
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
```

**Step 2: Run the test script**

```bash
cd /data/mangataro
source .venv/bin/activate
python scripts/test_vortex_scans.py
```

Expected output:
```
HH:MM:SS | SUCCESS  | Initialized: <VortexScans(name='VortexScans', base_url='https://vortexscans.org')>
HH:MM:SS | INFO     | TEST: parsear_numero_capitulo
HH:MM:SS | INFO       PASS: '233' -> '233'
... (all 5 cases passing)
HH:MM:SS | INFO     | TEST: buscar_manga('rankers return')
HH:MM:SS | SUCCESS  | Found N results:
...
HH:MM:SS | INFO     | TEST: obtener_capitulos
HH:MM:SS | SUCCESS  | Found N chapters
HH:MM:SS | INFO     | First 3: ...
HH:MM:SS | SUCCESS  | Done!
```

If `buscar_manga` finds 0 results (search is fuzzy), that's acceptable — try `--search "steel emperor"` as a fallback.

If `obtener_capitulos` fails to detect postId, wait an extra 5 seconds may be needed — increase the `for _ in range(20)` loop to 40 in the plugin.

**Step 3: Commit**

```bash
git add scripts/test_vortex_scans.py
git commit -m "feat: add VortexScans test script"
```

---

## Task 3: Register in database and verify tracking

**Step 1: Insert the scanlator record**

```bash
cd /data/mangataro
source .venv/bin/activate
python3 -c "
from api.database import SessionLocal
from api import models

db = SessionLocal()
existing = db.query(models.Scanlator).filter_by(class_name='VortexScans').first()
if existing:
    print(f'Already exists: ID={existing.id}')
else:
    s = models.Scanlator(name='VortexScans', class_name='VortexScans', base_url='https://vortexscans.org')
    db.add(s)
    db.commit()
    db.refresh(s)
    print(f'Inserted: ID={s.id}')
db.close()
"
```

Expected:
```
Inserted: ID=35
```
(or shows existing ID if already inserted)

**Step 2: Verify via API**

```bash
curl -s "http://localhost:8008/api/scanlators/" | python3 -m json.tool | grep -A3 '"VortexScans"'
```

Expected: shows a scanlator entry with `class_name: "VortexScans"`.

**Step 3: Verify plugin appears in search endpoint**

Restart the API first:
```bash
sudo systemctl restart mangataro.service
sleep 3
```

Then test the cross-scanlator search to confirm VortexScans participates:
```bash
curl -s "http://localhost:8008/api/search/?q=solo" | python3 -m json.tool | grep -A2 '"scanlator"'
```

Expected: list includes a `"scanlator": "VortexScans"` entry.

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: register VortexScans in database"
```

---

## Notes

- **Search quality:** The VortexScans search API is fuzzy and does not guarantee title-matching results. Users should verify results by visiting the URL before mapping.
- **Cloudflare on manga pages:** The site's HTML pages are Cloudflare-protected but Playwright handles this. The REST API is not protected.
- **Locked chapters:** `isLocked: true` chapters (coin-gated early access) are included. The tracker records their existence even if the reader cannot access them.
- **postId detection timing:** The `_get_post_id` method polls for up to 10 seconds (20 × 0.5s). Slow connections may need this increased.
- **Chapter slugs:** May include a hash suffix (e.g. `chapter-1-8mi19zhy`) or just the number (`chapter-233`). Use the API's `slug` field directly for URLs.
