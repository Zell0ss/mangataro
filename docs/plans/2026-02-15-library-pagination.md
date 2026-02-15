# Library Pagination Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add server-side pagination to the library page so it scales beyond 100 manga.

**Architecture:** Backend returns paginated response with total count. Frontend uses Alpine.js to manage state, fetch pages via API, and render cards client-side. Initial page is SSR'd, subsequent pages loaded via "Load More" button.

**Tech Stack:** FastAPI + Pydantic (backend), Astro + Alpine.js + TailwindCSS (frontend)

**Design doc:** `docs/plans/2026-02-15-library-pagination-design.md`

---

### Task 1: Add PaginatedMangaResponse schema

**Files:**
- Modify: `api/schemas.py` (add new schema after line 55)

**Step 1: Add the schema**

Add after the `MangaResponse` class (line 55) in `api/schemas.py`:

```python
class PaginatedMangaResponse(BaseModel):
    """Paginated list of manga"""
    items: List[MangaResponse]
    total: int
    skip: int
    limit: int
```

**Step 2: Commit**

```bash
git add api/schemas.py
git commit -m "feat: add PaginatedMangaResponse schema"
```

---

### Task 2: Update list_manga endpoint to return paginated response

**Files:**
- Modify: `api/routers/manga.py:12-52`

**Step 1: Update the endpoint**

Replace lines 12-52 in `api/routers/manga.py` with:

```python
@router.get("/", response_model=schemas.PaginatedMangaResponse)
async def list_manga(
    skip: int = Query(0, ge=0),
    limit: int = Query(48, ge=1, le=500),
    status: Optional[models.MangaStatus] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all manga with optional filtering and pagination.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (default 48, max 500)
    - **status**: Filter by manga status (reading, completed, on_hold, plan_to_read)
    - **search**: Search in title and alternative titles
    """
    query = db.query(models.Manga)

    # Filter by status
    if status:
        query = query.filter(models.Manga.status == status)

    # Search in title and alternative titles
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.Manga.title.like(search_pattern)) |
            (models.Manga.alternative_titles.like(search_pattern))
        )

    # Get total count before pagination
    total = query.count()

    # Order by last checked (most recently checked first, nulls last)
    query = query.order_by(
        models.Manga.last_checked.is_(None),
        models.Manga.last_checked.desc()
    )

    # Apply pagination
    manga = query.offset(skip).limit(limit).all()

    return {
        "items": manga,
        "total": total,
        "skip": skip,
        "limit": limit
    }
```

**Step 2: Test the endpoint**

```bash
curl -s "http://localhost:8008/api/manga/?limit=5" | python3 -m json.tool | head -20
```

Expected: JSON with `items`, `total`, `skip`, `limit` fields. `total` should be 94+.

```bash
curl -s "http://localhost:8008/api/manga/?limit=5&search=solo" | python3 -m json.tool
```

Expected: Filtered results with `total` reflecting the search count.

**Step 3: Commit**

```bash
git add api/routers/manga.py
git commit -m "feat: return paginated response from list_manga endpoint"
```

---

### Task 3: Update frontend API client

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Step 1: Add PaginatedMangaResponse interface**

Add after the `Manga` interface (after line 13) in `frontend/src/lib/api.ts`:

```typescript
export interface PaginatedMangaResponse {
  items: Manga[];
  total: number;
  skip: number;
  limit: number;
}
```

**Step 2: Replace getAllManga with getMangaPage**

Replace the `getAllManga` method (lines 104-108) with:

```typescript
  async getMangaPage(params: {
    skip?: number;
    limit?: number;
    search?: string;
    status?: string;
  } = {}): Promise<PaginatedMangaResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set('limit', String(params.limit ?? 48));
    searchParams.set('skip', String(params.skip ?? 0));
    if (params.search) searchParams.set('search', params.search);
    if (params.status && params.status !== 'all') searchParams.set('status', params.status);
    const response = await fetch(`${API_BASE}/api/manga?${searchParams}`);
    if (!response.ok) throw new Error('Failed to fetch manga');
    return response.json();
  },
```

**Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add getMangaPage with pagination params to API client"
```

---

### Task 4: Rewrite library.astro with pagination

**Files:**
- Modify: `frontend/src/pages/library.astro` (full rewrite)

**Step 1: Rewrite library.astro**

This is the biggest change. The page shifts from SSR-render-all to a hybrid approach:
- SSR fetches initial page (first 48 manga + total count), serialized as JSON into the page
- Alpine.js takes over for search, filter, pagination, and rendering new cards
- Cards are rendered via Alpine.js `x-for` template (not Astro MangaCard component) so dynamically loaded cards work

Key design decisions:
- The card HTML template is inlined in the Alpine.js template (duplicates MangaCard.astro visually, but must be client-renderable)
- `getCoverUrl` logic is inlined in the template
- NSFW filter is client-side only — applied after fetching

Replace the entire file with:

```astro
---
import Layout from '../layouts/Layout.astro';

const API_BASE = import.meta.env.PUBLIC_API_URL || 'http://localhost:8008';
const PAGE_SIZE = 48;

let initialData = { items: [], total: 0, skip: 0, limit: PAGE_SIZE };
let error = null;

try {
  const res = await fetch(`${API_BASE}/api/manga?limit=${PAGE_SIZE}&skip=0`);
  if (!res.ok) throw new Error('Failed to fetch manga');
  initialData = await res.json();
} catch (e) {
  console.error('Failed to fetch manga:', e);
  error = e.message;
}
---

<Layout title="Library - MangaTaro">
  <div>
    {error ? (
      <div class="text-center py-24">
        <p class="text-crimson-400 text-lg font-display font-semibold">Failed to load library</p>
        <p class="text-ink-500 text-sm mt-2">{error}</p>
      </div>
    ) : (
      <div
        x-data={`library(${JSON.stringify(initialData)})`}
        x-init="init()"
      >
        <!-- Header -->
        <div class="mb-8">
          <h1 class="text-3xl font-display font-extrabold tracking-tight text-ink-50">Library</h1>
          <p class="text-ink-400 mt-1 text-sm">
            <span x-text="headerText"></span>
          </p>
        </div>

        <!-- Search & Filters -->
        <div class="mb-8">
          <!-- Search -->
          <div class="relative max-w-md">
            <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              x-model="searchInput"
              @input="debouncedSearch()"
              placeholder="Search manga..."
              class="w-full pl-10 pr-4 py-2.5 bg-ink-800/80 border border-ink-700/40 rounded-xl focus:outline-none focus:ring-2 focus:ring-crimson-600/40 focus:border-crimson-600/40 text-ink-50 text-sm placeholder:text-ink-500 transition"
            />
          </div>

          <!-- Status Filter & NSFW Toggle -->
          <div class="flex items-center justify-between mt-4 gap-4">
            <div class="flex gap-1.5">
              <template x-for="s in ['all', 'reading', 'completed', 'on_hold']" :key="s">
                <button
                  @click="setStatus(s)"
                  :class="status === s ? 'bg-crimson-600 text-white shadow-sm shadow-crimson-900/30' : 'bg-ink-800/80 text-ink-400 hover:text-ink-200 hover:bg-ink-700/80 ring-1 ring-ink-700/30'"
                  class="px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 capitalize"
                  x-text="s === 'all' ? 'All' : s.replace('_', ' ')"
                ></button>
              </template>
            </div>

            <!-- NSFW Toggle -->
            <div class="flex items-center gap-2">
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  class="sr-only peer"
                  x-model="showNSFW"
                  @change="localStorage.setItem('showNSFW', showNSFW)"
                />
                <div class="w-11 h-6 bg-ink-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-crimson-600/40 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-crimson-600"></div>
                <span class="ml-3 text-sm font-medium text-ink-300">Show NSFW</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Loading indicator for search/filter -->
        <div x-show="loading && manga.length === 0" class="text-center py-24">
          <div class="inline-block w-8 h-8 border-2 border-ink-600 border-t-crimson-600 rounded-full animate-spin"></div>
          <p class="text-ink-400 mt-4 text-sm">Loading...</p>
        </div>

        <!-- Empty state -->
        <div x-show="!loading && filteredManga.length === 0" x-cloak class="text-center py-24">
          <p class="text-ink-400 text-lg">No manga found</p>
          <p class="text-ink-500 text-sm mt-2" x-show="searchInput || status !== 'all'">Try adjusting your search or filters</p>
        </div>

        <!-- Grid -->
        <div
          x-show="filteredManga.length > 0"
          class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
        >
          <template x-for="m in filteredManga" :key="m.id">
            <a
              :href="`/manga/${m.id}`"
              class="block group relative rounded-xl overflow-hidden bg-ink-800 ring-1 ring-ink-700/30 hover:ring-crimson-600/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-crimson-950/20"
            >
              <!-- Cover Image -->
              <div class="aspect-[2/3] overflow-hidden">
                <img
                  :src="m.cover_filename ? `/data/img/${m.cover_filename}` : '/placeholder-cover.jpg'"
                  :alt="m.title"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out"
                  loading="lazy"
                />
                <div class="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/20 to-transparent opacity-90"></div>
              </div>

              <!-- NSFW Badge -->
              <div
                x-show="m.nsfw"
                class="absolute top-2 left-2 bg-crimson-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-md shadow-lg ring-1 ring-crimson-500"
              >NSFW</div>

              <!-- Title Overlay -->
              <div class="absolute bottom-0 left-0 right-0 p-3">
                <h3
                  class="font-display font-semibold text-ink-50 line-clamp-2 text-sm leading-snug"
                  x-text="m.title"
                ></h3>
                <p
                  class="text-[11px] text-ink-400 mt-1 capitalize font-medium tracking-wide"
                  x-text="m.status.replace('_', ' ')"
                ></p>
              </div>
            </a>
          </template>
        </div>

        <!-- Load More Button -->
        <div x-show="hasMore" x-cloak class="mt-8 text-center">
          <button
            @click="loadMore()"
            :disabled="loading"
            class="px-6 py-2.5 bg-ink-800/80 hover:bg-ink-700/80 text-ink-200 rounded-xl text-sm font-semibold ring-1 ring-ink-700/30 hover:ring-crimson-600/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span x-show="!loading" x-text="`Load More (${total - manga.length} remaining)`"></span>
            <span x-show="loading" class="flex items-center gap-2">
              <span class="inline-block w-4 h-4 border-2 border-ink-600 border-t-crimson-600 rounded-full animate-spin"></span>
              Loading...
            </span>
          </button>
        </div>
      </div>
    )}
  </div>
</Layout>

<script>
  const API_BASE = import.meta.env.PUBLIC_API_URL || 'http://localhost:8008';
  const PAGE_SIZE = 48;

  document.addEventListener('alpine:init', () => {
    Alpine.data('library', (initialData) => ({
      manga: initialData.items,
      total: initialData.total,
      skip: initialData.items.length,
      status: 'all',
      searchInput: '',
      search: '',
      showNSFW: localStorage.getItem('showNSFW') === 'true',
      loading: false,
      debounceTimer: null,

      init() {},

      get filteredManga() {
        if (this.showNSFW) return this.manga;
        return this.manga.filter(m => !m.nsfw);
      },

      get hasMore() {
        return this.manga.length < this.total;
      },

      get headerText() {
        if (this.search || this.status !== 'all') {
          return `${this.total} manga found`;
        }
        return `${this.total} manga in your collection`;
      },

      debouncedSearch() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
          this.search = this.searchInput;
          this.fetchFresh();
        }, 300);
      },

      setStatus(s) {
        this.status = s;
        this.fetchFresh();
      },

      async fetchFresh() {
        this.loading = true;
        try {
          const params = new URLSearchParams();
          params.set('limit', PAGE_SIZE);
          params.set('skip', '0');
          if (this.search) params.set('search', this.search);
          if (this.status !== 'all') params.set('status', this.status);

          const res = await fetch(`${API_BASE}/api/manga?${params}`);
          if (!res.ok) throw new Error('Failed to fetch');
          const data = await res.json();

          this.manga = data.items;
          this.total = data.total;
          this.skip = data.items.length;
        } catch (e) {
          console.error('Failed to fetch manga:', e);
        } finally {
          this.loading = false;
        }
      },

      async loadMore() {
        this.loading = true;
        try {
          const params = new URLSearchParams();
          params.set('limit', PAGE_SIZE);
          params.set('skip', this.skip);
          if (this.search) params.set('search', this.search);
          if (this.status !== 'all') params.set('status', this.status);

          const res = await fetch(`${API_BASE}/api/manga?${params}`);
          if (!res.ok) throw new Error('Failed to fetch');
          const data = await res.json();

          this.manga = [...this.manga, ...data.items];
          this.total = data.total;
          this.skip = this.manga.length;
        } catch (e) {
          console.error('Failed to load more manga:', e);
        } finally {
          this.loading = false;
        }
      }
    }));
  });
</script>
```

**Step 2: Verify Alpine.js is loaded globally**

Check `frontend/src/layouts/Layout.astro` to confirm Alpine.js is loaded. If it is, this will work. If not, we need to add it.

**Step 3: Build and test**

```bash
cd /data/mangataro/frontend && npm run build
```

Expected: No build errors.

**Step 4: Commit**

```bash
git add frontend/src/pages/library.astro
git commit -m "feat: add server-side pagination to library page with Load More"
```

---

### Task 5: Clean up unused getAllManga from api.ts

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Step 1: Remove getAllManga**

The `library.astro` now fetches directly via `fetch()` in both SSR and Alpine.js, so `getAllManga()` is unused. Check if any other page imports it first:

```bash
grep -r "getAllManga" frontend/src/
```

If only `library.astro` used it (and it no longer does), remove the `getAllManga` method from `api.ts` (lines 104-108). Keep `getMangaPage` if added in Task 3, or remove it too since library.astro uses inline fetch.

**Step 2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "refactor: remove unused getAllManga from API client"
```

---

### Task 6: Manual testing and restart

**Step 1: Restart the service**

```bash
sudo systemctl restart mangataro.service
```

**Step 2: Test in browser**

Visit `http://localhost:4343/library` and verify:
- Initial load shows up to 48 manga with correct total count in header
- Search field filters via API (debounced)
- Status buttons filter via API
- NSFW toggle works (client-side)
- "Load More" button appears and loads next batch
- "Load More" disappears when all manga loaded
- Manga cards link correctly to `/manga/{id}`

**Step 3: Test edge cases**

- Search for something with no results → "No manga found" message
- Search + status filter combined
- Toggle NSFW while viewing filtered results
- Load all manga via repeated "Load More" clicks

**Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address library pagination issues found in testing"
```
