# VortexScans Scanlator Plugin — Design Document

**Date:** 2026-03-08
**Status:** Approved

---

## Problem

The user wants to track manga chapters hosted on VortexScans (vortexscans.org).

## Solution

Implement a `VortexScans` scanlator plugin using VortexScans' public REST API (`api.vortexscans.org`) for search and chapter data. The manga detail pages are behind Cloudflare, so Playwright is used only to load the manga page and extract the internal `postId`. All chapter data is fetched via httpx.

---

## Architecture

### Site Characteristics

- **URL pattern:** `https://vortexscans.org/series/{slug}` (manga), `https://vortexscans.org/series/{slug}/{chapter-slug}` (chapter)
- **Frontend:** Custom Next.js app with Tailwind CSS
- **Cloudflare:** Blocks direct httpx on manga HTML pages; does NOT block `api.vortexscans.org`
- **Public REST API:** `https://api.vortexscans.org` — no auth required, returns JSON

### `buscar_manga(titulo)` — httpx only

```
GET https://api.vortexscans.org/api/posts?search={titulo}
→ { posts: [{id, slug, postTitle, featuredImage, ...}], totalCount }

Returns:
[
  {
    "titulo": post.postTitle,
    "url":    "https://vortexscans.org/series/{post.slug}",
    "portada": post.featuredImage
  },
  ...
]
```

No Playwright needed. Takes ~1s.

### `obtener_capitulos(manga_url)` — Playwright + httpx

1. Extract slug from URL (`/series/{slug}` → `slug`)
2. Playwright navigates to `manga_url` to pass Cloudflare
3. Intercept outgoing `api.vortexscans.org/api/chapters?postId=...` request → extract `postId`
4. httpx paginates all chapters: `GET /api/chapters?postId={id}&take=100&skip=0` (then `skip=100`, etc.) until `len(page) < 100`
5. Chapter URL = `https://vortexscans.org/series/{slug}/{chapter.slug}`
6. Date = ISO timestamp from `chapter.createdAt`
7. All chapters included regardless of lock status (locked chapters are still trackable)
8. Sort oldest → newest

```
Returns:
[
  {
    "numero": str(chapter.number),   # e.g. "233"
    "titulo": chapter.title or "",
    "url":    "https://vortexscans.org/series/{slug}/{chapter.slug}",
    "fecha":  datetime.fromisoformat(chapter.createdAt)
  },
  ...
]
```

### `parsear_numero_capitulo(texto)`

Chapter numbers from the API are already clean integers (233, 232, ...). The method strips the text to digits and returns as string. Standard fallback regex for edge cases.

---

## API Reference

| Endpoint | Method | Use |
|---|---|---|
| `/api/posts?search={q}` | GET | Search manga by title |
| `/api/chapters?postId={id}&take=100&skip={n}` | GET | Paginate chapters |

**Chapter response shape:**
```json
{
  "post": {
    "chapters": [
      {
        "id": 25280,
        "slug": "chapter-233",
        "number": 233,
        "title": "",
        "mangaPostId": 91,
        "createdAt": "2026-03-06T16:21:57.846Z",
        "isLocked": true,
        "mangaPost": { "slug": "rankers-return-c6f3k3os" }
      }
    ]
  },
  "totalChapterCount": 232
}
```

---

## Files Changed

| File | Change |
|---|---|
| `scanlators/vortex_scans.py` | New plugin (primary deliverable) |
| `scripts/test_vortex_scans.py` | Test script |

No API changes. No frontend changes. No DB schema changes.

---

## Database Setup

After implementation:

```sql
INSERT INTO scanlators (name, class_name, base_url)
VALUES ('VortexScans', 'VortexScans', 'https://vortexscans.org');
```

Then map manga via `/admin/map-sources` UI.
