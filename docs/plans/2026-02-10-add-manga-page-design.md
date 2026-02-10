# Add Manga Page - Design Document

**Date:** 2026-02-10
**Status:** Ready for Implementation
**Feature:** Admin page to add new manga with scanlator mapping

---

## Overview

Create a new admin page at `/admin/add-manga` that allows users to add new manga to their library with an associated scanlator mapping in a single atomic operation. The page will validate the scanlator URL by actually attempting to scrape it, download the cover image, and create both the manga entry and verified scanlator mapping.

---

## User Requirements

**What the user wants to provide:**
- Manga title (required)
- Alternative titles (optional)
- Scanlator selection from existing scanlators (required)
- URL to the manga on the scanlator's website (required)
- URL to cover image (required)
- Cover image filename as fallback if download fails (optional)

**User's preferences:**
- Cover images should be downloaded and stored locally
- Manual filename fallback if download fails (captcha, etc.)
- Full URL validation by actually scraping the page
- After success, redirect to the new manga's detail page

---

## Design Decisions

### 1. Cover Image Handling
**Decision:** Download from URL with manual fallback

- **Primary:** Download image from provided URL and store in `/data/mangataro/data/img/`
- **Fallback:** If download fails, user can provide a filename for an image already stored locally
- **Implementation:** Use existing `download_image()` utility from `api/utils.py`

### 2. Workflow
**Decision:** Atomic creation (manga + mapping in one action)

- Single form submission creates both manga and manga_scanlator mapping
- Sets `manually_verified=true` on the mapping for immediate tracking
- All-or-nothing transaction - if any step fails, rollback everything

### 3. Success Flow
**Decision:** Redirect to manga detail page

- After successful creation, redirect to `/manga/{id}`
- Shows the newly created manga with its cover and scanlator mapping
- User can immediately trigger tracking if desired

### 4. URL Validation
**Decision:** Full validation with scraping

- Backend actually attempts to scrape the URL using the scanlator plugin
- Confirms the manga page exists and can be accessed
- Takes 2-5 seconds but guarantees tracking will work
- Fail fast - validation happens before database writes

### 5. Validation UX
**Decision:** Validate on form submit

- User fills entire form and clicks "Add Manga"
- Shows loading spinner: "Validating URL and creating manga..."
- Clear loading state with single validation step
- On error, shows message and allows user to fix

---

## Architecture

### API Flow

```
1. Frontend submits form data
   ↓
2. Backend validates scanlator URL (Playwright + plugin)
   ↓
3. If valid, download cover image
   ↓
4. Create manga entry in database
   ↓
5. Create manga_scanlator mapping (manually_verified=true)
   ↓
6. Return manga ID
   ↓
7. Frontend redirects to /manga/{id}
```

### Error Handling

- **400:** Invalid URL format or scanlator mismatch
- **422:** URL validation failed (can't fetch/scrape the page)
- **500:** Cover download failed AND no fallback filename provided
- **Rollback:** Any error rolls back entire transaction

---

## Implementation Details

### Backend Changes

**File:** `api/schemas.py`

New schema for atomic creation:
```python
class MangaWithScanlatorCreate(BaseModel):
    """Schema for creating manga with scanlator mapping atomically"""
    title: str
    alternative_titles: Optional[str] = None
    scanlator_id: int
    scanlator_manga_url: str
    cover_url: str
    cover_filename: Optional[str] = None  # fallback if download fails
    status: MangaStatus = MangaStatus.reading
```

**File:** `api/routers/manga.py`

New endpoint:
```python
@router.post("/with-scanlator", response_model=schemas.MangaResponse, status_code=201)
async def create_manga_with_scanlator(
    manga_data: schemas.MangaWithScanlatorCreate,
    db: Session = Depends(get_db)
):
    """
    Create manga with scanlator mapping atomically.

    Validates URL by actually scraping, downloads cover,
    creates manga and mapping in single transaction.
    """
```

**Validation Logic:**
1. Verify scanlator exists in database
2. Check URL starts with scanlator's base_url
3. Instantiate scanlator plugin with Playwright
4. Call `plugin.obtener_capitulos(url)` - if succeeds, URL is valid
5. Close Playwright browser

**Cover Download Logic:**
1. Try `download_image(manga_data.cover_url, /data/mangataro/data/img/)`
2. If succeeds: use returned filename
3. If fails: use `manga_data.cover_filename` if provided, else raise 500

**Database Transaction:**
```python
# Create manga
db_manga = models.Manga(
    title=manga_data.title,
    alternative_titles=manga_data.alternative_titles,
    cover_filename=cover_filename,
    status=manga_data.status,
    date_added=datetime.utcnow()
)
db.add(db_manga)
db.flush()  # Get manga.id

# Create mapping
db_mapping = models.MangaScanlator(
    manga_id=db_manga.id,
    scanlator_id=manga_data.scanlator_id,
    scanlator_manga_url=manga_data.scanlator_manga_url,
    manually_verified=True
)
db.add(db_mapping)
db.commit()
```

### Frontend Changes

**File:** `frontend/src/pages/admin/add-manga.astro`

New page with form:

**Form Fields:**
1. Manga Title (required) - text input
2. Alternative Titles (optional) - text input, helper: "Separate with / or commas"
3. Scanlator (required) - dropdown populated from API
4. Scanlator URL (required) - text input, placeholder shows base_url
5. Cover Image URL (required) - text input
6. Cover Filename Fallback (optional) - text input

**Alpine.js State:**
```javascript
{
  loading: false,
  error: null,
  formData: {
    title: '',
    alternative_titles: '',
    scanlator_id: null,
    scanlator_url: '',
    cover_url: '',
    cover_filename: ''
  }
}
```

**Submit Handler:**
```javascript
async submitForm() {
  this.loading = true;
  this.error = null;

  try {
    const response = await fetch('/api/manga/with-scanlator', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.formData)
    });

    if (!response.ok) {
      const error = await response.json();
      this.error = error.detail;
      return;
    }

    const manga = await response.json();
    window.location.href = `/manga/${manga.id}`;
  } catch (err) {
    this.error = 'Failed to create manga';
  } finally {
    this.loading = false;
  }
}
```

**Visual Design:**
- Similar style to `map-sources.astro` for consistency
- Centered card with max-width
- Back button to library
- Clear field labels with helper text
- Loading spinner with message during validation
- Error messages displayed inline above form

**File:** `frontend/src/components/Navigation.astro`

Add navigation link:
```astro
<a href="/admin/add-manga">Add Manga</a>
```

**File:** `frontend/src/lib/api.ts`

Add API client method:
```typescript
export async function createMangaWithScanlator(data: {
  title: string;
  alternative_titles?: string;
  scanlator_id: number;
  scanlator_manga_url: string;
  cover_url: string;
  cover_filename?: string;
}): Promise<Manga> {
  const response = await fetch(`${API_URL}/manga/with-scanlator`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create manga');
  }

  return response.json();
}
```

---

## Testing Strategy

### Test Cases

1. **Happy Path**
   - Valid manga with downloadable cover
   - Should create manga, download image, create mapping
   - Redirect to manga detail page

2. **URL Validation Failure**
   - Invalid scanlator URL (404, wrong site, etc.)
   - Should show error without creating anything
   - No database changes

3. **Cover Download Failure with Fallback**
   - Cover URL fails but filename provided
   - Should create manga with fallback filename
   - Success despite download failure

4. **Cover Download Failure without Fallback**
   - Cover URL fails, no filename provided
   - Should show error
   - No database changes (rollback)

5. **Duplicate Title**
   - Manga with same title already exists
   - Should show error
   - No duplicate created

### Manual Testing

1. Add manga "Solo Leveling" with AsuraScans URL
2. Verify cover image downloads to `/data/mangataro/data/img/`
3. Check database shows manga with `manually_verified=true` mapping
4. Confirm redirect to manga detail page
5. Verify manga appears in library

---

## Additional Considerations

### Logging
Use centralized Loguru logging:
- Log validation attempts (success/failure)
- Log cover download attempts
- Log database transaction commits/rollbacks
- Use api logger: `logger = get_logger("api")`

### Duplicate Prevention
Check if manga with same title exists:
```python
existing = db.query(models.Manga).filter(
    models.Manga.title == manga_data.title
).first()

if existing:
    raise HTTPException(
        status_code=400,
        detail=f"Manga '{manga_data.title}' already exists"
    )
```

### Default Values
- `status`: Defaults to `MangaStatus.reading`
- `date_added`: Set to `datetime.utcnow()`
- `manually_verified`: Always `True` for user-added mappings

### Future Enhancements
- Add "Test URL" button for pre-validation (optional)
- Allow multiple scanlator mappings in one form
- Auto-populate title from scraped page
- Image preview before submission

---

## Files to Modify

### Backend
1. `api/schemas.py` - Add `MangaWithScanlatorCreate` schema
2. `api/routers/manga.py` - Add `POST /with-scanlator` endpoint

### Frontend
3. `frontend/src/pages/admin/add-manga.astro` - New page (CREATE)
4. `frontend/src/components/Navigation.astro` - Add navigation link
5. `frontend/src/lib/api.ts` - Add `createMangaWithScanlator()` method

### Documentation
6. Update `docs/USER_GUIDE.md` - Document new page
7. Update `README.md` - Add to features list if needed

---

## Summary

**What:** Admin page to add new manga with scanlator mapping
**Why:** Easier than manual database/API operations
**How:** Single form → validate URL → download cover → atomic DB transaction

**Benefits:**
- User-friendly interface for adding manga
- Validates URLs before creating entries
- Downloads and stores cover images locally
- Ensures tracking will work (verified mapping)
- Single atomic operation (no partial failures)

**Trade-offs:**
- Validation takes 2-5 seconds (acceptable for better UX)
- Requires Playwright for validation (already available)
- More complex than simple form (worth it for robustness)

---

**Design approved by:** User
**Ready for implementation:** Yes
**Next steps:** Create implementation plan and begin development
