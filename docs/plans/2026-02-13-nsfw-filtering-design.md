# NSFW Filtering Feature Design

**Date:** 2026-02-13
**Status:** Design Approved - Ready for Implementation
**Goal:** Add NSFW flag to manga with toggle switches in Library and Updates pages to show/hide NSFW content

---

## Problem Statement

Users need a way to:
1. Mark manga as NSFW (Not Safe For Work)
2. Filter NSFW manga in Library and Updates pages
3. Have the preference persist across sessions
4. See a visual indicator when NSFW manga are shown

Since only a minority of manga are NSFW, a simple toggle system is sufficient.

---

## Requirements

From user discussion:

1. **NSFW Flag Management:** Set/edit NSFW flag on manga detail page
2. **Toggle Persistence:** Store preference in localStorage (no user accounts needed)
3. **Default State:** Hide NSFW by default (safer default)
4. **Visual Indicator:** Small "NSFW" badge on manga cards when shown
5. **Toggle Scope:** Global setting applies to both Library AND Updates pages

---

## Selected Approach: Frontend-Only Filtering

**Why this approach:**
- Self-hosted single-user app (network privacy not a concern)
- Simplest to implement (minimal backend changes)
- Instant toggle response (no API call needed)
- Works perfectly for minority of NSFW manga

**How it works:**
1. Add `nsfw` boolean field to Manga database model
2. API always returns all manga (no endpoint changes)
3. Frontend reads localStorage preference and filters manga client-side
4. Toggle switch updates localStorage and re-filters immediately

**Rejected alternatives:**
- API-level filtering: Overkill for single-user setup, adds complexity
- Hybrid approach: Unnecessary flexibility for current needs

---

## Design Details

### 1. Database Changes

**Add NSFW field to Manga model:**

```python
# api/models.py - Add to Manga class
nsfw = Column(Boolean, default=False, index=True)
```

**Database migration:**

```sql
ALTER TABLE mangas ADD COLUMN nsfw TINYINT(1) DEFAULT 0;
ALTER TABLE mangas ADD INDEX idx_nsfw (nsfw);
```

**Schema update:**

```python
# api/schemas.py - Update MangaBase/MangaResponse
class MangaBase(BaseModel):
    # ... existing fields ...
    nsfw: bool = False
```

**Rationale:**
- Indexed for potential future API-level filtering
- Default `False` for all existing manga (safe assumption)
- Can be updated later on manga detail pages

---

### 2. Backend API Changes

**Update manga endpoints:**

```python
# api/routers/manga.py

# GET /api/manga/{id} - Already returns nsfw field via schema (no changes)

# PATCH /api/manga/{id} - Add support for updating nsfw
@router.patch("/{manga_id}", response_model=schemas.MangaResponse)
async def update_manga(
    manga_id: int,
    manga_update: schemas.MangaUpdate,
    db: Session = Depends(get_db)
):
    manga = db.query(models.Manga).filter(models.Manga.id == manga_id).first()
    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")

    # Update fields including nsfw
    if manga_update.nsfw is not None:
        manga.nsfw = manga_update.nsfw

    db.commit()
    db.refresh(manga)
    return manga
```

**Schema changes:**

```python
# api/schemas.py

class MangaUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    nsfw: Optional[bool] = None  # Add this
```

**No filtering at API level** - API returns all manga, frontend handles filtering.

---

### 3. Frontend Filtering & Toggle

**Toggle Switch Component** (Library and Updates pages):

```astro
<!-- Shared localStorage key: 'showNSFW' -->
<div class="flex items-center gap-2 mb-4">
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

**Alpine.js data initialization:**

```javascript
x-data="{
  showNSFW: localStorage.getItem('showNSFW') === 'true', // Default: false (hidden)
  // ... existing search/status filters ...
  isVisible(element) {
    const isNSFW = element.dataset.nsfw === 'true';
    const nsfwMatch = this.showNSFW || !isNSFW; // Show if toggle on, OR not NSFW
    const statusMatch = this.status === 'all' || this.status === element.dataset.mangaStatus;
    const searchMatch = this.search === '' || element.dataset.mangaTitle.includes(this.search.toLowerCase());
    return nsfwMatch && statusMatch && searchMatch;
  }
}"
```

**Update manga cards to include data-nsfw attribute:**

```astro
<div
  x-show="isVisible($el)"
  data-nsfw={manga.nsfw}
  data-manga-status={manga.status}
  data-manga-title={manga.title.toLowerCase()}
>
  <MangaCard manga={manga} />
</div>
```

**Pages affected:**
- `frontend/src/pages/library.astro`
- `frontend/src/pages/index.astro` (Updates page)

---

### 4. Manga Detail Page - NSFW Toggle

**Add NSFW toggle button:**

```astro
<!-- In frontend/src/pages/manga/[id].astro -->
<div class="flex items-center gap-3 mt-4">
  <!-- Existing status dropdown -->

  <!-- NSFW Toggle Button -->
  <button
    @click="toggleNSFW()"
    :class="manga.nsfw ? 'bg-crimson-600 text-white ring-2 ring-crimson-500' : 'bg-ink-800 text-ink-300 ring-1 ring-ink-700'"
    class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 hover:opacity-90"
  >
    <span x-show="!manga.nsfw">Mark as NSFW</span>
    <span x-show="manga.nsfw">NSFW</span>
  </button>
</div>

<script>
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
      }
    } catch (error) {
      console.error('Failed to update NSFW flag:', error);
    }
  }
</script>
```

**Placement:** Next to status dropdown, clearly visible but not intrusive.

**Behavior:**
- Button shows "Mark as NSFW" when `nsfw = false` (gray background)
- Button shows "NSFW" when `nsfw = true` (red background with ring)
- Click toggles state and updates database

---

### 5. NSFW Badge (Visual Indicator)

**Add badge to manga cards:**

```astro
<!-- In frontend/src/components/MangaCard.astro -->
<a href={`/manga/${manga.id}`} class="...">
  <div class="aspect-[2/3] overflow-hidden relative">
    <img src={getCoverUrl(manga.cover_filename)} alt={manga.title} ... />

    <!-- NSFW Badge (only shown if manga.nsfw is true) -->
    {manga.nsfw && (
      <div class="absolute top-2 left-2 bg-crimson-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-md shadow-lg ring-1 ring-crimson-500">
        NSFW
      </div>
    )}
  </div>
  <!-- ... rest of card ... -->
</a>
```

**Badge design:**
- Position: Top-left corner (unread count is top-right)
- Size: Small (10px font)
- Color: Crimson red (matches theme)
- Visibility: Only when `manga.nsfw = true` AND `showNSFW = true`

---

## Complete Data Flow

### Setting NSFW Flag

1. User visits manga detail page (`/manga/{id}`)
2. Clicks "Mark as NSFW" button
3. Frontend sends `PATCH /api/manga/{id}` with `{nsfw: true}`
4. Backend updates `mangas.nsfw` in database
5. Button updates to show "NSFW" (red background)

### Filtering NSFW Manga

1. User visits Library or Updates page
2. Alpine.js initializes: reads `localStorage.getItem('showNSFW')` (defaults to `false`)
3. Toggle switch reflects current preference
4. `isVisible()` function filters manga:
   - If `showNSFW = false`: hide manga where `nsfw = true`
   - If `showNSFW = true`: show all manga, NSFW badge appears on flagged ones
5. User toggles switch → saves to localStorage → re-filters immediately (no page reload)

### Visual Feedback

- **Default state:** NSFW manga hidden
- **Toggle persistence:** Saved in localStorage, survives browser restarts
- **Badge appearance:** Red "NSFW" badge on top-left of flagged manga when shown
- **Global setting:** Same toggle applies to both Library and Updates pages

---

## Components Affected

**Backend:**
- `api/models.py` - Add `nsfw` field to Manga model
- `api/schemas.py` - Add `nsfw` to MangaBase, MangaUpdate, MangaResponse
- `api/routers/manga.py` - Update PATCH endpoint to accept `nsfw`
- Database migration script

**Frontend:**
- `frontend/src/pages/library.astro` - Add toggle switch, update filtering logic
- `frontend/src/pages/index.astro` - Add toggle switch, update filtering logic
- `frontend/src/pages/manga/[id].astro` - Add NSFW toggle button
- `frontend/src/components/MangaCard.astro` - Add NSFW badge

---

## Edge Cases & Considerations

**Migration:** All existing manga default to `nsfw=false`. Users can manually flag NSFW manga after implementation.

**Performance:** Frontend filtering is instant since we're filtering a minority of manga. No performance concerns for typical collection sizes (90-200 manga).

**Future enhancements (not in scope):**
- Bulk edit NSFW flags (can add later if needed)
- NSFW filter in search/admin pages
- API-level filtering (if multi-user support added)

---

## Success Criteria

✅ NSFW flag can be set/unset on manga detail page
✅ Library and Updates pages have "Show NSFW" toggle
✅ Toggle preference persists across browser sessions
✅ NSFW manga are hidden by default
✅ NSFW badge appears on flagged manga when shown
✅ Toggle applies globally to both pages
✅ Filtering is instant (no API calls)

---

## Implementation Notes

- Use existing Alpine.js patterns from library/updates pages
- Follow TailwindCSS theme (crimson for NSFW, ink for backgrounds)
- Keep toggle switch UI consistent with existing UI elements
- Test with both NSFW flagged and unflagged manga
- Verify localStorage persistence across page reloads

---

**Next Steps:** Create detailed implementation plan with writing-plans skill.
