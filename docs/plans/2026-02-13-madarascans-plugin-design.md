# MadaraScans Scanlator Plugin Design

**Date:** 2026-02-13
**Status:** Design Approved - Ready for Implementation
**Goal:** Add MadaraScans scanlator plugin with complete chapter extraction using "Load More" button automation

---

## Problem Statement

The user needs to track manga chapters from MadaraScans (https://madarascans.com), a popular English/Spanish manga and manhwa scanlation site. The existing AsuraScans plugin provides a template, but MadaraScans has a different site structure requiring:

1. WordPress-based search functionality
2. Dynamic chapter loading via "Load More" button
3. Different HTML selectors for chapter extraction
4. Site-specific date and chapter number parsing

---

## Requirements

From user discussion:

1. **Immediate Use:** User has specific manga to track on MadaraScans
2. **Complete Chapter Extraction:** Must obtain ALL chapters, not just initially visible ones
3. **"Load More" Automation:** Click "Load More" button until all chapters are loaded
4. **Robust Parsing:** Handle chapter numbers and dates in various formats
5. **Search Support:** Implement manga search functionality for future manga additions
6. **Error Handling:** Graceful failures with proper logging

**Example Manga:** https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/

---

## Selected Approach: Complete Extraction with "Load More" Automation

**Why this approach:**
- Guarantees no chapters are missed (critical for tracking)
- Consistent with AsuraScans pattern (clicks "All" tab)
- Acceptable speed trade-off (runs in background jobs)
- User has immediate tracking needs requiring complete data

**How it works:**
1. Navigate to manga page
2. Wait for chapter list to appear
3. Loop: Click "Load More" button until it disappears
4. Extract all visible chapters in one pass
5. Parse and normalize chapter data
6. Return sorted list (oldest → newest)

**Rejected alternatives:**
- **Quick extraction (no Load More):** Risk missing chapters on manga with 50+ chapters
- **Hybrid with limit:** Arbitrary limit doesn't guarantee completeness

---

## Website Structure Analysis

### Search Functionality

**URL Pattern:**
```
https://madarascans.com/?s={query}
```

**Implementation:**
- WordPress standard search (`?s=` parameter)
- AJAX-enabled but direct URLs work fine
- Returns rendered page with search results

**Expected Selectors:**
- Manga links: `a[href*="/series/"]`
- Titles: From heading tags or link text
- Covers: `img` elements within manga cards

---

### Chapter Extraction

**Selectors (from WebFetch analysis):**
- **Chapter list container:** `#chapterlist ul`
- **Chapter items:** `#chapterlist ul li a`
- **Chapter title:** `.ch-name`
- **Chapter date:** `.ch-date`
- **Chapter URL:** `href` attribute of `<a>` tag
- **Load More button:** `.load-more-ch-btn`

**HTML Structure:**
```html
<div id="chapterlist">
  <ul>
    <li>
      <a href="/series/manga-name/chapter-1/">
        <div class="chapter-info-box">
          <span class="ch-name">Chapter 1</span>
          <span class="ch-date">2 days ago</span>
        </div>
      </a>
    </li>
    <!-- ... more chapters ... -->
  </ul>
</div>
<button class="load-more-ch-btn">Load More</button>
```

**Loading Behavior:**
- Clicking `.load-more-ch-btn` appends new `<li>` elements to the list
- Button disappears when all chapters are loaded
- 1-2 second delay needed for content to render

---

## Design Details

### 1. Plugin Class Structure

**File:** `/data/mangataro/scanlators/madara_scans.py`

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
```

**Key Design Decisions:**
- **Class name:** `MadaraScans` (matches database `class_name` requirement)
- **Display name:** "Madara Scans" (user-facing name)
- **Base URL:** `https://madarascans.com` (no trailing slash)

---

### 2. Search Implementation

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

**Key Features:**
- WordPress standard search (`?s=` parameter)
- Deduplication via `Set` (avoid duplicate URLs)
- Flexible title extraction (tries multiple selectors)
- Graceful error handling

---

### 3. Chapter Extraction with Load More Automation

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

**Key Features:**
- **Load More automation:** Clicks until button disappears
- **Safety limit:** Max 30 clicks to prevent infinite loops
- **Batch extraction:** Extracts all chapters after loading completes
- **Robust selectors:** Uses specific `#chapterlist` and `.ch-name`/`.ch-date` selectors
- **Error logging:** Tracks how many times Load More was clicked

---

### 4. Chapter Number Parsing

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

**Pattern:** Same as AsuraScans - remove prefixes, extract numeric part.

---

### 5. Date Parsing

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

**Pattern:** Identical to AsuraScans - handles relative and absolute dates.

---

## Data Flow

### Search Flow

1. User calls `buscar_manga("villain")`
2. Navigate to `https://madarascans.com/?s=villain`
3. Wait for `a[href*="/series/"]` elements
4. Extract manga cards with titles, URLs, covers
5. Deduplicate by URL
6. Return list of manga candidates

### Chapter Extraction Flow

1. User triggers tracking for manga
2. TrackerService calls `obtener_capitulos(manga_url)`
3. Navigate to manga page
4. Wait for `#chapterlist ul` to load
5. **Loop:** Click `.load-more-ch-btn` until invisible (max 30 times)
6. Extract all `#chapterlist ul li a` elements with `.ch-name`, `.ch-date`, `href`
7. Parse chapter numbers and dates
8. Sort chapters oldest → newest
9. Return list with Spanish field names: `numero`, `titulo`, `url`, `fecha`
10. TrackerService maps to English fields and saves to database

### Error Handling

- **Navigation fails:** `safe_goto()` returns `False`, method returns `[]`
- **Selectors not found:** Try-except catches, logs error, returns `[]`
- **Load More timeout:** Safety limit of 30 clicks prevents infinite loops
- **Parse failures:** Fallback to `"0"` for chapter numbers, `datetime.now()` for dates

---

## Components Affected

**New File:**
- `scanlators/madara_scans.py` - New plugin implementation

**Auto-Discovery:**
- `scanlators/__init__.py` - Automatically discovers `MadaraScans` class

**Database:**
- Add new scanlator entry via `scripts/add_scanlator.py` or API:
  ```sql
  INSERT INTO scanlators (name, class_name, base_url)
  VALUES ('Madara Scans', 'MadaraScans', 'https://madarascans.com');
  ```

**Testing:**
- Test search: `python scripts/test_madara_scans.py --search "villain"`
- Test chapters: `python scripts/test_madara_scans.py --url "https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/"`

**Integration:**
- Add manga-scanlator mappings via `scripts/add_manga_source.py`
- Run tracking via `python scripts/track_chapters.py --scanlator-id <id>`

---

## Edge Cases & Considerations

### Load More Button Behavior

**Problem:** Button might be hidden but still in DOM, or loading indicator might interfere.

**Solution:** Use `.is_visible()` check instead of just `.locator()`. If button exists but invisible, stop clicking.

### Empty Search Results

**Problem:** Search might return no results for typos or unavailable manga.

**Solution:** Return empty list `[]` gracefully. Frontend/user can retry with different search terms.

### Duplicate Chapters

**Problem:** DOM might have duplicate chapter entries after multiple Load More clicks.

**Solution:** Use Set for deduplication in JavaScript extraction if needed, but current implementation should avoid this.

### Very Large Chapter Lists (100+ chapters)

**Problem:** 30 click limit might not be enough for extremely long series.

**Solution:**
- Default limit of 30 should handle 300+ chapters (typical: 10 chapters per page)
- Can increase limit if needed
- Log warning if limit is reached

### Date Parsing Failures

**Problem:** Site might use unusual date formats not covered by parser.

**Solution:** Fallback to `datetime.now()` ensures tracking continues. Can investigate logs and add new formats if patterns emerge.

---

## Success Criteria

✅ Plugin class `MadaraScans` inherits from `BaseScanlator`
✅ Search functionality returns manga candidates with title, URL, cover
✅ Chapter extraction loads ALL chapters via "Load More" automation
✅ Chapter numbers are correctly parsed from various formats
✅ Dates are parsed from relative ("2 days ago") and absolute formats
✅ Chapters are sorted oldest → newest
✅ Spanish field names used in return values (`numero`, `titulo`, `url`, `fecha`)
✅ Robust error handling with logging
✅ Plugin auto-discovered by `scanlators/__init__.py`
✅ Can be tested with user's example manga URL

---

## Testing Plan

### Unit Testing (Manual)

**Search Test:**
```bash
# Create test script: scripts/test_madara_scans.py
python scripts/test_madara_scans.py --search "villain"

# Expected: Returns list of manga matching "villain"
# Verify: Titles, URLs, cover images are extracted
```

**Chapter Extraction Test:**
```bash
python scripts/test_madara_scans.py \
  --url "https://madarascans.com/series/i-became-the-villain-the-hero-is-obsessed-with/"

# Expected: Returns all chapters (10-50+)
# Verify:
# - Load More was clicked multiple times
# - Chapter numbers are correct (1, 2, 3, ...)
# - Dates are parsed
# - Sorted oldest → newest
```

**Load More Verification:**
- Run with `--visible` flag to watch browser
- Verify button clicks are happening
- Verify all chapters appear before extraction

### Integration Testing

**Add Scanlator to Database:**
```bash
# Via API or SQL
curl -X POST http://localhost:8008/api/scanlators \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Madara Scans",
    "class_name": "MadaraScans",
    "base_url": "https://madarascans.com"
  }'
```

**Add Manga-Scanlator Mapping:**
```bash
python scripts/add_manga_source.py
# Select manga, select MadaraScans, paste URL, verify
```

**Run Tracking:**
```bash
python scripts/track_chapters.py --scanlator-id <madara_id> --visible
# Verify chapters are discovered and saved to database
```

---

## Implementation Notes

**Code Patterns:**
- Follow AsuraScans structure closely (proven pattern)
- Use `safe_goto()` helper for navigation
- Use `asyncio.sleep()` for waiting (not `time.sleep()`)
- Log all major operations (search, load more clicks, extraction)
- Use descriptive variable names (`capitulos_raw`, `load_more_count`)

**Playwright Best Practices:**
- Use `locator()` for dynamic elements (Load More button)
- Use `evaluate()` for batch data extraction
- Use `wait_for_selector()` for initial page load
- Use `is_visible()` to check element state

**Error Handling:**
- Catch broad `Exception` at method level
- Log specific errors with context
- Return empty lists on failure (not None)
- Don't crash tracking job if one manga fails

**Logging Levels:**
- `INFO`: Major operations (searching, extracting, counts)
- `DEBUG`: Details (Load More clicks, selector waits)
- `WARNING`: Recoverable issues (parse failures, hit limits)
- `ERROR`: Failures (navigation failed, extraction failed)

---

## Next Steps

1. **Create implementation plan** using `writing-plans` skill
2. **Implement plugin** following the design above
3. **Create test script** for manual verification
4. **Add scanlator to database**
5. **Test with user's manga** URL
6. **Add manga-scanlator mappings**
7. **Run first tracking job**
8. **Verify chapters appear in web UI**

---

**Design Status:** ✅ Approved - Ready for Implementation Plan
