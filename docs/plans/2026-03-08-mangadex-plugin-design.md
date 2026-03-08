# MangaDex Scanlator Plugin — Design Document

**Date:** 2026-03-08
**Status:** Approved
**Context:** Bato.to shut down 2026-01-19; MangaDex is the replacement target.

---

## Problem

The user needs to track new chapters for manga hosted on MangaDex, including "Bromance Book Club". Previous candidates (Bato.to, ManhwaClan, Manta.net) were either shut down or blocked by Cloudflare Turnstile in headless Playwright.

## Solution

Implement a `MangaDex` scanlator plugin using the MangaDex public REST API (`api.mangadex.org`) instead of Playwright-based scraping. No browser automation required.

---

## Architecture

### API Access

MangaDex provides a public, unauthenticated REST API:

- **Search:** `GET https://api.mangadex.org/manga?title={query}&availableTranslatedLanguage[]=en&limit=10`
- **Chapters:** `GET https://api.mangadex.org/chapter?manga={uuid}&translatedLanguage[]=en&order[chapter]=desc&limit=500`

No Cloudflare. No auth token. No Playwright page needed.

### URL Format

MangaDex manga URLs follow this pattern:

```
https://mangadex.org/title/32d76d19-8a05-4db0-9fc2-e0b0648fe9d0/solo-leveling
```

The UUID is always the path segment immediately after `/title/`. The slug is optional and ignored.

Chapter URLs use the chapter UUID:

```
https://mangadex.org/chapter/f7d2cb75-83b2-426b-bdbd-032870c30abb
```

### HTTP Client

`httpx` (v0.27.0, already installed) is used for all API calls — it supports `async`/`await` natively, matching the plugin interface.

---

## Plugin Class

**File:** `scanlators/manga_dex.py`
**Class name:** `MangaDex` (used for plugin discovery via `class_name` in DB)
**Display name:** `MangaDex`
**Base URL:** `https://mangadex.org`

### Interface Compliance

`BaseScanlator.__init__` requires a `playwright_page` argument. The `MangaDex` plugin accepts it and stores it as `self.page` for interface compatibility but never uses it. All network calls go through `httpx.AsyncClient`.

### Methods

#### `obtener_capitulos(manga_url: str) -> list[dict]`

1. Extract UUID from URL path (second segment after `/title/`)
2. Fetch chapters from `/chapter` endpoint with `translatedLanguage[]=en`, `order[chapter]=desc`, `limit=500`
3. Paginate if `total > 500` (rare, but correct)
4. Map each chapter to the plugin return format:
   ```python
   {
       "numero": ch["attributes"]["chapter"],   # e.g. "42", "42.5"
       "titulo": ch["attributes"]["title"] or "",
       "url":    f"https://mangadex.org/chapter/{ch['id']}",
       "fecha":  datetime.fromisoformat(ch["attributes"]["publishAt"])
   }
   ```
5. Add 0.5s delay between paginated requests (API courtesy)

#### `buscar_manga(titulo: str) -> list[dict]`

1. Call `/manga` with `title={titulo}&availableTranslatedLanguage[]=en&limit=10`
2. For each result, extract cover art relationship ID, construct cover URL:
   `https://uploads.mangadex.org/covers/{manga_uuid}/{filename}`
3. Return:
   ```python
   {
       "titulo": title_en or first_available_title,
       "url":    f"https://mangadex.org/title/{manga_id}",
       "portada": cover_url
   }
   ```

#### `parsear_numero_capitulo(texto: str) -> str`

MangaDex already provides clean chapter numbers (e.g. `"42"`, `"42.5"`). This method strips whitespace and returns as-is. Fallback regex for any edge cases.

---

## Data Mapping

| MangaDex API field | Plugin field | DB field |
|---|---|---|
| `attributes.chapter` | `numero` | `chapter_number` |
| `attributes.title` | `titulo` | `title` |
| `chapter/{id}` URL | `url` | `url` |
| `attributes.publishAt` | `fecha` | `release_date` |

---

## Scope

- Chapters filtered to English only (`translatedLanguage[]=en`)
- All scanlation groups included (no group filtering)
- No MangaDex authentication — public API only
- `externalUrl` chapters (e.g. Webnovel) are included; the chapter URL links to the MangaDex reader page which redirects externally

---

## Files Changed

| File | Change |
|---|---|
| `scanlators/manga_dex.py` | New plugin (primary deliverable) |
| `requirements.txt` | No change — `httpx` already installed |

No database changes. No API changes. No frontend changes.

---

## Database Setup

After implementation, add the scanlator record:

```sql
INSERT INTO scanlators (name, class_name, base_url)
VALUES ('MangaDex', 'MangaDex', 'https://mangadex.org');
```

Then map manga via the existing `/admin/map-sources` UI or API.
