# Library Pagination Design

**Date:** 2026-02-15
**Status:** Approved
**Problem:** Library page limited to 100 manga due to hardcoded API limit. Collection expected to grow to 200-500.

## Approach

Server-side pagination with "Load More" button. Search and status filters move server-side (API already supports them). NSFW toggle stays client-side.

## Backend Changes

### `GET /api/manga/` response format

Change from `List[MangaResponse]` to paginated wrapper:

```json
{
  "items": [{ "id": 1, "title": "...", ... }],
  "total": 142,
  "skip": 0,
  "limit": 48
}
```

- Raise `le` from 100 to 500
- Default page size: 48 (divisible by 2, 3, 4, 5, 6 — all grid column counts)
- Add `total` count query before pagination
- New Pydantic schema: `PaginatedMangaResponse`

### Files changed

- `api/schemas.py` — add `PaginatedMangaResponse` schema
- `api/routers/manga.py` — update `list_manga` endpoint to return paginated wrapper with total count

## Frontend Changes

### `api.ts`

- Update `getAllManga()` → `getMangaPage(skip, limit, search?, status?)` returning paginated response
- Add TypeScript interface for paginated response

### `library.astro`

Shift from SSR-fetch-all to hybrid Alpine.js-driven pagination:

- **Initial SSR load:** First 48 manga + total count
- **Alpine.js reactive state:** Manages loaded manga array, current skip, search, status, NSFW toggle
- **Search:** Debounced 300ms, resets to page 1, calls API with `search` param
- **Status filter:** Resets to page 1, calls API with `status` param
- **NSFW toggle:** Client-side filter on loaded results (localStorage persistence)
- **"Load More" button:** Fetches next 48, appends to grid. Shows remaining count.
- **Count display:** "Showing X of Y manga"
- **Loading state:** Subtle indicator while fetching

## UX Details

- Page size: 48
- Search debounce: 300ms
- Filters reset pagination to start
- NSFW filtering is purely client-side (privacy, no API changes needed)
- "Load More" disappears when all manga loaded
- Button text: "Load More (N remaining)"
