# Cross-Scanlator Search — Design Document

**Date:** 2026-03-08
**Status:** Approved

---

## Problem

Users can't easily discover whether a manga exists on any of their tracked scanlators. To add a new manga, they currently have to manually visit each site. A search page that queries all plugins simultaneously would solve this.

## Solution

A `/search` page that accepts a title query and shows results from all registered scanlators in parallel.

---

## Architecture

### Approach

Option A: single API endpoint, all scanlators searched in parallel with `asyncio.gather`, results returned as one JSON payload. The frontend shows a spinner while waiting (~20-30s), then all results appear at once.

### Backend

**New file:** `api/routers/search.py`
**New endpoint:** `GET /api/search?q={title}`

For the 3 Playwright-based scrapers (AsuraScans, RavenScans, MadaraScans), a single Chromium browser is launched with one page per scraper. MangaDex (httpx-based) reuses one of those pages as a dummy. All 4 `buscar_manga()` calls run concurrently via `asyncio.gather`.

```
Request arrives
  ├── Launch 1 Playwright browser
  ├── Create 3 pages
  ├── asyncio.gather(
  │     AsuraScans(page1).buscar_manga(q),    ← Playwright
  │     RavenScans(page2).buscar_manga(q),    ← Playwright
  │     MadaraScans(page3).buscar_manga(q),   ← Playwright
  │     MangaDex(page1).buscar_manga(q)       ← httpx, page unused
  │   )
  ├── Close browser
  └── Return combined JSON
```

Only scanlators registered in the `scanlators` DB table with a matching plugin class are searched. Unknown/unimplemented scanlators are skipped gracefully.

**Timeout:** 30s per scanlator via `asyncio.wait_for`. A failed scraper sets `error` and does not block the others.

**Response shape:**
```json
{
  "query": "solo leveling",
  "results": [
    {
      "scanlator": "AsuraScans",
      "matches": [
        {"titulo": "Solo Leveling", "url": "https://...", "portada": "https://..."}
      ],
      "error": null
    },
    {
      "scanlator": "MangaDex",
      "matches": [...],
      "error": null
    },
    {
      "scanlator": "RavenScans",
      "matches": [],
      "error": null
    },
    {
      "scanlator": "MadaraScans",
      "matches": [],
      "error": "Timeout"
    }
  ]
}
```

Every registered scanlator always appears — empty `matches` if nothing found, `error` string if the plugin failed.

### Frontend

**New page:** `frontend/src/pages/search.astro`

- Minimal SSR shell; all interactivity handled by Alpine.js
- Search form with text input + submit button
- On submit: `fetch('/api/search?q=...')`, shows spinner during wait
- Results rendered per scanlator in card sections
- Each result: cover thumbnail (if available) + title linking to the scanlator URL
- "No results" shown when `matches` is empty
- Error shown in red when `error` is non-null

**Navigation:** "Search" link added to `Layout.astro` nav bar.

---

## Files Changed

| File | Change |
|---|---|
| `api/routers/search.py` | New — search endpoint |
| `api/main.py` | Register new router |
| `frontend/src/pages/search.astro` | New — search page |
| `frontend/src/layouts/Layout.astro` | Add "Search" nav link |

No DB changes. No schema changes.

---

## Constraints

- Search requires a live Playwright browser — it cannot run during an active tracking job without resource contention (acceptable for personal use)
- Playwright scrapers that have Cloudflare protection may return empty results or errors — this is expected and shown transparently
- Result quality depends on each plugin's `buscar_manga()` implementation
