# Cross-Scanlator Search Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/search` page that queries all registered scanlator plugins in parallel and shows results grouped by scanlator.

**Architecture:** A new FastAPI router (`/api/search`) launches one Playwright browser with one page per Playwright-based scraper, runs all `buscar_manga()` calls concurrently via `asyncio.gather`, then returns a combined JSON response. A new Astro page renders the search form and results client-side via Alpine.js. MangaDex uses httpx (no browser needed) but shares a page object for interface compliance.

**Tech Stack:** FastAPI, asyncio, Playwright (existing), httpx (existing), Astro, Alpine.js, TailwindCSS

---

## Context: Plugin Architecture

Scanlator plugins live in `scanlators/`. The auto-discovery system finds all `BaseScanlator` subclasses by class name. Each plugin is registered in the `scanlators` DB table with a `class_name` field that must match the Python class name exactly.

```python
# Correct pattern for plugin instantiation
from scanlators import get_scanlator_by_name
plugin_class = get_scanlator_by_name(scanlator.class_name)  # use class_name, NOT name
plugin = plugin_class(page)
chapters = await plugin.buscar_manga("solo leveling")
# Returns: [{"titulo": "...", "url": "...", "portada": "..."}, ...]
```

**CRITICAL:** Always use `scanlator.class_name` for plugin lookup, never `scanlator.name`. See `CLAUDE.md` section 3.

Playwright-based plugins (AsuraScans, RavenScans, MadaraScans) require a real browser page. MangaDex uses httpx internally and ignores its page argument.

## Context: Key Files

- `api/main.py` — Register new router here (lines 45-48 pattern)
- `api/routers/scanlators.py` — Reference router style
- `scanlators/__init__.py` — `get_scanlator_by_name()`, `get_scanlator_classes()`
- `frontend/src/components/Navigation.astro` — Add "Search" nav link to `links` array (line 7)
- `frontend/src/pages/index.astro` — Reference for Alpine.js + `window.__API_BASE` pattern
- `frontend/src/layouts/Layout.astro` — Base layout (uses `Navigation.astro`)

---

## Task 1: Create the search API endpoint

**Files:**
- Create: `api/routers/search.py`
- Modify: `api/main.py`

**Step 1: Write the router file**

Create `/data/mangataro/api/routers/search.py`:

```python
"""
Cross-scanlator search endpoint.

Queries all registered scanlator plugins in parallel and returns
combined results grouped by scanlator.
"""

import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright
from loguru import logger

from api.dependencies import get_db
from api import models
from scanlators import get_scanlator_by_name

router = APIRouter()

SEARCH_TIMEOUT = 30.0  # seconds per scanlator


async def _search_one(plugin_class, page, query: str, scanlator_name: str) -> dict:
    """
    Run buscar_manga for one scanlator and return a result dict.
    Never raises — errors are captured in the 'error' field.
    """
    try:
        plugin = plugin_class(page)
        matches = await asyncio.wait_for(
            plugin.buscar_manga(query),
            timeout=SEARCH_TIMEOUT
        )
        return {"scanlator": scanlator_name, "matches": matches or [], "error": None}
    except asyncio.TimeoutError:
        logger.warning(f"[search] Timeout searching {scanlator_name}")
        return {"scanlator": scanlator_name, "matches": [], "error": "Timeout"}
    except Exception as e:
        logger.error(f"[search] Error searching {scanlator_name}: {e}")
        return {"scanlator": scanlator_name, "matches": [], "error": str(e)}


@router.get("/")
async def search_manga(
    q: str = Query(..., min_length=2, description="Title keywords to search"),
    db: Session = Depends(get_db)
):
    """
    Search for manga across all registered scanlators simultaneously.

    Returns results grouped by scanlator. Every registered scanlator
    appears in the response — with empty matches if nothing found,
    or an error string if the plugin failed.
    """
    logger.info(f"[search] Searching for: {q!r}")

    # Get all active scanlators that have an implemented plugin
    scanlators = db.query(models.Scanlator).filter(
        models.Scanlator.active == True
    ).order_by(models.Scanlator.name).all()

    # Filter to only those with an available plugin class
    searchable = []
    for s in scanlators:
        plugin_class = get_scanlator_by_name(s.class_name)
        if plugin_class:
            searchable.append((s, plugin_class))
        else:
            logger.debug(f"[search] Skipping {s.name} — no plugin class found")

    if not searchable:
        return {"query": q, "results": []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])

        # Create one page per scanlator (shared browser, lower resource use)
        pages = [await browser.new_page() for _ in searchable]

        tasks = [
            _search_one(plugin_class, pages[i], q, s.name)
            for i, (s, plugin_class) in enumerate(searchable)
        ]

        results = await asyncio.gather(*tasks)

        # Clean up pages and browser
        for page in pages:
            await page.close()
        await browser.close()

    logger.info(f"[search] Done. {sum(len(r['matches']) for r in results)} total matches across {len(results)} scanlators")
    return {"query": q, "results": list(results)}
```

**Step 2: Register the router in `api/main.py`**

Add after the existing `app.include_router` lines (around line 48):

```python
from api.routers import manga, scanlators, tracking, search   # add search here
```

And add:
```python
app.include_router(search.router, prefix="/api/search", tags=["search"])
```

**Step 3: Verify the endpoint works**

Restart the API:
```bash
sudo systemctl restart mangataro.service
sleep 3
```

Test it:
```bash
curl -s "http://localhost:8008/api/search?q=solo+leveling" | python3 -m json.tool | head -40
```

Expected: JSON with `query` and `results` array containing one entry per active scanlator with a plugin. Wait up to 35s for Playwright scrapers.

**Step 4: Commit**

```bash
git add api/routers/search.py api/main.py
git commit -m "feat: add cross-scanlator search API endpoint"
```

---

## Task 2: Add the Search nav link

**Files:**
- Modify: `frontend/src/components/Navigation.astro`

**Step 1: Add the Search link to the nav**

In `frontend/src/components/Navigation.astro`, find the `links` array (line 7):

```typescript
const links = [
  { href: '/', label: 'Updates', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { href: '/library', label: 'Library', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
  { href: '/admin/add-manga', label: 'Add Manga', icon: 'M12 4v16m8-8H4' },
  { href: '/admin/map-sources', label: 'Map Sources', icon: '...' },
];
```

Add the Search link after Library (before Add Manga):

```typescript
{ href: '/search', label: 'Search', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
```

**Step 2: Verify nav compiles**

```bash
cd /data/mangataro/frontend
npm run build 2>&1 | tail -10
```

Expected: Build succeeds with no errors.

**Step 3: Commit**

```bash
git add frontend/src/components/Navigation.astro
git commit -m "feat: add Search link to navigation"
```

---

## Task 3: Create the search frontend page

**Files:**
- Create: `frontend/src/pages/search.astro`

**Step 1: Create the page**

Create `/data/mangataro/frontend/src/pages/search.astro`:

```astro
---
import Layout from '../layouts/Layout.astro';
---

<Layout title="Search - MangaTaro">
  <div
    class="max-w-4xl mx-auto"
    x-data="{
      query: '',
      loading: false,
      searched: false,
      results: [],
      error: '',
      async doSearch() {
        if (this.query.trim().length < 2) return;
        this.loading = true;
        this.searched = false;
        this.results = [];
        this.error = '';
        try {
          const res = await fetch(`${window.__API_BASE}/api/search?q=${encodeURIComponent(this.query.trim())}`);
          if (!res.ok) throw new Error(`Server error: ${res.status}`);
          const data = await res.json();
          this.results = data.results || [];
        } catch (e) {
          this.error = e.message || 'Search failed';
        } finally {
          this.loading = false;
          this.searched = true;
        }
      }
    }"
  >
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-display font-extrabold tracking-tight text-ink-50">Search</h1>
      <p class="text-ink-400 mt-1 text-sm">Find manga across all scanlators simultaneously</p>
    </div>

    <!-- Search Form -->
    <div class="flex gap-3 mb-10">
      <input
        type="text"
        x-model="query"
        @keydown.enter="doSearch()"
        placeholder="Enter title keywords..."
        class="flex-1 px-4 py-2.5 bg-ink-800/80 border border-ink-700/40 rounded-xl focus:outline-none focus:ring-2 focus:ring-crimson-600/40 text-ink-50 text-sm placeholder:text-ink-500"
      />
      <button
        @click="doSearch()"
        :disabled="loading || query.trim().length < 2"
        :class="{ 'opacity-50 cursor-not-allowed': loading || query.trim().length < 2 }"
        class="px-6 py-2.5 bg-crimson-600 hover:bg-crimson-500 disabled:hover:bg-crimson-600 text-white rounded-xl font-semibold text-sm transition-all"
      >
        <span x-show="!loading">Search</span>
        <span x-show="loading">Searching...</span>
      </button>
    </div>

    <!-- Loading State -->
    <div x-show="loading" class="text-center py-16">
      <div class="inline-block w-8 h-8 border-2 border-crimson-600 border-t-transparent rounded-full animate-spin mb-4"></div>
      <p class="text-ink-400 text-sm">Searching all scanlators — this may take up to 30 seconds...</p>
    </div>

    <!-- Error State -->
    <div x-show="!loading && error" class="text-center py-12 bg-ink-800/20 rounded-xl ring-1 ring-crimson-700/30">
      <p class="text-crimson-400 font-medium" x-text="error"></p>
    </div>

    <!-- Results -->
    <div x-show="!loading && searched && !error" class="space-y-8">

      <!-- No results at all -->
      <template x-if="results.every(r => r.matches.length === 0 && !r.error)">
        <div class="text-center py-16 bg-ink-800/20 rounded-xl ring-1 ring-ink-700/20">
          <p class="text-ink-400 font-medium">No results found on any scanlator</p>
          <p class="text-ink-500 text-sm mt-1">Try different keywords</p>
        </div>
      </template>

      <!-- Per-scanlator sections -->
      <template x-for="result in results" :key="result.scanlator">
        <div class="bg-ink-800/20 rounded-xl ring-1 ring-ink-700/20 overflow-hidden">
          <!-- Scanlator header -->
          <div class="flex items-center justify-between px-5 py-3 border-b border-ink-700/30">
            <div class="flex items-center gap-2">
              <span class="text-sm font-display font-bold text-ink-50" x-text="result.scanlator"></span>
              <template x-if="result.matches.length > 0">
                <span class="px-2 py-0.5 bg-crimson-600/20 text-crimson-400 text-xs font-semibold rounded-full" x-text="result.matches.length + ' found'"></span>
              </template>
            </div>
            <template x-if="result.error">
              <span class="text-xs text-crimson-400 font-medium" x-text="'Error: ' + result.error"></span>
            </template>
          </div>

          <!-- Matches -->
          <template x-if="result.matches.length > 0">
            <div class="divide-y divide-ink-700/20">
              <template x-for="match in result.matches" :key="match.url">
                <a
                  :href="match.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center gap-4 px-5 py-3 hover:bg-ink-700/20 transition-colors group"
                >
                  <!-- Cover -->
                  <template x-if="match.portada">
                    <img
                      :src="match.portada"
                      :alt="match.titulo"
                      class="w-10 h-14 object-cover rounded-lg ring-1 ring-ink-700/50 flex-shrink-0"
                      @error="$el.style.display='none'"
                    />
                  </template>
                  <template x-if="!match.portada">
                    <div class="w-10 h-14 bg-ink-700/50 rounded-lg flex-shrink-0"></div>
                  </template>

                  <!-- Title and URL -->
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold text-ink-100 group-hover:text-crimson-400 transition-colors truncate" x-text="match.titulo"></p>
                    <p class="text-xs text-ink-500 truncate mt-0.5" x-text="match.url"></p>
                  </div>

                  <!-- Arrow -->
                  <svg class="w-4 h-4 text-ink-500 group-hover:text-crimson-400 flex-shrink-0 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                  </svg>
                </a>
              </template>
            </div>
          </template>

          <!-- No matches for this scanlator -->
          <template x-if="result.matches.length === 0 && !result.error">
            <div class="px-5 py-4">
              <p class="text-ink-500 text-sm">No results</p>
            </div>
          </template>
        </div>
      </template>
    </div>
  </div>
</Layout>
```

**Step 2: Build and verify**

```bash
cd /data/mangataro/frontend
npm run build 2>&1 | tail -10
```

Expected: Build succeeds, `/search` page appears in output.

**Step 3: Test in browser**

With the dev server running (`npm run dev` or via systemd), visit `http://localhost:4343/search` and:
- Confirm the search form appears
- Search for "one piece" — wait up to 35s — confirm results appear per scanlator
- Confirm "No results" shows cleanly for scanlators with no match
- Confirm error is shown in red for any failed scanlator

**Step 4: Commit**

```bash
git add frontend/src/pages/search.astro
git commit -m "feat: add cross-scanlator search page"
```

---

## Notes

- **Resource contention:** If a tracking job is running when a search is triggered, two Playwright browsers will be active simultaneously. Acceptable for personal use.
- **Playwright scrapers with Cloudflare:** AsuraScans and RavenScans may hit Cloudflare and return empty results or errors. This is expected and shown transparently — not a bug.
- **Search quality:** Results depend entirely on each plugin's `buscar_manga()` implementation. MangaDex is most reliable. Playwright scrapers vary.
- **No caching:** Each search always hits live sites. This is intentional — search is rare and results should be current.
- **Minimum query length:** The API enforces `min_length=2` on the `q` parameter. The frontend also disables the button when `query.trim().length < 2`.
