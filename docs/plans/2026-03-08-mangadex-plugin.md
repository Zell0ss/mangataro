# MangaDex Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a `MangaDex` scanlator plugin that fetches chapters via the MangaDex public REST API (no Playwright scraping required).

**Architecture:** The plugin inherits from `BaseScanlator` (accepting a `playwright_page` for interface compliance but never using it) and uses `httpx.AsyncClient` for all API calls. It extracts manga UUIDs from MangaDex URLs and queries `api.mangadex.org` for English-language chapters.

**Tech Stack:** Python, httpx (already installed), MangaDex REST API (`api.mangadex.org`), loguru

---

## Context: How MangaDex URLs Work

- Manga page URL: `https://mangadex.org/title/32d76d19-8a05-4db0-9fc2-e0b0648fe9d0/manga-slug`
  - UUID is the path segment **immediately after `/title/`**
- Chapter URL: `https://mangadex.org/chapter/{chapter-uuid}`
- Cover image: `https://uploads.mangadex.org/covers/{manga-uuid}/{filename}`

## Context: MangaDex API Endpoints

```
GET https://api.mangadex.org/manga
  ?title={query}
  &availableTranslatedLanguage[]=en
  &limit=10
  &includes[]=cover_art
  → Returns manga list with cover_art in relationships[]

GET https://api.mangadex.org/chapter
  ?manga={uuid}
  &translatedLanguage[]=en
  &order[chapter]=asc
  &limit=500
  &offset=0
  → Returns chapters. `total` field tells you if pagination needed.
    Each chapter: attributes.chapter (number), attributes.title, attributes.publishAt
```

## Context: Key Files

- `scanlators/base.py` — Abstract base class. Constructor requires `playwright_page: Page`.
- `scanlators/madara_scans.py` — Reference plugin implementation.
- `scanlators/__init__.py` — Auto-discovery (finds any `BaseScanlator` subclass by class name).
- `scripts/test_madara_scans.py` — Reference test script.
- `requirements.txt` — No changes needed (httpx already installed).

---

## Task 1: Create the plugin file

**Files:**
- Create: `scanlators/manga_dex.py`

**Step 1: Create the plugin with `parsear_numero_capitulo` and skeleton methods**

```python
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
    CHAPTERS_LIMIT = 500  # Max per request

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
                fecha = datetime.utcnow()

            capitulos.append({
                "numero": numero,
                "titulo": titulo,
                "url": chapter_url,
                "fecha": fecha,
            })

        logger.info(f"[{self.name}] Extracted {len(capitulos)} chapters")
        return capitulos
```

**Step 2: Verify the plugin is auto-discovered**

```bash
cd /data/mangataro
source .venv/bin/activate
python3 -c "
from scanlators import get_scanlator_classes
classes = get_scanlator_classes()
print('Discovered:', list(classes.keys()))
assert 'MangaDex' in classes, 'MangaDex not found!'
print('Auto-discovery OK')
"
```

Expected output: `Discovered: ['AsuraScans', 'MadaraScans', 'MangaDex']` (order may vary), `Auto-discovery OK`

**Step 3: Commit**

```bash
git add scanlators/manga_dex.py
git commit -m "feat: add MangaDex scanlator plugin"
```

---

## Task 2: Create the test script

**Files:**
- Create: `scripts/test_manga_dex.py`

**Step 1: Write the test script**

```python
#!/usr/bin/env python3
"""
Test script for MangaDex scanlator plugin.

Tests all three main methods using the live MangaDex API.
No browser required.

Usage:
    python scripts/test_manga_dex.py
    python scripts/test_manga_dex.py --search "bromance book club"
    python scripts/test_manga_dex.py --manga-url "https://mangadex.org/title/UUID/slug"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from loguru import logger
from scanlators.manga_dex import MangaDex

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


async def test_parsear_numero_capitulo(scanlator: MangaDex):
    logger.info("=" * 60)
    logger.info("TEST: parsear_numero_capitulo")
    logger.info("=" * 60)
    cases = [
        ("42", "42"),
        ("42.5", "42.5"),
        ("1", "1"),
        ("100", "100"),
        ("  7  ", "7"),
        ("Chapter 5", "5"),
    ]
    all_passed = True
    for text, expected in cases:
        result = scanlator.parsear_numero_capitulo(text)
        passed = result == expected
        if passed:
            logger.success(f"  PASS: '{text}' -> '{result}'")
        else:
            logger.error(f"  FAIL: '{text}' -> '{result}' (expected '{expected}')")
            all_passed = False
    return all_passed


async def test_buscar_manga(scanlator: MangaDex, search_term: str):
    logger.info("=" * 60)
    logger.info(f"TEST: buscar_manga('{search_term}')")
    logger.info("=" * 60)
    results = await scanlator.buscar_manga(search_term)
    if not results:
        logger.warning("No results found")
        return []
    logger.success(f"Found {len(results)} results:")
    for r in results[:5]:
        logger.info(f"  Title: {r['titulo']}")
        logger.info(f"  URL:   {r['url']}")
        logger.info(f"  Cover: {r['portada'][:80]}")
        logger.info("")
    return results


async def test_obtener_capitulos(scanlator: MangaDex, manga_url: str):
    logger.info("=" * 60)
    logger.info(f"TEST: obtener_capitulos")
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
    parser.add_argument("--search", default="bromance book club")
    parser.add_argument("--manga-url")
    args = parser.parse_args()

    async with async_playwright() as p:
        # MangaDex plugin doesn't use Playwright, but interface requires a page
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        scanlator = MangaDex(page)
        logger.success(f"Initialized: {scanlator}")

        try:
            # Test 1: parsear_numero_capitulo (no network)
            await test_parsear_numero_capitulo(scanlator)

            # Test 2: buscar_manga
            results = await test_buscar_manga(scanlator, args.search)

            # Test 3: obtener_capitulos
            manga_url = args.manga_url or (results[0]["url"] if results else None)
            if manga_url:
                await test_obtener_capitulos(scanlator, manga_url)
            else:
                logger.warning("No manga URL available for chapter test")

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
python scripts/test_manga_dex.py --search "bromance book club"
```

Expected output:
- `parsear_numero_capitulo`: all PASS
- `buscar_manga`: 1-10 results with titles/URLs/covers
- `obtener_capitulos`: N chapters with chapter numbers, dates, URLs

**Step 3: Commit**

```bash
git add scripts/test_manga_dex.py
git commit -m "test: add MangaDex plugin test script"
```

---

## Task 3: Add the scanlator to the database

**Step 1: Run the DB insert**

```bash
mysql -u mangataro_user -p mangataro -e "
INSERT INTO scanlators (name, class_name, base_url)
VALUES ('MangaDex', 'MangaDex', 'https://mangadex.org');
SELECT id, name, class_name, base_url FROM scanlators ORDER BY id;
"
```

Expected: New row appears with `name=MangaDex`, `class_name=MangaDex`.

Note the `id` — you'll need it when mapping manga.

**Step 2: Verify the tracker service can find the plugin**

```bash
cd /data/mangataro
source .venv/bin/activate
python3 -c "
from scanlators import get_scanlator_by_name
cls = get_scanlator_by_name('MangaDex')
print('Plugin class:', cls)
assert cls is not None, 'Plugin not found!'
print('Plugin lookup OK')
"
```

Expected: `Plugin class: <class 'scanlators.manga_dex.MangaDex'>`, `Plugin lookup OK`

---

## Task 4: Map manga via the admin UI

**Step 1: Open the map-sources admin page**

Visit: `http://localhost:4343/admin/map-sources?scanlator=<MangaDex-id>`

Replace `<MangaDex-id>` with the ID from the DB insert in Task 3.

**Step 2: For each manga you want to track, enter its MangaDex URL**

Format: `https://mangadex.org/title/{uuid}/optional-slug`

To find the URL for "Bromance Book Club", search MangaDex:
```bash
python3 -c "
import urllib.request, json
url = 'https://api.mangadex.org/manga?title=bromance+book+club&availableTranslatedLanguage[]=en&limit=5'
with urllib.request.urlopen(url, timeout=15) as r:
    data = json.loads(r.read())
for m in data['data']:
    title = m['attributes']['title'].get('en', list(m['attributes']['title'].values())[0])
    print(f'https://mangadex.org/title/{m[\"id\"]}  —  {title}')
"
```

**Step 3: Verify the mapping in the DB**

```bash
mysql -u mangataro_user -p mangataro -e "
SELECT ms.id, m.titulo, s.name, ms.scanlator_manga_url, ms.manually_verified
FROM manga_scanlator ms
JOIN mangas m ON ms.manga_id = m.id
JOIN scanlators s ON ms.scanlator_id = s.id
WHERE s.class_name = 'MangaDex'
ORDER BY ms.id DESC LIMIT 10;
"
```

---

## Task 5: Run a tracking job to verify end-to-end

**Step 1: Trigger tracking for one manga**

Find a `manga_scanlator` ID for a MangaDex mapping from the query above. Then:

```bash
cd /data/mangataro
source .venv/bin/activate
python3 -c "
import asyncio, sys
sys.path.insert(0, '.')

async def main():
    from api.database import SessionLocal
    from api import models
    from api.services.tracker_service import get_tracker_service

    db = SessionLocal()
    service = get_tracker_service()

    # Get one MangaDex manga_scanlator record
    ms = db.query(models.MangaScanlator).join(models.Scanlator).filter(
        models.Scanlator.class_name == 'MangaDex',
        models.MangaScanlator.manually_verified == True
    ).first()

    if not ms:
        print('No verified MangaDex mappings found')
        return

    print(f'Testing manga: {ms.manga.titulo}')
    print(f'URL: {ms.scanlator_manga_url}')

    result = await service.track_single_manga_scanlator(ms, db, notify=False)
    print(f'Result: {result}')
    db.close()

asyncio.run(main())
"
```

Expected: chapters inserted (or 0 new if already up to date). No errors.

**Step 2: Verify chapters in DB**

```bash
mysql -u mangataro_user -p mangataro -e "
SELECT c.chapter_number, c.title, c.url, c.release_date, c.detected_date
FROM chapters c
JOIN manga_scanlator ms ON c.manga_scanlator_id = ms.id
JOIN scanlators s ON ms.scanlator_id = s.id
WHERE s.class_name = 'MangaDex'
ORDER BY c.detected_date DESC LIMIT 10;
"
```

**Step 3: Check the web UI**

Visit `http://localhost:4343` — new chapters should appear in the updates feed.

---

## Notes

- **No `requirements.txt` changes** — `httpx` is already installed.
- **No API or frontend changes** — the plugin slots into the existing architecture.
- **Pagination:** The API returns max 500 chapters per request. The plugin handles this automatically with a 0.5s delay between pages.
- **External chapters:** Some MangaDex chapters link to Webnovel/other platforms (`externalUrl`). The chapter URL still points to `mangadex.org/chapter/{id}`, which redirects to the external site. This is intentional and correct.
- **Timezone:** `publishAt` is ISO 8601 with timezone. We strip timezone info for DB consistency with other plugins.
