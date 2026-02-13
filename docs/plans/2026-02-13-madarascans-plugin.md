# MadaraScans Scanlator Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement MadaraScans scanlator plugin with complete chapter extraction using "Load More" button automation

**Architecture:** Follows BaseScanlator pattern from AsuraScans. WordPress search via `?s=` parameter, dynamic chapter loading with `.load-more-ch-btn` automation, JavaScript-based batch extraction with proper selectors.

**Tech Stack:** Python 3.11, Playwright (async), Loguru (logging), Regex (parsing)

---

## Task 1: Create MadaraScans Plugin Skeleton

**Files:**
- Create: `scanlators/madara_scans.py`

**Step 1: Create plugin file with class structure**

```python
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
        # TODO: Implement in next task
        pass

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
```

**Step 2: Verify plugin is discoverable**

Run: `python -c "from scanlators import get_scanlator_by_name; print(get_scanlator_by_name('MadaraScans'))"`

Expected: Should print `<class 'scanlators.madara_scans.MadaraScans'>` (plugin auto-discovered)

**Step 3: Commit skeleton**

```bash
git add scanlators/madara_scans.py
git commit -m "feat(scanlators): add MadaraScans plugin skeleton

Add basic plugin structure with abstract method stubs.
Plugin auto-discovered via class name.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Implement Search Functionality

**Files:**
- Modify: `scanlators/madara_scans.py` (buscar_manga method)

**Step 1: Implement buscar_manga method**

Replace the `buscar_manga` method with:

```python
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
```

**Step 2: Commit search implementation**

```bash
git add scanlators/madara_scans.py
git commit -m "feat(scanlators): implement MadaraScans search

Add WordPress search via ?s= parameter with deduplication.
Flexible title extraction from multiple selectors.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Implement Chapter Number Parsing

**Files:**
- Modify: `scanlators/madara_scans.py` (parsear_numero_capitulo method)

**Step 1: Implement parsear_numero_capitulo method**

Replace the `parsear_numero_capitulo` method with:

```python
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
    texto_lower = texto.lower()

    # Remove common prefixes
    texto_clean = re.sub(
        r'^(chapter|ch\.?|episode|ep\.?|cap\.?|capítulo)\s*',
        '',
        texto_lower,
        flags=re.IGNORECASE
    )

    # Extract first number (including decimals)
    match = re.search(r'(\d+(?:\.\d+)?)', texto_clean)
    if match:
        return match.group(1)

    # Fallback
    logger.warning(f"[{self.name}] Could not parse chapter number from: {texto}")
    return "0"
```

**Step 2: Commit chapter parsing**

```bash
git add scanlators/madara_scans.py
git commit -m "feat(scanlators): implement MadaraScans chapter number parsing

Parse chapter numbers from various formats with prefix removal.
Supports decimals (42.5) and fallback to '0'.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Implement Date Parsing

**Files:**
- Modify: `scanlators/madara_scans.py` (_parse_date method)

**Step 1: Implement _parse_date method**

Replace the `_parse_date` method with:

```python
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
    if not fecha_texto:
        return datetime.now()

    fecha_texto = fecha_texto.strip().lower()

    try:
        # Handle relative dates: "X days ago"
        if "ago" in fecha_texto:
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

        # Handle "yesterday" and "today"
        if "yesterday" in fecha_texto:
            return datetime.now() - timedelta(days=1)
        if "today" in fecha_texto:
            return datetime.now()

        # Try standard date formats
        date_formats = [
            "%b %d, %Y",    # Jan 15, 2026
            "%B %d, %Y",    # January 15, 2026
            "%Y-%m-%d",     # 2026-01-15
            "%d/%m/%Y",     # 15/01/2026
            "%m/%d/%Y",     # 01/15/2026
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
```

**Step 2: Commit date parsing**

```bash
git add scanlators/madara_scans.py
git commit -m "feat(scanlators): implement MadaraScans date parsing

Parse relative ('2 days ago') and absolute date formats.
Fallback to datetime.now() ensures tracking continues.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Implement Chapter Extraction with Load More

**Files:**
- Modify: `scanlators/madara_scans.py` (obtener_capitulos method)

**Step 1: Implement obtener_capitulos method**

Replace the `obtener_capitulos` method with:

```python
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
    logger.info(f"[{self.name}] Extracting chapters from: {manga_url}")

    if not await self.safe_goto(manga_url):
        logger.error(f"[{self.name}] Failed to load manga page")
        return []

    try:
        # Wait for chapter list to appear
        await self.page.wait_for_selector("#chapterlist ul", timeout=10000)

        # Click "Load More" until all chapters are loaded
        load_more_count = 0
        max_clicks = 30  # Safety limit to prevent infinite loops

        while load_more_count < max_clicks:
            load_more_btn = self.page.locator(".load-more-ch-btn")

            # Check if button exists and is visible
            if not await load_more_btn.is_visible():
                logger.debug(f"[{self.name}] No more chapters to load (clicked {load_more_count} times)")
                break

            # Click button and wait for new content
            await load_more_btn.click()
            await asyncio.sleep(1.5)  # Wait for content to load
            load_more_count += 1
            logger.debug(f"[{self.name}] Clicked 'Load More' ({load_more_count})")

        if load_more_count >= max_clicks:
            logger.warning(f"[{self.name}] Reached max Load More clicks ({max_clicks})")

        # Extract all chapters in one pass
        capitulos_raw = await self.page.evaluate("""
            () => {
                const items = document.querySelectorAll('#chapterlist ul li a');
                const chapters = [];

                for (const item of items) {
                    const texto = item.querySelector('.ch-name')?.textContent.trim() || '';
                    const url = item.href;
                    const fecha_texto = item.querySelector('.ch-date')?.textContent.trim() || '';

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
            numero = self.parsear_numero_capitulo(cap["texto"])
            fecha = self._parse_date(cap.get("fecha_texto", ""))

            capitulos.append({
                "numero": numero,
                "titulo": cap["texto"],
                "url": cap["url"],
                "fecha": fecha
            })

        # Sort chapters from oldest to newest
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
```

**Step 2: Commit chapter extraction**

```bash
git add scanlators/madara_scans.py
git commit -m "feat(scanlators): implement MadaraScans chapter extraction

Add complete chapter extraction with 'Load More' automation.
Safety limit of 30 clicks, batch extraction after loading.
Returns sorted chapters with Spanish field names.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Create Test Script

**Files:**
- Create: `scripts/test_madara_scans.py`

**Step 1: Create test script**

```python
#!/usr/bin/env python3
"""
Test script for MadaraScans scanlator plugin.

Usage:
    # Test search
    python scripts/test_madara_scans.py --search "villain"

    # Test chapter extraction
    python scripts/test_madara_scans.py --url "https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/"

    # Test with visible browser
    python scripts/test_madara_scans.py --url "https://madarascans.com/series/..." --visible
"""

import argparse
import asyncio
from playwright.async_api import async_playwright
from loguru import logger

from scanlators import get_scanlator_by_name


async def test_search(query: str, headless: bool = True):
    """Test MadaraScans search functionality."""
    logger.info(f"Testing search for: {query}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()

        # Get plugin class and instantiate
        plugin_class = get_scanlator_by_name("MadaraScans")
        if not plugin_class:
            logger.error("MadaraScans plugin not found!")
            await browser.close()
            return

        plugin = plugin_class(page)

        # Test search
        results = await plugin.buscar_manga(query)

        logger.info(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. {result['titulo']}")
            logger.info(f"     URL: {result['url']}")
            logger.info(f"     Cover: {result['portada'][:80]}...")

        await browser.close()


async def test_chapters(manga_url: str, headless: bool = True):
    """Test MadaraScans chapter extraction."""
    logger.info(f"Testing chapter extraction for: {manga_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()

        # Get plugin class and instantiate
        plugin_class = get_scanlator_by_name("MadaraScans")
        if not plugin_class:
            logger.error("MadaraScans plugin not found!")
            await browser.close()
            return

        plugin = plugin_class(page)

        # Test chapter extraction
        chapters = await plugin.obtener_capitulos(manga_url)

        logger.info(f"Extracted {len(chapters)} chapters:")
        for i, chapter in enumerate(chapters[:10], 1):  # Show first 10
            logger.info(f"  {i}. Chapter {chapter['numero']}: {chapter['titulo']}")
            logger.info(f"     URL: {chapter['url']}")
            logger.info(f"     Date: {chapter['fecha']}")

        if len(chapters) > 10:
            logger.info(f"  ... and {len(chapters) - 10} more chapters")

        await browser.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test MadaraScans plugin")
    parser.add_argument("--search", type=str, help="Search for manga by title")
    parser.add_argument("--url", type=str, help="Extract chapters from manga URL")
    parser.add_argument("--visible", action="store_true", help="Show browser (not headless)")

    args = parser.parse_args()

    if args.search:
        asyncio.run(test_search(args.search, headless=not args.visible))
    elif args.url:
        asyncio.run(test_chapters(args.url, headless=not args.visible))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 2: Make script executable**

Run: `chmod +x scripts/test_madara_scans.py`

Expected: Script is now executable

**Step 3: Commit test script**

```bash
git add scripts/test_madara_scans.py
git commit -m "test(scanlators): add MadaraScans test script

Add manual test script for search and chapter extraction.
Supports --visible flag for debugging.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Manual Testing - Search

**Files:**
- None (manual testing)

**Step 1: Test search functionality**

Run: `python scripts/test_madara_scans.py --search "villain"`

Expected output:
```
[INFO] Testing search for: villain
[INFO] [Madara Scans] Searching for: villain
[INFO] [Madara Scans] Navigating to: https://madarascans.com/?s=villain
[INFO] [Madara Scans] Successfully loaded https://madarascans.com/?s=villain
[INFO] [Madara Scans] Found X results for 'villain'
[INFO] Found X results:
  1. I Became the Villain the Hero Is Obsessed With
     URL: https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/
     Cover: https://...
```

**Step 2: Verify results**

- Check that manga titles are extracted correctly
- Check that URLs point to `/series/` pages
- Check that cover images are valid URLs

---

## Task 8: Manual Testing - Chapter Extraction

**Files:**
- None (manual testing)

**Step 1: Test chapter extraction (headless)**

Run:
```bash
python scripts/test_madara_scans.py \
  --url "https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/"
```

Expected output:
```
[INFO] Testing chapter extraction for: https://madarascans.com/series/...
[INFO] [Madara Scans] Extracting chapters from: https://madarascans.com/series/...
[DEBUG] [Madara Scans] Clicked 'Load More' (1)
[DEBUG] [Madara Scans] Clicked 'Load More' (2)
...
[DEBUG] [Madara Scans] No more chapters to load (clicked X times)
[INFO] [Madara Scans] Extracted XX chapters
[INFO] Extracted XX chapters:
  1. Chapter 1: ...
     URL: https://...
     Date: 2026-XX-XX ...
```

**Step 2: Verify chapter extraction**

- Check that all chapters are extracted (compare with website)
- Check that "Load More" was clicked multiple times
- Check that chapters are sorted oldest → newest (Chapter 1 first)
- Check that chapter numbers are parsed correctly

**Step 3: Test with visible browser (optional)**

Run:
```bash
python scripts/test_madara_scans.py \
  --url "https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/" \
  --visible
```

Watch the browser:
- Verify that "Load More" button is being clicked
- Verify that chapter list grows after each click
- Verify that extraction happens after all chapters load

---

## Task 9: Add Scanlator to Database

**Files:**
- None (database operation)

**Step 1: Add MadaraScans scanlator to database**

Run:
```bash
curl -X POST http://localhost:8008/api/scanlators \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Madara Scans",
    "class_name": "MadaraScans",
    "base_url": "https://madarascans.com"
  }'
```

Expected response:
```json
{
  "id": 8,
  "name": "Madara Scans",
  "class_name": "MadaraScans",
  "base_url": "https://madarascans.com"
}
```

**Step 2: Verify scanlator was added**

Run: `curl http://localhost:8008/api/scanlators/`

Expected: Should include MadaraScans in the list

**Step 3: Note the scanlator ID**

Save the ID (e.g., `8`) for next task

---

## Task 10: Add Manga-Scanlator Mapping

**Files:**
- None (database operation)

**Step 1: Run add_manga_source.py script**

Run: `python scripts/add_manga_source.py`

Interactive prompts:
1. Select manga (search or browse)
2. Select scanlator: Choose "Madara Scans"
3. Enter URL: `https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/`
4. Manually verified: `y` (yes)

Expected output:
```
✓ Manga-scanlator mapping added successfully!
  ID: XX
  Manga: I Became the Villain the Hero Is Obsessed With
  Scanlator: Madara Scans
  URL: https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/
  Verified: Yes
```

**Step 2: Verify mapping in database**

Run:
```bash
curl http://localhost:8008/api/tracking/manga-scanlators | jq '.[] | select(.scanlator.class_name == "MadaraScans")'
```

Expected: Should show the newly created mapping

---

## Task 11: Integration Test - Run Tracking

**Files:**
- None (integration test)

**Step 1: Run tracking for MadaraScans**

Run:
```bash
python scripts/track_chapters.py --scanlator-id 8 --visible
```

(Replace `8` with actual scanlator ID from Task 9)

Expected output:
```
[INFO] Starting chapter tracking...
[INFO] Found 1 verified manga-scanlator mappings to track
[INFO] Processing: I Became the Villain the Hero Is Obsessed With (Madara Scans)
[DEBUG] [Madara Scans] Extracting chapters from: https://madarascans.com/series/...
[DEBUG] [Madara Scans] Clicked 'Load More' (1)
...
[INFO] [Madara Scans] Extracted XX chapters
[INFO] Found XX new chapters for: I Became the Villain the Hero Is Obsessed With
[INFO] Saving chapters to database...
[SUCCESS] Tracking completed! XX new chapters discovered
```

**Step 2: Verify chapters in database**

Run:
```bash
mysql -u mangataro_user -p mangataro -e "
SELECT COUNT(*) as chapter_count
FROM chapters c
JOIN manga_scanlator ms ON c.manga_scanlator_id = ms.id
JOIN scanlators s ON ms.scanlator_id = s.id
WHERE s.class_name = 'MadaraScans';
"
```

Expected: Should show the number of chapters inserted

**Step 3: Verify chapters in web UI**

- Open browser: `http://localhost:4343`
- Check Updates page - should show new chapters from MadaraScans
- Click on manga - should show all chapters

---

## Task 12: Final Verification and Documentation

**Files:**
- Modify: `README.md` or `docs/USER_GUIDE.md` (optional)

**Step 1: Verify all success criteria**

Check:
- ✅ Plugin class `MadaraScans` inherits from `BaseScanlator`
- ✅ Search functionality returns manga candidates
- ✅ Chapter extraction loads ALL chapters via "Load More"
- ✅ Chapter numbers parsed correctly
- ✅ Dates parsed from relative/absolute formats
- ✅ Chapters sorted oldest → newest
- ✅ Spanish field names used (`numero`, `titulo`, `url`, `fecha`)
- ✅ Robust error handling with logging
- ✅ Plugin auto-discovered
- ✅ Works with user's example manga URL

**Step 2: Run final end-to-end test**

Run:
```bash
# Trigger tracking via API
curl -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"notify": false}'
```

Check web UI for new chapters

**Step 3: Document MadaraScans addition (optional)**

Add to `docs/USER_GUIDE.md` or README:
- MadaraScans is now supported
- Example manga URL format
- How to add new manga from MadaraScans

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(scanlators): complete MadaraScans plugin implementation

MadaraScans plugin is now fully functional with:
- WordPress search support
- Complete chapter extraction with 'Load More' automation
- Robust parsing for chapter numbers and dates
- Integration tested with real manga

Resolves user request for MadaraScans support.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Success Criteria Checklist

After completing all tasks, verify:

- [ ] Plugin file created at `scanlators/madara_scans.py`
- [ ] Plugin inherits from `BaseScanlator`
- [ ] Search functionality works (tested with "villain")
- [ ] Chapter extraction works (tested with user's manga URL)
- [ ] "Load More" automation clicks until all chapters loaded
- [ ] Chapter numbers parsed correctly from various formats
- [ ] Dates parsed from relative and absolute formats
- [ ] Chapters sorted oldest → newest
- [ ] Spanish field names used in return values
- [ ] Plugin auto-discovered by `scanlators/__init__.py`
- [ ] Test script created and functional
- [ ] Scanlator added to database
- [ ] Manga-scanlator mapping created
- [ ] Tracking job completes successfully
- [ ] Chapters appear in web UI
- [ ] All commits made with descriptive messages

---

## Troubleshooting

**Issue: Plugin not found by get_scanlator_by_name**

Solution:
- Verify class name is exactly `MadaraScans`
- Restart Python to reload module
- Check `scanlators/__init__.py` auto-discovery logic

**Issue: "Load More" button not found**

Solution:
- Visit URL in browser manually to verify button exists
- Check if selector `.load-more-ch-btn` is correct
- Increase timeout in `wait_for_selector`
- Use `--visible` flag to debug

**Issue: Chapter extraction returns empty list**

Solution:
- Check selectors: `#chapterlist ul li a`, `.ch-name`, `.ch-date`
- Verify manga URL is correct format
- Check logs for specific error messages
- Test with different manga URL

**Issue: Chapters not appearing in web UI**

Solution:
- Verify manga-scanlator mapping has `manually_verified = 1`
- Check database for inserted chapters
- Refresh web UI (hard refresh: Ctrl+Shift+R)
- Check API: `curl http://localhost:8008/api/manga/{id}/updates`

---

## Implementation Notes

**Time Estimate:** 45-60 minutes for full implementation and testing

**Dependencies:**
- API server must be running (`uvicorn api.main:app`)
- Database must be accessible
- Playwright must be installed (`playwright install chromium`)

**Testing Strategy:**
- Manual testing with real website (no mocks)
- Test search with multiple queries
- Test chapter extraction with user's manga URL
- Integration test with full tracking workflow

**Commit Strategy:**
- Commit after each major feature (search, parsing, extraction)
- Descriptive commit messages with context
- Co-authored commits to acknowledge collaboration

---

**Plan Status:** ✅ Ready for Implementation
