# MangaTaro Developer Guide

Technical guide for extending and maintaining MangaTaro.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Critical Concepts](#critical-concepts)
- [Plugin Development](#plugin-development)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Development Workflow](#development-workflow)
- [Contributing](#contributing)

---

## Architecture Overview

### System Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐    ┌──────────────┐
│ Astro (SSR) │───→│   FastAPI    │
│  Frontend   │    │   Backend    │
└─────────────┘    └──────┬───────┘
                          │ SQLAlchemy
                          ▼
                   ┌──────────────┐
                   │   MariaDB    │
                   └──────────────┘
                          ▲
                          │
                   ┌──────┴───────┐
                   │  Playwright  │
                   │   Plugins    │
                   └──────────────┘
```

### Component Breakdown

**Frontend (Astro + TailwindCSS + Alpine.js):**
- Server-side rendering for performance
- Island architecture (minimal JavaScript)
- Pages: Homepage, Library, Manga detail, Admin
- Located: `frontend/src/`

**Backend (FastAPI + SQLAlchemy):**
- Async REST API
- Routers: `manga.py`, `scanlators.py`, `tracking.py`
- Services: TrackerService, NotificationService
- OpenAPI docs at `/docs`
- Located: `api/`

**Database (MariaDB):**
- Tables: mangas, scanlators, manga_scanlator, chapters
- Many-to-many: manga ↔ scanlator
- Located: `scripts/create_db.sql`

**Scraping (Playwright + Plugins):**
- BaseScanlator abstract class
- Plugin auto-discovery by class name
- Headless browser automation
- Located: `scanlators/`

### Tech Stack Rationale

**Why FastAPI?**
- Native async/await support for Playwright
- Auto-generated OpenAPI documentation
- Type safety with Pydantic
- Excellent performance for I/O-bound operations

**Why Astro?**
- Fast server-side rendering
- Minimal JavaScript shipped to client
- Great developer experience
- TailwindCSS integration

**Why Playwright?**
- Modern browser automation (better than Selenium)
- Native async support
- Reliable handling of dynamic content
- Cross-browser support

**Why MariaDB?**
- Proven reliability
- Excellent JSON support
- UTF-8 unicode for manga titles
- Easy backup and migration

### Directory Structure

```
mangataro/
├── api/                  # FastAPI backend
│   ├── routers/          # API endpoints
│   │   ├── manga.py
│   │   ├── scanlators.py
│   │   └── tracking.py
│   ├── services/         # Business logic
│   │   ├── tracker_service.py
│   │   └── notification_service.py
│   ├── models.py         # SQLAlchemy ORM
│   ├── schemas.py        # Pydantic validation
│   ├── database.py       # DB connection
│   └── main.py           # FastAPI app
├── frontend/             # Astro frontend
│   └── src/
│       ├── pages/        # Route pages
│       ├── components/   # Reusable components
│       ├── layouts/      # Page layouts
│       └── lib/          # API client, utils
├── scanlators/           # Plugin system
│   ├── base.py           # Abstract base class
│   ├── template.py       # Plugin template
│   ├── asura_scans.py    # Example plugin
│   └── raven_scans.py    # Example plugin
├── scripts/              # CLI utilities
├── data/                 # Data storage
│   └── img/              # Cover images
├── logs/                 # Log files
└── docs/                 # Documentation
```

---

## Critical Concepts

### 1. Spanish vs English Field Names

⚠️ **CRITICAL:** Plugin interface uses Spanish, database uses English.

**Why?** The first plugin (AsuraScans) served Spanish-speaking users, so the plugin interface was designed in Spanish. This must be maintained for consistency.

**Plugin API (Spanish):**
```python
# Plugins return:
{
    "numero": "42",           # Chapter number
    "titulo": "Chapter 42",   # Chapter title
    "url": "https://...",
    "fecha": datetime(...)    # Release date
}
```

**Database Schema (English):**
```python
# Database stores:
Chapter(
    chapter_number="42",      # Maps from "numero"
    title="Chapter 42",       # Maps from "titulo"
    url="https://...",
    release_date=datetime()   # Maps from "fecha"
)
```

**Where This Matters:**

`api/services/tracker_service.py` lines 214-228 contains the field mapping logic:

```python
# Field mapping: Spanish (plugin) → English (database)
chapter = models.Chapter(
    manga_scanlator_id=mapping.id,
    chapter_number=cap["numero"],      # Spanish → English
    title=cap["titulo"],                # Spanish → English
    url=cap["url"],
    release_date=cap["fecha"],          # Spanish → English
    detected_date=datetime.now()
)
```

### 2. Scanlator name vs class_name

⚠️ **CRITICAL PITFALL:** The `scanlators` table has TWO name fields that are often confused.

```sql
-- scanlators table
id | name          | class_name
7  | Asura Scans   | AsuraScans
32 | Raven Scans   | RavenScans
```

- **`name`** - Display name for UI ("Asura Scans")
- **`class_name`** - Python class name for plugin lookup ("AsuraScans")

**Always use `class_name` for plugin discovery!**

✅ **Correct:**
```python
scanlator = db.query(models.Scanlator).filter_by(id=7).first()
plugin_class = get_scanlator_by_name(scanlator.class_name)  # "AsuraScans"
plugin = plugin_class(page)
```

❌ **Wrong (returns None):**
```python
scanlator = db.query(models.Scanlator).filter_by(id=7).first()
plugin_class = get_scanlator_by_name(scanlator.name)  # "Asura Scans" - Returns None!
plugin = plugin_class(page)  # TypeError: 'NoneType' object is not callable
```

**This is documented in CLAUDE.md as a recurring pitfall!**

### 3. Async Everywhere

The entire system is async - **never mix sync and async**:

- FastAPI endpoints: `async def`
- Services: `async/await`
- Scanlator plugins: `async def` methods (except `parsear_numero_capitulo`)
- Playwright: `async_playwright()`

❌ **Wrong:**
```python
async def track_chapters():
    time.sleep(5)  # BLOCKS EVENT LOOP!
```

✅ **Correct:**
```python
async def track_chapters():
    await asyncio.sleep(5)  # NON-BLOCKING
```

### 4. Singleton Service Pattern

Services use singleton pattern to maintain state across requests:

```python
# api/services/tracker_service.py
_tracker_service = TrackerService()

def get_tracker_service() -> TrackerService:
    return _tracker_service
```

**Why?**
- TrackerService maintains job dictionary
- One instance per application
- Shared state for background jobs

### 5. Plugin Instantiation

⚠️ **Plugins REQUIRE Playwright page in constructor:**

✅ **Correct:**
```python
page = await browser.new_page()
plugin = AsuraScans(page)
chapters = await plugin.obtener_capitulos(url)
await page.close()
```

❌ **Wrong (crashes):**
```python
plugin = AsuraScans()  # TypeError - missing required argument 'playwright_page'
```

---

## Plugin Development

### Plugin Architecture

All plugins inherit from `BaseScanlator` abstract class:

```python
from playwright.async_api import Page
from scanlators.base import BaseScanlator
from datetime import datetime
from abc import ABC, abstractmethod

class BaseScanlator(ABC):
    def __init__(self, playwright_page: Page):
        self.page = playwright_page
        self.name = "Override this"
        self.base_url = "Override this"

    @abstractmethod
    async def buscar_manga(self, titulo: str) -> list[dict]:
        """Search for manga by title
        Returns: list of {"titulo", "url", "portada"}
        """
        pass

    @abstractmethod
    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """Get all chapters from manga page
        Returns: list of {"numero", "titulo", "url", "fecha"}
        """
        pass

    @abstractmethod
    def parsear_numero_capitulo(self, texto: str) -> str:
        """Parse chapter number from text
        Returns: chapter number as string (e.g., "42", "42.5")
        """
        pass
```

### Return Formats

**`buscar_manga()` returns:**
```python
[
    {
        "titulo": "Manga Title",
        "url": "https://scanlator.com/series/manga-title",
        "portada": "https://scanlator.com/covers/manga.jpg"
    },
    ...
]
```

**`obtener_capitulos()` returns:**
```python
[
    {
        "numero": "42",                      # Chapter number as string
        "titulo": "Chapter 42: The Battle",  # Chapter title
        "url": "https://scanlator.com/manga/chapter-42",
        "fecha": datetime(2025, 1, 15)       # Release date
    },
    ...
]
```

### Creating a New Plugin

**Quick start:** See [PLUGIN_QUICK_REFERENCE.md](PLUGIN_QUICK_REFERENCE.md) for step-by-step guide.

**Detailed steps:**

1. **Copy template:**
   ```bash
   cp scanlators/template.py scanlators/newsite.py
   ```

2. **Implement required methods:**
   - `buscar_manga()` - Search functionality
   - `obtener_capitulos()` - Chapter extraction
   - `parsear_numero_capitulo()` - Chapter number parsing

3. **Test the plugin:**
   ```bash
   python scripts/test_newsite.py --visible
   ```

4. **Add to database:**
   ```sql
   INSERT INTO scanlators (name, base_url, class_name, active)
   VALUES ('New Site', 'https://newsite.com', 'NewSite', 1);
   ```

### Plugin Examples

**AsuraScans** (`scanlators/asura_scans.py`):
- Modern site with predictable structure
- Chapters in `.chapterlist .eph-num a` selectors
- Date format: "January 15, 2025"
- Simple chapter number parsing

**RavenScans** (`scanlators/raven_scans.py`):
- JavaScript-rendered content
- Waits for `.chbox` selector
- Handles relative dates
- Important: `.first` is property not async method

### Common Patterns

**Date Parsing:**
```python
def _parse_date(self, texto: str) -> datetime:
    """Parse date from scanlator format"""
    try:
        return datetime.strptime(texto.strip(), "%B %d, %Y")
    except:
        return datetime.now()
```

**Chapter Number Extraction:**
```python
def parsear_numero_capitulo(self, texto: str) -> str:
    """Extract chapter number"""
    match = re.search(r'chapter\s*(\d+(?:\.\d+)?)', texto, re.I)
    return match.group(1) if match else "0"
```

**Handling Pagination:**
```python
async def obtener_capitulos(self, manga_url: str) -> list[dict]:
    capitulos = []
    page_num = 1

    while True:
        url = f"{manga_url}?page={page_num}"
        if not await self.safe_goto(url):
            break

        items = await self.page.locator(".chapter").all()
        if not items:
            break

        # Extract chapters...
        page_num += 1
        if page_num > 50:  # Safety limit
            break

    return capitulos
```

---

## API Reference

### Base URL

- **Development:** `http://localhost:8008`
- **Authentication:** None (local use)
- **OpenAPI Docs:** `http://localhost:8008/docs`

### Manga Endpoints

#### GET /api/manga/

List all manga with optional filters.

**Query Parameters:**
- `limit` (int): Max results (default 100)
- `offset` (int): Pagination offset (default 0)
- `status` (str): Filter by reading status

**Response: 200 OK**
```json
[
    {
        "id": 1,
        "title": "Solo Leveling",
        "alternative_titles": "나 혼자만 레벨업",
        "cover_url": "http://localhost:8008/static/covers/1.jpg",
        "description": "...",
        "status": "reading"
    }
]
```

#### GET /api/manga/{id}

Get manga details with scanlators and chapter counts.

**Response: 200 OK**
```json
{
    "id": 1,
    "title": "Solo Leveling",
    "alternative_titles": "나 혼자만 레벨업",
    "scanlators": [
        {
            "id": 7,
            "name": "Asura Scans",
            "manga_url": "https://asuracomic.net/series/solo-leveling",
            "chapter_count": 150
        }
    ]
}
```

#### POST /api/manga/with-scanlator

Create manga with scanlator mapping atomically.

**Request Body:**
```json
{
    "title": "New Manga",
    "alternative_titles": "Alt titles, comma separated",
    "scanlator_id": 7,
    "scanlator_manga_url": "https://asuracomic.net/series/new-manga",
    "cover_url": "https://example.com/cover.jpg",
    "cover_filename": ""
}
```

**Response: 201 Created**
```json
{
    "id": 95,
    "title": "New Manga",
    ...
}
```

**Errors:**
- `400` - Duplicate manga title
- `400` - Duplicate scanlator URL
- `400` - URL validation failed (plugin couldn't scrape)

### Chapter Endpoints

#### GET /api/chapters/

List chapters with filters.

**Query Parameters:**
- `manga_id` (int): Filter by manga
- `read` (bool): Filter by read status
- `limit` (int): Max results
- `offset` (int): Pagination

**Response: 200 OK**
```json
[
    {
        "id": 1,
        "manga_id": 1,
        "chapter_number": "42",
        "title": "The Great Battle",
        "url": "https://...",
        "release_date": "2025-01-15T00:00:00",
        "detected_date": "2025-01-15T12:30:00",
        "read": false
    }
]
```

#### PATCH /api/chapters/{id}

Update chapter (mark as read/unread).

**Request Body:**
```json
{
    "read": true
}
```

**Response: 200 OK**
```json
{
    "id": 1,
    "read": true,
    ...
}
```

### Tracking Endpoints

#### POST /api/tracking/trigger

Trigger background tracking job.

**Request Body:**
```json
{
    "notify": true  // Optional: send Discord notification
}
```

**Response: 202 Accepted**
```json
{
    "job_id": "abc123",
    "status": "running",
    "started_at": "2025-01-15T12:00:00"
}
```

#### GET /api/tracking/jobs/{job_id}

Get tracking job status.

**Response: 200 OK**
```json
{
    "job_id": "abc123",
    "status": "completed",  // running, completed, failed
    "started_at": "2025-01-15T12:00:00",
    "completed_at": "2025-01-15T12:05:00",
    "result": {
        "tracked": 15,
        "new_chapters": 3,
        "errors": 0
    }
}
```

#### GET /api/tracking/jobs

List recent tracking jobs.

**Response: 200 OK**
```json
[
    {
        "job_id": "abc123",
        "status": "completed",
        ...
    }
]
```

### Scanlator Endpoints

#### GET /api/scanlators/

List all scanlators.

**Response: 200 OK**
```json
[
    {
        "id": 7,
        "name": "Asura Scans",
        "class_name": "AsuraScans",
        "base_url": "https://asuracomic.net",
        "active": true
    }
]
```

#### POST /api/scanlators/

Create new scanlator.

**Request Body:**
```json
{
    "name": "New Scanlator",
    "class_name": "NewScanlator",
    "base_url": "https://newscanlator.com",
    "active": true
}
```

**Response: 201 Created**

---

## Database Schema

### Tables Overview

```sql
mangas
├── id (PK)
├── title
├── alternative_titles
├── cover_url
├── description
└── status

scanlators
├── id (PK)
├── name              -- Display name (UI)
├── class_name        -- Plugin class name (CODE)
├── base_url
└── active

manga_scanlator (join table)
├── id (PK)
├── manga_id (FK → mangas)
├── scanlator_id (FK → scanlators)
├── scanlator_manga_url
└── manually_verified  -- Must be true for tracking!

chapters
├── id (PK)
├── manga_scanlator_id (FK → manga_scanlator)
├── chapter_number
├── title
├── url
├── release_date       -- When scanlator posted
├── detected_date      -- When we discovered it
└── read               -- User read status
```

### Key Relationships

- **Many-to-many:** Manga ↔ Scanlator (via `manga_scanlator`)
- **Chapters** belong to manga_scanlator pair (not directly to manga)
- One manga can have multiple scanlators
- One scanlator can track multiple manga

### Important Fields

**`scanlators.class_name`:**
- Must match Python class name exactly!
- Example: "AsuraScans" (not "asurascans" or "Asura Scans")
- Used for plugin discovery

**`manga_scanlator.manually_verified`:**
- Must be `1` for tracking to process
- Set to `0` by default (safety measure)
- Update to `1` after confirming URL is correct

**`chapters.chapter_number`:**
- Stored as string (not float)
- Supports formats: "42", "42.5", "42.1"
- Allows natural sorting

---

## Development Workflow

### Running Tests

```bash
# API tests
pytest api/tests/

# Plugin tests
python scripts/test_asura_scans.py

# Integration tests
python scripts/test_tracking.py
```

### Adding New API Endpoints

1. **Add Pydantic schema** to `api/schemas.py`:
   ```python
   class NewFeatureRequest(BaseModel):
       param: str

   class NewFeatureResponse(BaseModel):
       result: str
   ```

2. **Add endpoint** to appropriate router:
   ```python
   @router.post("/new-feature", response_model=schemas.NewFeatureResponse)
   async def new_feature(
       request: schemas.NewFeatureRequest,
       db: Session = Depends(get_db)
   ):
       # Implementation
       return {"result": "success"}
   ```

3. **Test with curl:**
   ```bash
   curl -X POST http://localhost:8008/api/path/new-feature \
     -H "Content-Type: application/json" \
     -d '{"param": "value"}'
   ```

4. **Update frontend API client** in `frontend/src/lib/api.ts`:
   ```typescript
   export async function newFeature(param: string) {
       const response = await fetch(`${API_URL}/path/new-feature`, {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ param })
       });
       return response.json();
   }
   ```

### Modifying Frontend Pages

1. **Edit page** in `frontend/src/pages/`
2. **Use Astro for SSR, Alpine.js for interactivity**
3. **Call API via fetch() or API client**
4. **Test with:** `cd frontend && npm run dev`

### Database Migrations

```bash
# Create backup first!
mysqldump -u mangataro_user -p mangataro > backup.sql

# Make schema changes
mysql -u mangataro_user -p mangataro < migration.sql

# Update models.py to match new schema
```

---

## Contributing

### Code Style

**Python:**
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

**TypeScript:**
- Functions: `camelCase`
- Components: `PascalCase`

**Astro:**
- Components: `PascalCase.astro`

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-scanlator

# Make changes, test locally

# Commit with descriptive message
git commit -m "feat: add NewScanlator plugin

- Support for https://newscanlator.com/
- Handles pagination with 50 chapters per page
- Successfully tested with 5 manga

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Testing Requirements

- **Plugins:** Test with `--visible` first, then headless
- **API:** Test with curl or Swagger UI (`/docs`)
- **Frontend:** Manual browser testing
- **Integration:** Run full tracking with `--limit 1`

---

## Additional Resources

- **CLAUDE.md** - Comprehensive guide for AI assistants (includes all critical information)
- **PLUGIN_QUICK_REFERENCE.md** - One-page cheat sheet for plugins
- **User Guide** - End-user documentation
- **Getting Started** - Installation and setup

For questions about architecture or design decisions, consult CLAUDE.md first!
