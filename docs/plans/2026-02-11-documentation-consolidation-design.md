# Documentation Consolidation Design

**Date:** 2026-02-11
**Status:** Design Complete - Ready for Implementation
**Goal:** Consolidate 15+ scattered documentation files into 5 focused, visually engaging guides

---

## Problem Statement

MangaTaro currently has too many documentation files (15+) scattered across root and docs/ directory:
- Duplicate information across multiple files
- Unclear entry points for users vs developers
- Historical/legacy content mixed with current docs
- No visual elements to engage readers
- Navigation requires reading multiple files

**User Request:** "Consolidate them. Remove duplicates. Clear, precise, and engaging. Not too many files. Perhaps a main one with links?"

---

## Solution: Hub-and-Spoke Documentation Model

### Target Structure (15 files → 5 files)

```
MangaTaro/
├── README.md                           # Quick-action landing page
└── docs/
    ├── GETTING_STARTED.md              # Install → Run → Deploy
    ├── USER_GUIDE.md                   # Daily operations
    ├── DEVELOPER_GUIDE.md              # Architecture + Plugins + API
    ├── PLUGIN_QUICK_REFERENCE.md       # One-page cheat sheet
    └── images/                         # Screenshots
        ├── homepage_updates.png
        ├── library-grid.png
        ├── manga-detail.png
        ├── add-manga-empty.png
        └── map-sources.png
```

### Design Principles

1. **Quick Action Focus** - Get users running fast, prove value immediately
2. **Visual Engagement** - Screenshots and diagrams throughout
3. **Clear Separation** - User docs vs Developer docs
4. **No Redundancy** - Each piece of information lives in exactly one place
5. **Progressive Disclosure** - Surface basics first, link to details

---

## Detailed File Specifications

### 1. README.md - Quick Action Landing Page

**Purpose:** Hook users in 30 seconds, get them running in 5 minutes

**Structure:**

```markdown
# MangaTaro

Self-hosted manga chapter tracker. Automatically monitors scanlation sites and shows you new chapters.

![Homepage Updates](docs/images/homepage_updates.png)

## Quick Start

```bash
cp .env.example .env
# Edit .env with your database credentials
pip install -r requirements.txt && cd frontend && npm install
uvicorn api.main:app --reload &
cd frontend && npm run dev
```

Visit: http://localhost:4343

## Features

- 📚 **Track Manga Across Scanlators** - Monitor multiple sources for each manga
- 🔍 **Automatic Chapter Detection** - Background jobs fetch new chapters
- 🌐 **Modern Web Interface** - Clean UI built with Astro + TailwindCSS
- 🔔 **Discord Notifications** - Get notified when new chapters drop
- 🧩 **Extensible Plugin System** - Add new scanlators in minutes

## Screenshots

| Updates Feed | Library Grid | Manga Detail |
|--------------|--------------|--------------|
| ![Updates](docs/images/homepage_updates.png) | ![Library](docs/images/library-grid.png) | ![Detail](docs/images/manga-detail.png) |

## Documentation

**For Users:**
- 📖 [Getting Started](docs/GETTING_STARTED.md) - Installation and setup
- 👤 [User Guide](docs/USER_GUIDE.md) - Daily operations

**For Developers:**
- 🛠️ [Developer Guide](docs/DEVELOPER_GUIDE.md) - Architecture and API
- ⚡ [Plugin Quick Reference](docs/PLUGIN_QUICK_REFERENCE.md) - Add scanlators fast

## Tech Stack

FastAPI • Astro • Playwright • MariaDB

## Status

✅ Production Ready - Tracking 90+ manga across multiple scanlators

## License

MIT
```

**Key Features:**
- Hero screenshot immediately shows what it does
- 4 commands to get running (no fluff)
- Feature list with emoji icons for scannability
- Three-screenshot gallery showing key pages
- Clear navigation to user vs developer docs
- Concise tech stack and status

---

### 2. docs/GETTING_STARTED.md - Installation to Production

**Purpose:** Take user from zero to fully operational system

**Consolidates:**
- docs/SETUP.md
- docs/DEPLOYMENT.md
- docs/TRACKING_GUIDE.md
- docs/TRACKING_QUICK_START.md
- docs/SERVICE_MANAGEMENT.md

**Structure:**

#### Introduction
- "Get MangaTaro running in 15 minutes"
- What you'll accomplish: Install → First Run → Tracking → (Optional) Production

#### Table of Contents
- Prerequisites
- Installation
- First Run
- Adding Your First Manga
- Setting Up Tracking
- Production Deployment (Optional)
- Troubleshooting

#### Section 1: Prerequisites
- System requirements (Python 3.10+, Node 18+, MariaDB 10.6+)
- Verification commands for each requirement

#### Section 2: Installation
- Database creation and user setup
- Schema import: `mysql < scripts/create_db.sql`
- Python virtual environment
- Dependencies: `pip install -r requirements.txt`
- Playwright browsers: `playwright install chromium`
- Frontend dependencies: `cd frontend && npm install`
- Environment configuration (.env walkthrough)
  - Database credentials
  - API settings
  - CORS origins
  - Optional: Discord webhook

#### Section 3: First Run
- Starting API server: `uvicorn api.main:app --reload`
- Verification: `curl http://localhost:8008/health`
- Starting frontend: `cd frontend && npm run dev`
- Accessing UI: http://localhost:4343
- **Screenshot:** Expected homepage view

![Expected First Run](images/homepage_updates.png)

#### Section 4: Adding Your First Manga
- Navigate to http://localhost:4343/admin/add-manga
- **Screenshot:** Add manga form

![Add Manga Form](images/add-manga-empty.png)

- Form fields explained:
  - Title (required) - Manga name
  - Alternative titles (optional) - Comma-separated
  - Scanlator (required) - Must have plugin implemented
  - Scanlator URL (required) - Validated by plugin
  - Cover URL or filename (required) - Downloads or uses local
- Submit and verify chapters appear
- **Screenshot:** Manga detail page with chapters

![Manga Detail](images/manga-detail.png)

#### Section 5: Setting Up Tracking
- Manual test run: `python scripts/track_chapters.py --limit 1 --visible`
- What happens: Browser opens, scrapes chapters, saves to database
- Mapping more manga: http://localhost:4343/admin/map-sources
- **Screenshot:** Map sources interface

![Map Sources](images/map-sources.png)

- **Automation Option 1: n8n Workflow**
  - Import workflow: `n8n/workflows/scheduled_tracking.json`
  - Configure schedule (default: every 6 hours)
  - Enable workflow

- **Automation Option 2: Cron Job**
  ```bash
  # Add to crontab
  0 */6 * * * cd /data/mangataro && .venv/bin/python scripts/track_chapters.py
  ```

- Testing notifications:
  - Add Discord webhook to .env
  - Trigger tracking: `curl -X POST http://localhost:8008/api/tracking/trigger`
  - Check Discord for new chapter notification

#### Section 6: Production Deployment (Optional)
- **Systemd Services:**
  - API service: `/etc/systemd/system/mangataro-api.service`
  - Frontend service: `/etc/systemd/system/mangataro-frontend.service`
  - Enable auto-start: `systemctl enable mangataro-api mangataro-frontend`

- **Process Management:**
  ```bash
  # Start services
  sudo systemctl start mangataro-api mangataro-frontend

  # Check status
  sudo systemctl status mangataro-api

  # View logs
  sudo journalctl -u mangataro-api -f
  ```

- **Nginx Reverse Proxy (Optional):**
  - Configuration example for serving on port 80
  - SSL setup with Let's Encrypt

- **Security Considerations:**
  - Firewall rules
  - Database user permissions
  - Environment variable protection

#### Troubleshooting
- **Database connection errors:** Check credentials, MariaDB running
- **Playwright errors:** `playwright install-deps chromium`
- **Port conflicts:** Change ports in .env
- **Missing chapters:** Verify manga-scanlator mapping has `manually_verified=1`
- **Frontend can't connect to API:** Check CORS_ORIGINS in .env

---

### 3. docs/USER_GUIDE.md - Daily Operations

**Purpose:** How to use the web interface for tracking manga

**Consolidates:**
- Existing USER_GUIDE.md (streamlined and enhanced with screenshots)

**Structure:**

#### Introduction
- "Daily operations guide for MangaTaro"
- Prerequisites: System installed and running (see Getting Started)

#### Section 1: Web Interface Overview
- Navigation tour
- **Screenshot:** Annotated homepage showing navigation

#### Section 2: Checking for New Chapters
- Homepage updates feed walkthrough
- **Screenshot:** Homepage with annotations

![Homepage Updates](images/homepage_updates.png)

- Key elements explained:
  - Manga cover + title
  - Chapter number and title
  - Release date (when scanlator posted) vs detected date (when we found it)
  - "Mark as Read" button
  - Link to scanlator site
- Filtering updates (search, read/unread status)
- Sorting options

#### Section 3: Managing Your Library
- Library grid view
- **Screenshot:** Library grid

![Library Grid](images/library-grid.png)

- Browsing your collection
- Searching for specific manga
- Clicking through to manga details
- **Screenshot:** Manga detail page

![Manga Detail](images/manga-detail.png)

- Understanding chapter lists
- Bulk actions (mark all as read)

#### Section 4: Adding New Manga
- When to use /admin/add-manga vs /admin/map-sources
  - **add-manga:** Creating brand new manga entry + mapping
  - **map-sources:** Adding scanlator source to existing manga

- Using add-manga page:
- **Screenshot:** Add manga form

![Add Manga Form](images/add-manga-empty.png)

- Form walkthrough:
  - Title field (required, checked for duplicates)
  - Alternative titles (comma-separated, optional)
  - Scanlator dropdown (must have plugin)
  - Scanlator URL (validated against scanlator domain)
  - Cover URL or filename (downloads image or uses local)

- What happens on submit:
  - URL validated by actually scraping with plugin
  - Cover downloaded to data/img/
  - Manga and mapping created atomically
  - Redirects to manga detail page
  - First chapter tracking happens automatically

#### Section 5: Mapping Manga to Scanlators
- Using /admin/map-sources page
- **Screenshot:** Map sources interface

![Map Sources](images/map-sources.png)

- Selecting scanlator from dropdown
- Seeing unmapped manga for that scanlator
- Entering scanlator URL for each manga
- URL validation (must match scanlator domain)
- Success feedback (row fades out)
- Switching scanlators to map more manga

#### Section 6: Discord Notifications
- Setting up webhook URL in .env
- What notifications look like (example screenshot if available)
- Customizing notification behavior:
  - Enable/disable in .env: `NOTIFICATION_TYPE=discord`
  - Notification triggers (new chapters detected)

#### Section 7: Common Tasks
- **Marking chapters as read:**
  - Individual: Click "Mark as Read" button
  - Bulk: "Mark All Read" on manga detail page

- **Checking tracking status:**
  - API endpoint: `http://localhost:8008/api/tracking/jobs`
  - Recent tracking runs and results

- **Viewing logs:**
  - Log directory: `/data/mangataro/logs/`
  - Tracking logs: `track_chapters_*.log`
  - API logs: `journalctl -u mangataro-api`

#### Troubleshooting
- **Chapters not appearing:** Check manga-scanlator mapping verified
- **"Mark as Read" not working:** Check browser console, API running
- **Missing cover images:** Check data/img/ directory, file permissions
- **Tracking not running:** Check automation (n8n/cron), check logs

---

### 4. docs/DEVELOPER_GUIDE.md - Architecture & Extension

**Purpose:** Technical guide for maintaining and extending MangaTaro

**Consolidates:**
- Key sections from CLAUDE.md (but CLAUDE.md stays for AI assistants)
- ASURASCANS_PLUGIN_USAGE.md
- docs/API_GUIDE.md
- Plugin development concepts

**Structure:**

#### Introduction
- "Technical guide for extending MangaTaro"
- Target audience: Developers, future maintainers
- Prerequisites: Familiarity with Python, TypeScript, SQL

#### Section 1: Architecture Overview

**System Architecture Diagram:**
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐    ┌──────────────┐
│ Astro (SSR) │───→│ FastAPI      │
│ Frontend    │    │ Backend      │
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

**Component Breakdown:**
- **Frontend (Astro + TailwindCSS + Alpine.js):**
  - Server-side rendering for performance
  - Island architecture for interactivity
  - Pages: Homepage, Library, Manga detail, Admin pages

- **Backend (FastAPI + SQLAlchemy):**
  - Async REST API
  - Routers: manga, scanlators, tracking
  - Services: TrackerService, NotificationService
  - OpenAPI docs at /docs

- **Database (MariaDB):**
  - Tables: mangas, scanlators, manga_scanlator, chapters
  - Relationships: manga ←→ scanlator (many-to-many)

- **Scraping (Playwright + Plugins):**
  - BaseScanlator abstract class
  - Plugin auto-discovery
  - Headless browser automation

**Tech Stack Rationale:**
- **FastAPI:** Native async support for Playwright, auto-generated docs
- **Astro:** Fast SSR, minimal JavaScript, great DX
- **Playwright:** Modern browser automation, better than Selenium
- **MariaDB:** Proven reliability, excellent JSON support

**Directory Structure:**
```
mangataro/
├── api/              # FastAPI backend
│   ├── routers/      # API endpoints
│   ├── services/     # Business logic
│   ├── models.py     # SQLAlchemy ORM
│   └── schemas.py    # Pydantic validation
├── frontend/         # Astro frontend
│   └── src/
│       ├── pages/    # Route pages
│       ├── components/ # Reusable components
│       └── lib/      # API client, utils
├── scanlators/       # Plugin system
│   ├── base.py       # Abstract base class
│   └── *.py          # Plugin implementations
└── scripts/          # CLI utilities
```

#### Section 2: Critical Concepts

**2.1 Spanish vs English Field Names**

⚠️ **CRITICAL:** Plugin interface uses Spanish, database uses English.

**Plugin API (Spanish):**
```python
# Plugins return:
{
    "numero": "42",           # Chapter number
    "titulo": "Title",        # Chapter title
    "url": "https://...",
    "fecha": datetime()       # Release date
}
```

**Database Schema (English):**
```python
# Database stores:
Chapter(
    chapter_number="42",      # Maps from "numero"
    title="Title",            # Maps from "titulo"
    url="https://...",
    release_date=datetime()   # Maps from "fecha"
)
```

**Why?** First plugin (AsuraScans) served Spanish-speaking users, so interface was designed in Spanish. Maintained for consistency.

**Where it matters:** `api/services/tracker_service.py` lines 214-228 (field mapping logic)

**2.2 Scanlator name vs class_name**

⚠️ **CRITICAL PITFALL:** Database has two name fields that are often confused.

```python
# scanlators table
id | name          | class_name
7  | Asura Scans   | AsuraScans
```

- **name:** Display name for UI ("Asura Scans")
- **class_name:** Python class name for plugin lookup ("AsuraScans")

**Always use class_name for plugin discovery:**

✅ **Correct:**
```python
plugin_class = get_scanlator_by_name(scanlator.class_name)
plugin = plugin_class(page)
```

❌ **Wrong (returns None):**
```python
plugin_class = get_scanlator_by_name(scanlator.name)  # Returns None!
plugin = plugin_class(page)  # TypeError: 'NoneType' object is not callable
```

**2.3 Async Everywhere**

Everything is async - never mix sync and async:
- FastAPI endpoints: `async def`
- Services: `async/await`
- Scanlator plugins: `async def` (except parsear_numero_capitulo)
- Playwright: `async_playwright()`

**2.4 Singleton Service Pattern**

Services use singleton pattern to maintain state:

```python
# api/services/tracker_service.py
_tracker_service = TrackerService()

def get_tracker_service() -> TrackerService:
    return _tracker_service
```

**Why?** TrackerService maintains job dictionary across requests.

**2.5 Plugin Instantiation**

⚠️ **Plugins require Playwright page in constructor:**

✅ **Correct:**
```python
page = await browser.new_page()
plugin = AsuraScans(page)
chapters = await plugin.obtener_capitulos(url)
await page.close()
```

❌ **Wrong (crashes):**
```python
plugin = AsuraScans()  # TypeError - missing required argument!
```

#### Section 3: Plugin Development

**3.1 Plugin Architecture**

All plugins inherit from `BaseScanlator` abstract class:

```python
from playwright.async_api import Page
from scanlators.base import BaseScanlator

class BaseScanlator(ABC):
    def __init__(self, playwright_page: Page):
        self.page = playwright_page
        self.name = "Override this"
        self.base_url = "Override this"

    @abstractmethod
    async def buscar_manga(self, titulo: str) -> list[dict]:
        """Search for manga by title"""
        pass

    @abstractmethod
    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """Get all chapters from manga page"""
        pass

    @abstractmethod
    def parsear_numero_capitulo(self, texto: str) -> str:
        """Parse chapter number from text"""
        pass
```

**Return formats (Spanish field names!):**

`buscar_manga()` returns:
```python
[
    {
        "titulo": "Manga Title",
        "url": "https://...",
        "portada": "https://.../cover.jpg"
    }
]
```

`obtener_capitulos()` returns:
```python
[
    {
        "numero": "42",           # Chapter number as string
        "titulo": "Chapter 42: Title",
        "url": "https://.../chapter-42",
        "fecha": datetime(2025, 1, 15)
    }
]
```

**3.2 Creating a New Plugin**

See [Plugin Quick Reference](PLUGIN_QUICK_REFERENCE.md) for step-by-step guide.

**3.3 Plugin Examples**

**AsuraScans Implementation:**
- Modern site with predictable structure
- Chapters in `.chapterlist .eph-num a` selectors
- Date format: "January 15, 2025"
- Simple chapter number parsing: `re.search(r'chapter\s*(\d+)', text, re.I)`

**RavenScans Implementation:**
- JavaScript-rendered content
- Must wait for `.chbox` selector before scraping
- Chapters in `.eph-num a` links
- Date format: "September 11, 2025"
- Important: `.first` is property not async method

**Common Patterns:**

**Date Parsing:**
```python
def _parse_date(self, texto: str) -> datetime:
    """Parse date from scanlator-specific format"""
    try:
        # Example: "January 15, 2025"
        return datetime.strptime(texto.strip(), "%B %d, %Y")
    except:
        return datetime.now()
```

**Chapter Number Extraction:**
```python
def parsear_numero_capitulo(self, texto: str) -> str:
    """Extract chapter number from text"""
    # Match "Chapter 42" or "Ch. 42.5"
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

        # Scrape current page
        items = await self.page.locator(".chapter").all()
        if not items:
            break  # No more pages

        # Extract chapters...

        page_num += 1

    return capitulos
```

**3.4 Testing Plugins**

**Manual test:**
```bash
# Create test script
cat > scripts/test_newsite.py << 'EOF'
import asyncio
from playwright.async_api import async_playwright
from scanlators.newsite import NewSite

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        plugin = NewSite(page)

        # Test search
        results = await plugin.buscar_manga("solo leveling")
        print(f"Found {len(results)} manga")

        # Test chapter extraction
        if results:
            chapters = await plugin.obtener_capitulos(results[0]['url'])
            print(f"Found {len(chapters)} chapters")
            for ch in chapters[:5]:
                print(f"  Ch {ch['numero']}: {ch['titulo']}")

        await browser.close()

asyncio.run(main())
EOF

python scripts/test_newsite.py
```

**Integration test:**
```bash
# Add scanlator to database first
mysql -u mangataro_user -p mangataro << EOF
INSERT INTO scanlators (name, base_url, class_name, active)
VALUES ('New Site', 'https://newsite.com', 'NewSite', 1);
EOF

# Test tracking
python scripts/track_chapters.py --scanlator-id <id> --limit 1 --visible
```

#### Section 4: API Reference

**4.1 Base URL and Authentication**
- Base URL: `http://localhost:8008`
- Authentication: None (local use only)
- OpenAPI Docs: `http://localhost:8008/docs`
- Content-Type: `application/json`

**4.2 Manga Endpoints**

**GET /api/manga/**
```
List all manga with optional filters

Query Parameters:
- limit (int): Max results (default 100)
- offset (int): Pagination offset (default 0)
- status (str): Filter by reading status

Response: 200 OK
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

**GET /api/manga/{id}**
```
Get manga details with scanlators and chapter counts

Response: 200 OK
{
    "id": 1,
    "title": "Solo Leveling",
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

**POST /api/manga/with-scanlator**
```
Create manga with scanlator mapping atomically

Request Body:
{
    "title": "New Manga",
    "alternative_titles": "Alt titles, comma separated",
    "scanlator_id": 7,
    "scanlator_manga_url": "https://asuracomic.net/series/new-manga",
    "cover_url": "https://example.com/cover.jpg",
    "cover_filename": ""  // Optional: use local file instead
}

Response: 201 Created
{
    "id": 95,
    "title": "New Manga",
    ...
}

Errors:
- 400: Duplicate manga title
- 400: Duplicate scanlator URL
- 400: URL validation failed (plugin couldn't scrape)
```

**4.3 Chapter Endpoints**

**GET /api/chapters/**
```
List chapters with filters

Query Parameters:
- manga_id (int): Filter by manga
- read (bool): Filter by read status
- limit (int): Max results
- offset (int): Pagination

Response: 200 OK
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

**PATCH /api/chapters/{id}**
```
Update chapter (mark as read/unread)

Request Body:
{
    "read": true
}

Response: 200 OK
{
    "id": 1,
    "read": true,
    ...
}
```

**4.4 Tracking Endpoints**

**POST /api/tracking/trigger**
```
Trigger background tracking job

Request Body:
{
    "notify": true  // Optional: send Discord notification
}

Response: 202 Accepted
{
    "job_id": "abc123",
    "status": "running",
    "started_at": "2025-01-15T12:00:00"
}
```

**GET /api/tracking/jobs/{job_id}**
```
Get tracking job status

Response: 200 OK
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

**GET /api/tracking/jobs**
```
List recent tracking jobs

Response: 200 OK
[
    {
        "job_id": "abc123",
        "status": "completed",
        ...
    }
]
```

**4.5 Scanlator Endpoints**

**GET /api/scanlators/**
```
List all scanlators

Response: 200 OK
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

**POST /api/scanlators/**
```
Create new scanlator

Request Body:
{
    "name": "New Scanlator",
    "class_name": "NewScanlator",
    "base_url": "https://newscanlator.com",
    "active": true
}

Response: 201 Created
```

#### Section 5: Database Schema

**Tables Overview:**

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

**Key Relationships:**
- Many-to-many: Manga ←→ Scanlator (via manga_scanlator)
- Chapters belong to manga_scanlator pair (not directly to manga)

**Important Fields:**
- `scanlators.class_name` - Must match Python class name exactly!
- `manga_scanlator.manually_verified` - Must be 1 for tracking to process
- `chapters.chapter_number` - Stored as string to support "42.5", "42.1", etc.

#### Section 6: Development Workflow

**Running Tests:**
```bash
# API tests
pytest api/tests/

# Plugin tests
python scripts/test_asura_scans.py

# Integration tests
python scripts/test_tracking.py
```

**Adding API Endpoints:**
1. Add Pydantic schema to `api/schemas.py`
2. Add endpoint to appropriate router in `api/routers/`
3. Use dependency injection: `db: Session = Depends(get_db)`
4. Test with curl or Swagger UI at `/docs`
5. Update frontend API client in `frontend/src/lib/api.ts`

**Modifying Frontend:**
1. Edit page in `frontend/src/pages/`
2. Use Astro for SSR, Alpine.js for interactivity
3. Call API via `fetch()` or API client functions
4. Test with `npm run dev`

**Database Migrations:**
```bash
# Create backup
mysqldump -u mangataro_user -p mangataro > backup.sql

# Make schema changes
mysql -u mangataro_user -p mangataro < migration.sql

# Update models.py to match new schema
```

#### Section 7: Contributing

**Code Style:**
- Python: `snake_case` functions, `PascalCase` classes
- TypeScript: `camelCase` functions, `PascalCase` components
- Astro components: `PascalCase.astro`

**Git Workflow:**
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

# Push and create PR (if collaborating)
git push origin feature/new-scanlator
```

**Testing Requirements:**
- Plugins: Must test with --visible first, then headless
- API endpoints: Test with curl or Swagger UI
- Frontend: Manual browser testing
- Integration: Run full tracking cycle with --limit 1

---

### 5. docs/PLUGIN_QUICK_REFERENCE.md - One-Page Cheat Sheet

**Purpose:** Fast reference for adding new scanlator plugins

**Content:** (See detailed outline from earlier - complete copy-paste template with annotations)

---

## Implementation Plan

### Phase 1: Preparation
1. Review current documentation to extract content
2. Take screenshots (DONE - 5 screenshots in docs/images/)
3. Create backup branch

### Phase 2: Content Migration
1. Write new README.md (quick-action style)
2. Write docs/GETTING_STARTED.md (consolidate SETUP + DEPLOYMENT + TRACKING)
3. Write docs/USER_GUIDE.md (enhance with screenshots)
4. Write docs/DEVELOPER_GUIDE.md (consolidate architecture + plugins + API)
5. Write docs/PLUGIN_QUICK_REFERENCE.md (new cheat sheet)

### Phase 3: Cleanup
1. Delete 15 obsolete documentation files
2. Delete docs/legacy/ directory
3. Update any internal links in code/configs

### Phase 4: Validation
1. Test all links in new docs
2. Verify screenshots display correctly
3. Check for any broken references
4. Get user approval

### Phase 5: Finalization
1. Commit documentation consolidation
2. Update CLAUDE.md to reference new structure
3. Archive old docs in git history

---

## Files to Delete

### Root Level
- QUICK_START.md
- ASURASCANS_PLUGIN_USAGE.md
- SCANLATOR_QUICK_REFERENCE.md

### docs/ Directory
- docs/SETUP.md
- docs/DEPLOYMENT.md
- docs/API_GUIDE.md
- docs/TRACKING_GUIDE.md
- docs/TRACKING_QUICK_START.md
- docs/PROJECT_STRUCTURE.md
- docs/SERVICE_MANAGEMENT.md
- docs/SCANLATORS.md
- docs/BROWSER_TESTING_GUIDE.md
- docs/TEST_SUMMARY.md
- docs/END_TO_END_TEST_REPORT.md
- docs/legacy/ (entire directory)

**Total:** 15 files deleted, 5 files created/rewritten

---

## Success Criteria

✅ Documentation reduced from 15+ files to 5 focused guides
✅ Clear entry points for users vs developers
✅ All content accessible within 2 clicks from README
✅ No duplicate information across files
✅ Screenshots integrated throughout
✅ Quick-action README gets users running in 5 minutes
✅ Zero broken links or references
✅ User approval obtained

---

## Notes

- Screenshots already captured in docs/images/ (5 files, ~2MB total)
- CLAUDE.md and TOMORROW.md intentionally excluded (for AI assistants)
- Git history preserves all deleted content if needed
- New structure supports both user and developer audiences equally
- Visual elements (screenshots, diagrams) make docs more engaging
