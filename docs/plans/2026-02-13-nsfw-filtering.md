# NSFW Filtering Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add NSFW flag to manga with toggle switches in Library and Updates pages for showing/hiding NSFW content.

**Architecture:** Frontend-only filtering approach with database-backed NSFW flag. Backend adds `nsfw` boolean field to Manga model and supports PATCH updates. Frontend uses Alpine.js + localStorage for instant client-side filtering with persistent user preference.

**Tech Stack:** FastAPI, SQLAlchemy, Astro, Alpine.js, TailwindCSS, MariaDB

---

## Task 1: Database Migration

**Files:**
- Create: `scripts/migrations/add_nsfw_field.sql`

**Step 1: Create migration SQL file**

```sql
-- scripts/migrations/add_nsfw_field.sql
-- Add NSFW flag to mangas table

ALTER TABLE mangas ADD COLUMN nsfw TINYINT(1) DEFAULT 0 NOT NULL;
ALTER TABLE mangas ADD INDEX idx_nsfw (nsfw);
```

**Step 2: Run migration**

```bash
mysql -u mangataro_user -p mangataro < scripts/migrations/add_nsfw_field.sql
```

Expected output: `Query OK, [N] rows affected` (twice - one for ADD COLUMN, one for ADD INDEX)

**Step 3: Verify migration**

```bash
mysql -u mangataro_user -p mangataro -e "DESCRIBE mangas;"
```

Expected: Output should include `nsfw | tinyint(1) | NO | | 0 |` row

**Step 4: Verify index**

```bash
mysql -u mangataro_user -p mangataro -e "SHOW INDEX FROM mangas WHERE Key_name = 'idx_nsfw';"
```

Expected: Should show index on `nsfw` column

**Step 5: Commit**

```bash
git add scripts/migrations/add_nsfw_field.sql
git commit -m "feat(db): add nsfw field to mangas table

- Add nsfw boolean column (default false)
- Add index for potential future API filtering
- All existing manga default to non-NSFW

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Backend - Update Manga Model

**Files:**
- Modify: `api/models.py:17-34` (Manga class)

**Step 1: Add nsfw field to Manga model**

Find the Manga class (around line 17) and add the nsfw field after the `status` field:

```python
class Manga(Base):
    __tablename__ = "mangas"

    id = Column(Integer, primary_key=True, index=True)
    mangataro_id = Column(String(50))
    title = Column(String(255), nullable=False, index=True)
    alternative_titles = Column(Text)
    cover_filename = Column(String(255))
    mangataro_url = Column(String(500))
    date_added = Column(DateTime)
    last_checked = Column(DateTime)
    status = Column(Enum(MangaStatus), default=MangaStatus.reading, index=True)
    nsfw = Column(Boolean, default=False, index=True)  # ADD THIS LINE
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga_scanlators = relationship("MangaScanlator", back_populates="manga", cascade="all, delete-orphan")
```

**Step 2: Restart API to load new model**

```bash
# If running with uvicorn --reload, it should auto-reload
# Otherwise, restart manually:
pkill -f "uvicorn api.main:app"
cd /data/mangataro && source .venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8008 &
```

**Step 3: Verify field is accessible**

```bash
curl http://localhost:8008/api/manga/1
```

Expected: JSON response should include `"nsfw": false` (or true if you manually set it)

**Step 4: Commit**

```bash
git add api/models.py
git commit -m "feat(api): add nsfw field to Manga model

- Add nsfw boolean column with default False
- Indexed for filtering performance
- Matches database schema from migration

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Backend - Update Pydantic Schemas

**Files:**
- Modify: `api/schemas.py`

**Step 1: Find and read current schemas**

```bash
grep -n "class MangaBase" api/schemas.py
grep -n "class MangaUpdate" api/schemas.py
```

**Step 2: Add nsfw to MangaBase schema**

Find `MangaBase` class and add `nsfw` field:

```python
class MangaBase(BaseModel):
    title: str
    alternative_titles: Optional[str] = None
    cover_filename: Optional[str] = None
    mangataro_url: Optional[str] = None
    status: Optional[str] = None
    nsfw: bool = False  # ADD THIS LINE
```

**Step 3: Add nsfw to MangaUpdate schema**

Find `MangaUpdate` class and add `nsfw` field:

```python
class MangaUpdate(BaseModel):
    title: Optional[str] = None
    alternative_titles: Optional[str] = None
    cover_filename: Optional[str] = None
    status: Optional[str] = None
    nsfw: Optional[bool] = None  # ADD THIS LINE
```

**Step 4: Verify schemas in API docs**

```bash
# API should auto-reload
# Visit http://localhost:8008/docs in browser
# Check /api/manga/{manga_id} GET and PATCH endpoints
# Should show nsfw field in response/request schemas
```

Expected: OpenAPI docs show `nsfw` field in manga schemas

**Step 5: Commit**

```bash
git add api/schemas.py
git commit -m "feat(api): add nsfw field to manga schemas

- Add nsfw to MangaBase (default False)
- Add nsfw to MangaUpdate (optional)
- Enables API to accept and return nsfw flag

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Backend - Update PATCH Endpoint

**Files:**
- Modify: `api/routers/manga.py`

**Step 1: Find the update_manga endpoint**

```bash
grep -n "def update_manga" api/routers/manga.py
```

**Step 2: Add nsfw update logic**

Find the `update_manga` function (PATCH endpoint) and add nsfw handling:

```python
@router.patch("/{manga_id}", response_model=schemas.MangaResponse)
async def update_manga(
    manga_id: int,
    manga_update: schemas.MangaUpdate,
    db: Session = Depends(get_db)
):
    manga = db.query(models.Manga).filter(models.Manga.id == manga_id).first()
    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Update fields
    if manga_update.title is not None:
        manga.title = manga_update.title
    if manga_update.alternative_titles is not None:
        manga.alternative_titles = manga_update.alternative_titles
    if manga_update.cover_filename is not None:
        manga.cover_filename = manga_update.cover_filename
    if manga_update.status is not None:
        manga.status = manga_update.status
    if manga_update.nsfw is not None:  # ADD THIS BLOCK
        manga.nsfw = manga_update.nsfw

    manga.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(manga)
    return manga
```

**Step 3: Test PATCH endpoint with curl**

```bash
# Test setting nsfw to true
curl -X PATCH http://localhost:8008/api/manga/1 \
  -H "Content-Type: application/json" \
  -d '{"nsfw": true}'
```

Expected: Response should show `"nsfw": true`

**Step 4: Verify in database**

```bash
mysql -u mangataro_user -p mangataro -e "SELECT id, title, nsfw FROM mangas WHERE id=1;"
```

Expected: `nsfw` column should show `1` (true)

**Step 5: Test setting back to false**

```bash
curl -X PATCH http://localhost:8008/api/manga/1 \
  -H "Content-Type: application/json" \
  -d '{"nsfw": false}'
```

Expected: Response should show `"nsfw": false`

**Step 6: Commit**

```bash
git add api/routers/manga.py
git commit -m "feat(api): support nsfw updates in PATCH endpoint

- Add nsfw handling to update_manga endpoint
- Allows toggling NSFW flag via API
- Tested with curl (true/false toggle)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Frontend - Add NSFW Badge to MangaCard

**Files:**
- Modify: `frontend/src/components/MangaCard.astro`

**Step 1: Read current MangaCard structure**

```bash
cat frontend/src/components/MangaCard.astro
```

Note the structure - find the `<div class="aspect-[2/3]">` that contains the cover image.

**Step 2: Add NSFW badge**

Find the cover image container and add the badge div:

```astro
---
import { getCoverUrl } from '../lib/utils';

const { manga } = Astro.props;
---

<a href={`/manga/${manga.id}`} class="group relative rounded-xl overflow-hidden bg-ink-800 ring-1 ring-ink-700/30 hover:ring-crimson-600/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-crimson-950/20">
  <div class="aspect-[2/3] overflow-hidden relative">
    <img
      src={getCoverUrl(manga.cover_filename)}
      alt={manga.title}
      class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
      loading="lazy"
    />

    <!-- NSFW Badge - ADD THIS BLOCK -->
    {manga.nsfw && (
      <div class="absolute top-2 left-2 bg-crimson-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-md shadow-lg ring-1 ring-crimson-500">
        NSFW
      </div>
    )}
  </div>

  <div class="p-3">
    <h3 class="font-display font-semibold text-ink-50 line-clamp-2 text-sm leading-snug">{manga.title}</h3>
    <p class="text-ink-400 text-xs mt-1 capitalize">{manga.status?.replace('_', ' ')}</p>
  </div>
</a>
```

**Step 3: Test visually**

1. Set a manga to NSFW in database: `mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=1 WHERE id=1;"`
2. Visit http://localhost:4343/library
3. Should see red "NSFW" badge on top-left of manga card

**Step 4: Test badge absence**

1. Set manga back: `mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=0 WHERE id=1;"`
2. Refresh library page
3. Badge should disappear

**Step 5: Commit**

```bash
git add frontend/src/components/MangaCard.astro
git commit -m "feat(ui): add NSFW badge to manga cards

- Show red 'NSFW' badge on top-left when manga.nsfw is true
- Small (10px font), crimson theme color
- Only visible when manga is flagged as NSFW
- Tested with flagged and unflagged manga

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Frontend - Update Library Page (Toggle + Filtering)

**Files:**
- Modify: `frontend/src/pages/library.astro`

**Step 1: Read current library page structure**

```bash
head -100 frontend/src/pages/library.astro
```

Note the Alpine.js `x-data` section and the `isVisible` function.

**Step 2: Add showNSFW to x-data**

Find the `x-data="{..."` block and add `showNSFW`:

```javascript
x-data="{
  search: '',
  status: 'all',
  showNSFW: localStorage.getItem('showNSFW') === 'true',  // ADD THIS LINE
  isVisible(element) {
    const mangaStatus = element.dataset.mangaStatus;
    const mangaTitle = element.dataset.mangaTitle;
    const isNSFW = element.dataset.nsfw === 'true';  // ADD THIS LINE
    const statusMatch = this.status === 'all' || this.status === mangaStatus;
    const searchMatch = this.search === '' || mangaTitle.includes(this.search.toLowerCase());
    const nsfwMatch = this.showNSFW || !isNSFW;  // ADD THIS LINE
    return statusMatch && searchMatch && nsfwMatch;  // UPDATE THIS LINE
  }
}"
```

**Step 3: Add toggle switch**

After the status filter buttons, add the toggle switch:

```astro
<!-- Status Filter -->
<div class="flex gap-1.5 mt-4">
  {['all', 'reading', 'completed', 'on_hold'].map(s => (
    <button
      @click={`status = '${s}'`}
      :class={`status === '${s}' ? 'bg-crimson-600 text-white shadow-sm shadow-crimson-900/30' : 'bg-ink-800/80 text-ink-400 hover:text-ink-200 hover:bg-ink-700/80 ring-1 ring-ink-700/30'`}
      class="px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 capitalize"
    >
      {s === 'all' ? 'All' : s.replace('_', ' ')}
    </button>
  ))}
</div>

<!-- NSFW Toggle - ADD THIS BLOCK -->
<div class="flex items-center gap-2 mt-4">
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
```

**Step 4: Add data-nsfw attribute to manga cards**

Find the manga card rendering and add `data-nsfw`:

```astro
<div
  x-show="isVisible($el)"
  x-transition:enter="transition ease-out duration-200"
  x-transition:enter-start="opacity-0 scale-95"
  x-transition:enter-end="opacity-100 scale-100"
  x-transition:leave="transition ease-in duration-150"
  x-transition:leave-start="opacity-100 scale-100"
  x-transition:leave-end="opacity-0 scale-95"
  data-manga-status={manga.status}
  data-manga-title={manga.title.toLowerCase()}
  data-nsfw={manga.nsfw}
>
  <MangaCard manga={manga} />
</div>
```

**Step 5: Test filtering**

1. Set one manga to NSFW: `mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=1 WHERE id=1;"`
2. Visit http://localhost:4343/library
3. By default, toggle should be OFF and NSFW manga should be hidden
4. Click toggle ON - NSFW manga should appear with badge
5. Click toggle OFF - NSFW manga should disappear

**Step 6: Test localStorage persistence**

1. Toggle ON
2. Refresh page (F5)
3. Toggle should still be ON and NSFW manga visible

**Step 7: Commit**

```bash
git add frontend/src/pages/library.astro
git commit -m "feat(ui): add NSFW filtering to library page

- Add 'Show NSFW' toggle switch
- Update isVisible() to filter based on nsfw flag
- Integrate with localStorage for persistence
- Add data-nsfw attribute to manga cards
- Tested: filtering works, persistence works

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Frontend - Update Updates Page (Toggle + Filtering)

**Files:**
- Modify: `frontend/src/pages/index.astro`

**Step 1: Read current updates page structure**

```bash
head -150 frontend/src/pages/index.astro
```

Note: This page has TWO views - "Latest" (grid) and "All Updates" (list). Both need filtering.

**Step 2: Filter mangaUpdates array**

After creating `mangaUpdates`, add filtering:

```astro
---
// ... existing imports and data fetching ...

const mangaUpdates = latestChapters.map(ch => ({
  chapter: ch,
  manga: ch.manga_scanlator.manga,
  scanlator: ch.manga_scanlator.scanlator,
  unreadCount: unreadCountPerManga.get(ch.manga_scanlator.manga.id) || 0,
}));

// ADD THIS BLOCK - Filter unread chapters based on NSFW
// Note: Client-side filtering happens in Alpine.js, but we pass nsfw data
---
```

**Step 3: Add Alpine.js data with showNSFW**

Find the x-data block and update:

```astro
<div class="max-w-5xl mx-auto" x-data="{
  mode: 'latest',
  showNSFW: localStorage.getItem('showNSFW') === 'true',
  isVisibleManga(nsfw) {
    return this.showNSFW || !nsfw;
  }
}">
```

**Step 4: Add toggle switch**

Add toggle between the header and the mode toggle:

```astro
<div class="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
  <div>
    <h1 class="text-3xl font-display font-extrabold tracking-tight text-ink-50">Updates</h1>
    <p class="text-ink-400 mt-1 text-sm">
      {unreadChapters.length} unread chapter{unreadChapters.length !== 1 ? 's' : ''} across {mangaUpdates.length} series
    </p>
  </div>

  <div class="flex gap-3 items-center">
    <!-- NSFW Toggle - ADD THIS BLOCK -->
    <label class="relative inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        class="sr-only peer"
        x-model="showNSFW"
        @change="localStorage.setItem('showNSFW', showNSFW)"
      />
      <div class="w-11 h-6 bg-ink-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-crimson-600/40 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-crimson-600"></div>
      <span class="ml-3 text-sm font-medium text-ink-300 whitespace-nowrap">Show NSFW</span>
    </label>

    {/* Mode toggle */}
    {mangaUpdates.length > 0 && (
      <div class="flex bg-ink-800/80 rounded-lg p-1 ring-1 ring-ink-700/40">
        <!-- ... existing mode toggle buttons ... -->
      </div>
    )}
  </div>
</div>
```

**Step 5: Add filtering to "Latest" grid view**

Find the "Latest" grid and add x-show:

```astro
<div x-show="mode === 'latest'" x-transition:enter="transition ease-out duration-200">
  <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
    {mangaUpdates.map(({ chapter, manga, scanlator, unreadCount }) => (
      <a
        x-show="isVisibleManga({manga.nsfw})"
        href={`/manga/${manga.id}`}
        class="group relative rounded-xl overflow-hidden bg-ink-800 ring-1 ring-ink-700/30 hover:ring-crimson-600/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-crimson-950/20"
      >
        <!-- ... rest of card ... -->
      </a>
    ))}
  </div>
</div>
```

**Step 6: Add filtering to "All Updates" list view**

Find the "All Updates" list and add x-show:

```astro
<div x-show="mode === 'all'" x-transition:enter="transition ease-out duration-200">
  <div class="space-y-2">
    {unreadChapters.map((chapter) => (
      <div x-show="isVisibleManga({chapter.manga_scanlator.manga.nsfw})">
        <ChapterItem chapter={chapter} />
      </div>
    ))}
  </div>
</div>
```

**Step 7: Test both views**

1. Set manga to NSFW: `mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=1 WHERE id=1;"`
2. Visit http://localhost:4343/
3. **Latest view:** NSFW manga should be hidden by default, visible when toggled
4. **All Updates view:** Chapters from NSFW manga should be hidden/shown based on toggle
5. Test toggle persistence (refresh page)

**Step 8: Commit**

```bash
git add frontend/src/pages/index.astro
git commit -m "feat(ui): add NSFW filtering to updates page

- Add 'Show NSFW' toggle switch
- Add isVisibleManga() filter function
- Filter both 'Latest' grid and 'All Updates' list views
- Integrate with localStorage for persistence
- Tested: both views filter correctly

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Frontend - Add NSFW Toggle to Manga Detail Page

**Files:**
- Modify: `frontend/src/pages/manga/[id].astro`

**Step 1: Read current manga detail page**

```bash
grep -A 20 "x-data" frontend/src/pages/manga/[id].astro | head -40
```

Note the Alpine.js data structure and where the status dropdown is.

**Step 2: Add manga.nsfw to Alpine.js data**

Ensure the initial data includes manga object with nsfw field (should already be there from API).

**Step 3: Add toggleNSFW function to script section**

Find or create the `<script>` section and add:

```astro
<script>
  // ADD THIS FUNCTION (or add to existing script tag)
  async function toggleNSFW() {
    const newValue = !this.manga.nsfw;
    try {
      const response = await fetch(`${window.__API_BASE}/api/manga/${this.manga.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nsfw: newValue })
      });
      if (response.ok) {
        this.manga.nsfw = newValue;
      } else {
        console.error('Failed to update NSFW flag');
      }
    } catch (error) {
      console.error('Error updating NSFW flag:', error);
    }
  }
</script>
```

**Step 4: Add NSFW toggle button**

Find the status dropdown section and add the button next to it:

```astro
<div class="flex items-center gap-3 mt-4">
  <!-- Existing status dropdown -->
  <select
    x-model="manga.status"
    @change="updateStatus()"
    class="..."
  >
    <!-- ... options ... -->
  </select>

  <!-- NSFW Toggle Button - ADD THIS -->
  <button
    @click="toggleNSFW()"
    :class="manga.nsfw ? 'bg-crimson-600 text-white ring-2 ring-crimson-500' : 'bg-ink-800 text-ink-300 ring-1 ring-ink-700'"
    class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 hover:opacity-90"
  >
    <span x-show="!manga.nsfw">Mark as NSFW</span>
    <span x-show="manga.nsfw">NSFW</span>
  </button>
</div>
```

**Step 5: Test NSFW toggle**

1. Visit http://localhost:4343/manga/1
2. Click "Mark as NSFW" button
3. Button should change to "NSFW" with red background
4. Verify in database: `mysql -u mangataro_user -p mangataro -e "SELECT id, title, nsfw FROM mangas WHERE id=1;"`
5. Click "NSFW" button again
6. Should toggle back to "Mark as NSFW" with gray background

**Step 6: Test error handling**

1. Stop API server: `pkill -f "uvicorn"`
2. Try toggling NSFW
3. Should see error in browser console
4. Restart API: `cd /data/mangataro && source .venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8008 &`

**Step 7: Commit**

```bash
git add frontend/src/pages/manga/[id].astro
git commit -m "feat(ui): add NSFW toggle to manga detail page

- Add 'Mark as NSFW' / 'NSFW' toggle button
- Implement toggleNSFW() function with PATCH request
- Visual feedback: gray (not NSFW) vs red (NSFW)
- Error handling for failed requests
- Tested: toggle works, persists to database

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: End-to-End Testing & Verification

**Files:**
- None (testing only)

**Step 1: Reset test data**

```bash
# Set one manga to NSFW for testing
mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=1 WHERE id=1;"
mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=0 WHERE id > 1;"
```

**Step 2: Test complete workflow**

1. **Manga Detail Page:**
   - Visit http://localhost:4343/manga/2
   - Click "Mark as NSFW"
   - Should change to red "NSFW" button
   - Refresh page - button should still be red

2. **Library Page:**
   - Visit http://localhost:4343/library
   - By default, manga #1 and #2 should be hidden (NSFW filter OFF)
   - Toggle "Show NSFW" ON
   - Manga #1 and #2 should appear with red "NSFW" badge
   - Toggle OFF - they should disappear

3. **Updates Page:**
   - Visit http://localhost:4343/
   - NSFW manga should be hidden by default
   - Toggle "Show NSFW" ON
   - NSFW manga should appear in both "Latest" and "All Updates" views
   - Toggle OFF - should disappear

4. **localStorage Persistence:**
   - Turn toggle ON
   - Visit library, then updates, then library again
   - Toggle should remain ON across all pages
   - Close browser completely
   - Reopen and visit library
   - Toggle should still be ON

5. **Badge Visibility:**
   - With "Show NSFW" ON, NSFW manga should show badge
   - Toggle OFF, manga disappears (so badge not visible)
   - Toggle ON, badge reappears

**Step 3: Test edge cases**

```bash
# Test with no NSFW manga
mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=0;"
```

Visit library and updates - toggle should work but have no effect (no manga to hide)

```bash
# Test with all NSFW manga
mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=1;"
```

Visit library and updates - toggle OFF should hide everything, ON should show all with badges

**Step 4: Verify database state**

```bash
mysql -u mangataro_user -p mangataro -e "SELECT COUNT(*), nsfw FROM mangas GROUP BY nsfw;"
```

Expected: Should show count of NSFW vs non-NSFW manga

**Step 5: Clean up test data**

```bash
# Reset all manga to non-NSFW (safe default)
mysql -u mangataro_user -p mangataro -e "UPDATE mangas SET nsfw=0;"
```

**Step 6: Final verification checklist**

- ✅ Database has nsfw column with index
- ✅ API GET returns nsfw field
- ✅ API PATCH accepts nsfw updates
- ✅ Manga detail page has toggle button
- ✅ Library page has toggle switch and filters correctly
- ✅ Updates page has toggle switch and filters correctly
- ✅ NSFW badge appears on manga cards
- ✅ localStorage persists preference
- ✅ Default state is hidden (showNSFW = false)
- ✅ Toggle works globally across both pages

**Step 7: Final commit**

```bash
git add -A
git commit -m "test: verify NSFW filtering end-to-end

- Tested complete workflow: set flag, filter, persist
- Verified localStorage persistence across sessions
- Tested both Library and Updates page filtering
- Confirmed NSFW badge appears/disappears correctly
- All success criteria met

Feature complete:
✅ NSFW flag on manga detail page
✅ Toggle on Library and Updates pages
✅ Persistent preference (localStorage)
✅ Hidden by default
✅ NSFW badge visual indicator
✅ Global setting applies to both pages

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Success Criteria Verification

After completing all tasks, verify:

- ✅ NSFW flag can be set/unset on manga detail page
- ✅ Library and Updates pages have "Show NSFW" toggle
- ✅ Toggle preference persists across browser sessions (localStorage)
- ✅ NSFW manga are hidden by default (showNSFW defaults to false)
- ✅ NSFW badge appears on flagged manga when shown
- ✅ Toggle applies globally to both Library and Updates pages
- ✅ Filtering is instant (no API calls for filtering)

---

## Common Issues & Solutions

**Issue: Toggle doesn't persist**
- Check browser console for localStorage errors
- Verify `@change="localStorage.setItem('showNSFW', showNSFW)"` is present

**Issue: NSFW badge always shows**
- Check Alpine.js conditional: `{manga.nsfw && (...)}` must have `&&` not `||`
- Verify manga object has nsfw field

**Issue: Filtering doesn't work**
- Check `data-nsfw={manga.nsfw}` attribute on manga card containers
- Verify `isVisible()` or `isVisibleManga()` includes `nsfwMatch` in return
- Check browser console for JavaScript errors

**Issue: PATCH endpoint returns 404**
- Verify API is running: `curl http://localhost:8008/health`
- Check manga ID exists: `mysql -u mangataro_user -p mangataro -e "SELECT id FROM mangas;"`

**Issue: Migration fails**
- Check if column already exists: `mysql -u mangataro_user -p mangataro -e "DESCRIBE mangas;"`
- If exists, skip migration or use `ALTER TABLE mangas MODIFY COLUMN nsfw...`

---

## Development Tips

- **Testing NSFW flag:** Use mysql commands to quickly set/unset for testing
- **Frontend hot reload:** Astro dev server should auto-reload on file changes
- **API hot reload:** uvicorn --reload should auto-reload on Python file changes
- **localStorage:** Use browser DevTools → Application → Local Storage to view/edit
- **Alpine.js debugging:** Use `x-log` directive or browser console to debug state

---

**Implementation complete!** All tasks ready for execution.
