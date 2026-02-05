# Manga-Scanlator Mapping UI Design

**Date:** 2026-02-05
**Status:** Design Complete - Ready for Implementation
**Phase:** Phase 1 (Admin Bulk Mapping) + Phase 2 (Detail Page Management)

---

## Overview

Add web UI for managing manga-scanlator mappings. Currently requires database updates or command-line scripts. This feature enables:
- **Phase 1:** Bulk mapping unmapped manga via admin page (immediate need)
- **Phase 2:** Per-manga management via detail page (ongoing maintenance)

## User Requirements

- User has ~23 manga needing AsuraScans mapping (peak unmapped period)
- After initial bulk mapping, will rarely add new mappings
- Wants quick, focused interface for current task
- Needs ability to add/remove mappings per manga later

## Design Decisions

### Phase 1: Admin Bulk Mapping Page

**Location:** `/admin/map-sources`

**Access:**
- Link in main navigation (Layout.astro)
- No authentication needed (single-user system)

**Purpose:**
Map multiple unmapped manga to scanlators efficiently.

---

## Phase 1 Architecture

### Page Structure

```
┌─────────────────────────────────────────────────────┐
│ [← Back to Library]           MangaTaro             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Map Manga Sources                                   │
│                                                      │
│  Scanlator: [AsuraScans ▼]                          │
│  23 manga need mapping                               │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ [Cover] Solo Leveling                          │ │
│  │         URL: [___________________________] [Add]│ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ [Cover] One Punch Man                          │ │
│  │         URL: [___________________________] [Add]│ │
│  │         ❌ Error: URL must be from asurascans.com│ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ... (more manga rows)                               │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Components

**Header:**
- Page title: "Map Manga Sources"
- Scanlator dropdown: All active scanlators, defaults to AsuraScans
- Counter: "X manga need mapping" (updates as mappings added)

**Manga Row:**
- Small cover thumbnail (48x72px)
- Manga title
- URL input field (full width, placeholder shows expected URL format)
- "Add" button (enabled only when URL valid)
- Inline error message area (red text, appears below input)

**Empty State:**
- Shown when all manga mapped for selected scanlator
- Message: "🎉 All Done! All manga are mapped to [Scanlator]"
- Prompt to switch scanlator

### Data Flow

**On Page Load (SSR):**
1. Fetch all active scanlators for dropdown
2. Get default scanlator (AsuraScans or first active)
3. Fetch unmapped manga for default scanlator
4. Render page with data

**On Scanlator Change (Client):**
1. User selects different scanlator from dropdown
2. Page reloads with query param: `/admin/map-sources?scanlator=3`
3. SSR fetches unmapped manga for new scanlator
4. Page renders with new list

**On Add Mapping (Client):**
1. User enters URL in input field
2. On blur: Validate URL format and base_url match
3. If invalid: Show inline error, disable "Add" button
4. If valid: Enable "Add" button, clear error
5. On click "Add": POST to API
6. On success: Row fades out and removes from DOM
7. On error: Show inline error message
8. Counter decrements automatically as rows disappear

---

## API Design

### New Endpoint

**GET `/api/manga/unmapped`**

**Query Parameters:**
- `scanlator_id` (required): Filter by scanlator

**Response:**
```json
{
  "scanlator_id": 3,
  "scanlator_name": "AsuraScans",
  "base_url": "https://asurascans.com",
  "unmapped_manga": [
    {
      "id": 5,
      "title": "Solo Leveling",
      "cover_filename": "abc-123.jpg",
      "status": "reading"
    }
  ],
  "count": 23
}
```

**Backend Logic:**
```sql
SELECT m.* FROM mangas m
WHERE m.id NOT IN (
  SELECT manga_id FROM manga_scanlator
  WHERE scanlator_id = ? AND manually_verified = 1
)
ORDER BY m.title
```

### Existing Endpoints (Reused)

**GET `/api/scanlators`**
- Fetch all scanlators for dropdown
- Filter: `active = 1`

**POST `/api/tracking/manga-scanlators`**
- Create new manga-scanlator mapping
- Body: `{manga_id, scanlator_id, scanlator_manga_url, manually_verified: true}`

---

## Frontend Implementation

### File Structure

```
frontend/src/
├── pages/
│   └── admin/
│       └── map-sources.astro    # New admin page
├── lib/
│   └── api.ts                   # Add getUnmappedManga()
└── layouts/
    └── Layout.astro             # Add "Admin" link
```

### Technology Stack

- **Astro:** SSR for initial data load and page structure
- **Alpine.js:** Client-side interactivity (form validation, API calls, animations)
- **TailwindCSS:** Styling (consistent with existing pages)

### Component Pseudo-code

**map-sources.astro (SSR):**
```astro
---
import Layout from '../../layouts/Layout.astro';
import { api } from '../../lib/api';

const scanlatorId = Astro.url.searchParams.get('scanlator') || null;
const scanlators = await api.getScanlators();
const defaultScanlator = scanlatorId
  ? scanlators.find(s => s.id == scanlatorId)
  : scanlators.find(s => s.name === 'AsuraScans') || scanlators[0];

const data = await api.getUnmappedManga(defaultScanlator.id);
---

<Layout title="Map Manga Sources">
  <h1>Map Manga Sources</h1>

  <select onchange="location.href=`/admin/map-sources?scanlator=${this.value}`">
    {scanlators.map(s =>
      <option value={s.id} selected={s.id === defaultScanlator.id}>
        {s.name}
      </option>
    )}
  </select>

  <p>{data.count} manga need mapping</p>

  <div id="manga-list">
    {data.unmapped_manga.map(manga =>
      <MangaRow
        manga={manga}
        scanlatorId={data.scanlator_id}
        baseUrl={data.base_url}
      />
    )}
  </div>
</Layout>
```

**MangaRow (Alpine.js component):**
```astro
<div
  x-data="mangaRow({
    mangaId: {manga.id},
    scanlatorId: {scanlatorId},
    baseUrl: '{baseUrl}'
  })"
  class="manga-row"
>
  <img src={getCoverUrl(manga.cover_filename)} />
  <h3>{manga.title}</h3>

  <input
    type="url"
    x-model="url"
    @blur="validateUrl()"
    placeholder="{baseUrl}/manga/..."
    class="url-input"
  />

  <button
    @click="addMapping()"
    :disabled="!isValid"
    class="add-button"
  >
    Add
  </button>

  <p x-show="error" class="error-message">
    <span x-text="error"></span>
  </p>
</div>

<script>
function mangaRow(config) {
  return {
    url: '',
    error: null,
    isValid: false,

    validateUrl() {
      const cleanBaseUrl = config.baseUrl.replace(/^https?:\/\//, '');

      // Check URL format
      if (!this.url.startsWith('http://') && !this.url.startsWith('https://')) {
        this.error = 'URL must start with http:// or https://';
        this.isValid = false;
        return;
      }

      // Check base URL match
      if (!this.url.includes(cleanBaseUrl)) {
        this.error = `URL must be from ${config.baseUrl}`;
        this.isValid = false;
        return;
      }

      this.error = null;
      this.isValid = true;
    },

    async addMapping() {
      try {
        await fetch('/api/tracking/manga-scanlators', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            manga_id: config.mangaId,
            scanlator_id: config.scanlatorId,
            scanlator_manga_url: this.url,
            manually_verified: true
          })
        });

        // Fade out and remove
        this.$el.classList.add('fade-out');
        setTimeout(() => this.$el.remove(), 300);

      } catch (e) {
        this.error = e.message || 'Failed to save. Try again.';
      }
    }
  }
}
</script>
```

---

## Error Handling

### Validation Errors

**Invalid URL Format:**
- **Trigger:** URL doesn't start with http:// or https://
- **Display:** Inline error: "URL must start with http:// or https://"
- **Action:** User corrects, error clears on blur

**Wrong Scanlator URL:**
- **Trigger:** URL doesn't contain scanlator's base_url
- **Display:** Inline error: "URL must be from https://asurascans.com"
- **Action:** User corrects, error clears on blur

### API Errors

**Duplicate Mapping:**
- **Trigger:** Manga already has verified mapping (shouldn't happen, filtered out)
- **Display:** Inline error: "Already mapped to this scanlator"
- **Action:** Backend safety check, row shouldn't be in list

**Network Failure:**
- **Trigger:** API request fails (timeout, server error, network down)
- **Display:** Inline error: "Failed to save. Try again."
- **Action:** User can retry without losing entered URL

### Edge Cases

**No Unmapped Manga:**
- **Trigger:** All manga already mapped for selected scanlator
- **Display:** Empty state with success message and scanlator switcher
- **Action:** User switches to different scanlator

**Concurrent Mapping:**
- **Trigger:** User maps same manga in multiple tabs
- **Display:** Second request fails with duplicate error
- **Action:** Row already removed in first tab, error in second tab

---

## Phase 2: Manga Detail Page Management

**Status:** Future Enhancement (not part of initial implementation)

**Location:** `/manga/[id]` - in "Tracking On" section

**Purpose:**
Add or remove scanlator mappings for individual manga during ongoing maintenance.

### UI Mockup

```
┌─────────────────────────────────────────────┐
│ Tracking On                                  │
│ ┌──────────────┐ ┌──────────────┐          │
│ │ AsuraScans × │ │ MangaDex   × │  [+ Add] │
│ └──────────────┘ └──────────────┘          │
└─────────────────────────────────────────────┘
```

### Interactions

**Add Source:**
1. Click "+ Add" → Modal/dropdown appears
2. Select scanlator from active list
3. Enter URL for that scanlator
4. Validate against base_url
5. Save with `manually_verified=true`
6. New badge appears in "Tracking On" section

**Remove Source:**
1. Click "×" on badge → Confirmation dialog
2. "Remove [Scanlator] tracking? This will delete all tracked chapters."
3. Confirm → DELETE manga_scanlator (cascade deletes chapters)
4. Badge disappears

**Why Separate Phase:**
- Different use case: per-manga maintenance vs bulk initial setup
- Different UI pattern: modal/inline vs dedicated page
- Phase 1 solves immediate need (bulk mapping)
- Phase 2 adds convenience for ongoing maintenance
- Can be implemented independently

---

## Implementation Checklist

### Backend
- [ ] Add `GET /api/manga/unmapped?scanlator_id=X` endpoint
  - Query manga not in manga_scanlator with manually_verified=1
  - Include scanlator info (name, base_url) in response
- [ ] Test endpoint with various scanlator IDs
- [ ] Verify existing POST endpoint handles duplicates gracefully

### Frontend
- [ ] Create `frontend/src/pages/admin/map-sources.astro`
- [ ] Add `getUnmappedManga()` to `frontend/src/lib/api.ts`
- [ ] Implement Alpine.js `mangaRow` component
- [ ] Add URL validation logic (format + base_url check)
- [ ] Implement fade-out animation on successful mapping
- [ ] Add "Admin" link to Layout.astro navigation
- [ ] Style with TailwindCSS (consistent with existing pages)
- [ ] Test error handling (invalid URL, network failure)
- [ ] Test empty state (all manga mapped)

### Testing
- [ ] Test with AsuraScans (default scanlator)
- [ ] Test switching scanlators via dropdown
- [ ] Test URL validation (valid/invalid formats, wrong scanlator)
- [ ] Test successful mapping (row disappears, counter updates)
- [ ] Test error scenarios (duplicate, network failure)
- [ ] Test empty state display
- [ ] Test on mobile (responsive layout)

---

## Success Criteria

**Phase 1 Complete When:**
- Can view list of unmapped manga for any active scanlator
- Can add manga-scanlator mapping with URL via web UI
- URL validation prevents common mistakes (wrong scanlator, bad format)
- Successful mappings remove from list immediately
- Errors display inline with clear messages
- All manga mapped shows success state
- No database/script access required for mapping

**User Can:**
- Map all 23 AsuraScans manga via web UI in <10 minutes
- Switch to other scanlators and map those too
- See validation errors before submitting
- Know when they're done (empty state)

---

## Future Enhancements (Beyond Phase 2)

- Batch URL paste (paste 10 URLs, auto-match to manga)
- AsuraScans search integration (search their site from UI)
- URL testing (verify URL works before saving)
- Bulk operations (select multiple, apply same scanlator)
- History/audit log (who mapped what, when)
- Auto-suggestion (detect manga title in URL, suggest manga)

---

## Notes

- Keep YAGNI: Don't add features not in Phase 1 scope
- Consistent styling with existing pages (library, manga detail)
- Simple Alpine.js state management (no complex state library needed)
- Inline errors preferred over toasts (clearer connection to input)
- Immediate removal on success (shows progress, keeps list focused)
- No authentication needed (single-user system)

---

**Design Approved:** 2026-02-05
**Ready for Implementation:** Yes
**Estimated Effort:** 3-4 hours (backend endpoint + frontend page + testing)
