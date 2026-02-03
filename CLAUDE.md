# CLAUDE.md - MangaTaro Developer Guide

**Last Updated:** 2026-02-03
**Project Status:** Production Ready (100% Complete)
**For:** Future Claude sessions or AI assistants working on this project

---

## 📋 Table of Contents

1. [Project Context](#project-context)
2. [Quick Architecture Overview](#quick-architecture-overview)
3. [Critical Information (Read First!)](#critical-information-read-first)
4. [System Components](#system-components)
5. [Code Organization](#code-organization)
6. [Key Design Decisions](#key-design-decisions)
7. [Development Workflows](#development-workflows)
8. [Common Tasks](#common-tasks)
9. [Troubleshooting](#troubleshooting)
10. [What NOT to Change](#what-not-to-change)

---

## 🎯 Project Context

### Why This Exists

**The Problem:** MangaTaro (a manga reading tracker) is shutting down. The user has 94 manga in their collection and needs a way to continue tracking new chapters after the shutdown.

**The Solution:** MangaTaro - a self-hosted manga chapter tracker that:
- Imports the user's manga collection from MangaTaro export
- Automatically tracks new chapters across multiple scanlation websites
- Provides a modern web UI to view updates and mark chapters as read
- Sends Discord notifications for new chapters
- Runs automated tracking on a schedule

**Timeline:** MangaTaro closes in ~12 days (as of 2026-02-03), but extraction is complete with 94 manga safely in the database.

### User Requirements

The user wanted:
- ✅ A working system BEFORE MangaTaro shuts down (achieved!)
- ✅ Modern, clean web interface (Astro + TailwindCSS)
- ✅ Automated chapter tracking (cron/n8n)
- ✅ Discord notifications for new chapters
- ✅ Extensible plugin architecture for scanlators
- ✅ Comprehensive documentation

### Project Phases (All Complete)

1. **Phase 1: Urgent Extraction** - Extract manga from MangaTaro before shutdown ✅
2. **Phase 2: Tracking System** - Plugin architecture + AsuraScans implementation ✅
3. **Phase 3: API** - FastAPI REST API with CRUD operations ✅
4. **Phase 4: Frontend** - Astro web UI with updates feed ✅
5. **Phase 5: Automation** - n8n workflows + cron scripts ✅
6. **Phase 6: Documentation** - User guides, setup, deployment docs ✅

---

## 🏗️ Quick Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                          │
│                   http://localhost:4343                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Astro Frontend (SSR)                       │
│  - Updates feed (homepage)                                   │
│  - Library grid (manga collection)                           │
│  - Manga detail pages                                        │
│  Technologies: Astro + TailwindCSS + Alpine.js              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Requests
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│                 http://localhost:8008                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Routers:                                             │   │
│  │  - /api/manga         - Manga CRUD                    │   │
│  │  - /api/scanlators    - Scanlator CRUD                │   │
│  │  - /api/tracking      - Chapter tracking & jobs       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Services:                                            │   │
│  │  - NotificationService - Discord webhooks             │   │
│  │  - TrackerService      - Background tracking jobs     │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ SQLAlchemy ORM
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    MariaDB Database                          │
│  Tables: mangas, scanlators, manga_scanlator, chapters       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Scanlator Plugins                           │
│  (Playwright-based web scraping)                             │
│  - BaseScanlator (abstract)                                  │
│  - AsuraScans (implemented)                                  │
│  - [Future plugins]                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Automation                                │
│  - Cron (scripts/run_scheduled_tracking.sh)                  │
│  - n8n (n8n/workflows/scheduled_tracking.json)               │
│  - Systemd Timer (docs/DEPLOYMENT.md)                        │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow for Chapter Tracking:**
1. Cron/n8n triggers → POST /api/tracking/trigger
2. TrackerService creates background job → launches Playwright
3. For each verified manga-scanlator mapping:
   - Instantiate scanlator plugin with Playwright page
   - Call `plugin.obtener_capitulos(manga_url)`
   - Plugin scrapes website, returns chapters
4. TrackerService inserts new chapters to database
5. NotificationService sends Discord webhook with new chapters
6. User sees updates in web UI

---

## 🚨 Critical Information (Read First!)

### 1. Spanish Field Names in Scanlator Plugins

**CRITICAL:** The scanlator plugin architecture uses **Spanish field names** while the database uses **English field names**. This was an early design decision that must be maintained for consistency.

**Scanlator Plugin API (Spanish):**
```python
# Plugins return:
{
    "numero": "42",      # Chapter number
    "titulo": "Title",   # Chapter title
    "url": "https://...",
    "fecha": datetime()  # Release date
}
```

**Database Schema (English):**
```python
# Database stores:
Chapter(
    chapter_number="42",  # Maps from "numero"
    title="Title",        # Maps from "titulo"
    url="https://...",
    release_date=datetime()  # Maps from "fecha"
)
```

**Where This Matters:**
- `api/services/tracker_service.py` - Has field mapping logic (line ~214-228)
- When adding new scanlator plugins - MUST return Spanish field names
- When creating test data - Use Spanish fields for plugin responses

**Why Spanish?** The first scanlator implemented (AsuraScans) serves Spanish-speaking users, so the plugin interface was designed in Spanish. Changing this now would break the existing AsuraScans plugin.

### 2. Scanlator Plugin Instantiation Pattern

**CRITICAL:** Scanlator plugins REQUIRE a Playwright page in the constructor.

**Correct Pattern:**
```python
# Create page FIRST
page = await browser.new_page()

# Pass page to plugin constructor
plugin_class = get_scanlator_by_name("AsuraScans")
plugin = plugin_class(page)

# Call methods
chapters = await plugin.obtener_capitulos(manga_url)

# Clean up
await page.close()
```

**Wrong Pattern (Will Crash):**
```python
# DON'T DO THIS - missing page parameter
plugin = plugin_class()  # TypeError!
```

**Location:** `api/services/tracker_service.py:192-198`

### 3. Async Everywhere

The entire tracking system is async:
- FastAPI endpoints are `async def`
- Services use `async/await`
- Scanlator plugins use `async def` methods
- Playwright is async (`async_playwright`)

**Never mix sync and async** - if you add new code, it must be async-compatible.

### 4. Environment Variables

Critical configuration in `.env`:
```bash
# Database
DB_HOST=localhost
DB_NAME=mangataro
DB_USER=mangataro_user
DB_PASSWORD=<secure_password>

# API
CORS_ORIGINS=http://localhost:3000,http://localhost:4343

# Notifications (optional)
NOTIFICATION_TYPE=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**Never commit `.env`** - only `.env.example`

---

## 🧩 System Components

### Backend (FastAPI)

**Location:** `/data/mangataro/api/`

**Structure:**
```
api/
├── main.py              # FastAPI app, CORS, routers
├── database.py          # SQLAlchemy engine, SessionLocal
├── models.py            # ORM models (Manga, Chapter, etc.)
├── schemas.py           # Pydantic models for validation
├── dependencies.py      # Dependency injection (get_db)
├── utils.py             # Utility functions
├── routers/
│   ├── manga.py         # Manga CRUD endpoints
│   ├── scanlators.py    # Scanlator CRUD endpoints
│   └── tracking.py      # Tracking & job endpoints
└── services/
    ├── __init__.py      # Service exports
    ├── notification_service.py  # Discord notifications
    └── tracker_service.py       # Background tracking jobs
```

**Key Patterns:**
- **Dependency Injection:** `get_db()` provides database sessions
- **Services:** Business logic separated from routers
- **Schemas:** Request/response validation with Pydantic
- **Models:** Database entities with SQLAlchemy ORM

### Frontend (Astro)

**Location:** `/data/mangataro/frontend/`

**Structure:**
```
frontend/
├── astro.config.mjs     # Astro + TailwindCSS config
├── src/
│   ├── layouts/
│   │   └── Layout.astro # Base layout with navigation
│   ├── pages/
│   │   ├── index.astro      # Homepage (updates feed)
│   │   ├── library.astro    # Library grid
│   │   └── manga/[id].astro # Manga detail pages
│   ├── components/
│   │   ├── ChapterItem.astro  # Chapter card
│   │   ├── ChapterList.astro  # Chapter list
│   │   └── MangaCard.astro    # Manga card
│   └── lib/
│       ├── api.ts       # API client (TypeScript)
│       └── utils.ts     # Utility functions
└── public/
    └── manga/           # Symlink to /data/mangataro/data/img/
```

**Key Features:**
- **SSR:** Server-side rendering with Astro
- **Alpine.js:** Client-side interactivity (mark as read)
- **TailwindCSS:** Utility-first styling
- **TypeScript:** Type-safe API client

### Scanlator Plugins

**Location:** `/data/mangataro/scanlators/`

**Architecture:**
```
scanlators/
├── __init__.py          # Auto-discovery, get_scanlator_by_name()
├── base.py              # BaseScanlator abstract class
├── template.py          # Template for new plugins
└── asura_scans.py       # AsuraScans implementation
```

**Plugin Interface (Abstract Methods):**
```python
class BaseScanlator(ABC):
    def __init__(self, playwright_page: Page):
        self.page = playwright_page

    @abstractmethod
    async def buscar_manga(self, titulo: str) -> list[dict]:
        """Search for manga by title"""

    @abstractmethod
    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """Get all chapters from manga page"""

    @abstractmethod
    def parsear_numero_capitulo(self, texto: str) -> str:
        """Parse chapter number from text"""
```

**Plugin Discovery:**
```python
# Automatic plugin discovery by class name
from scanlators import get_scanlator_by_name

plugin_class = get_scanlator_by_name("AsuraScans")
# Returns: AsuraScans class
```

### Database Schema

**Location:** `scripts/create_db.sql`

**Tables:**
```sql
mangas
├── id (PK)
├── titulo (manga title)
├── portada_url (cover image)
├── descripcion
└── estado (reading status)

scanlators
├── id (PK)
├── name (scanlator name)
└── base_url

manga_scanlator (join table)
├── id (PK)
├── manga_id (FK → mangas)
├── scanlator_id (FK → scanlators)
├── scanlator_manga_url (URL to manga on scanlator)
└── manually_verified (boolean - must be true for tracking)

chapters
├── id (PK)
├── manga_scanlator_id (FK → manga_scanlator)
├── chapter_number (string, e.g., "42", "42.5")
├── title (optional chapter title)
├── url (link to chapter)
├── release_date (when scanlator released it)
├── detected_date (when we discovered it)
└── read (boolean - user read status)
```

**Key Relationships:**
- One manga can have multiple scanlators
- One scanlator can track multiple manga
- Chapters belong to a manga-scanlator pair (not directly to manga)
- `manually_verified=1` is required for tracking to process the mapping

---

## 📂 Code Organization

### Import Patterns

**Backend imports:**
```python
# FastAPI and routing
from fastapi import FastAPI, APIRouter, Depends, HTTPException

# Database
from sqlalchemy.orm import Session
from api.database import SessionLocal
from api.models import Manga, Chapter
from api import schemas

# Services
from api.services.notification_service import get_notification_service
from api.services.tracker_service import get_tracker_service

# Scanlator plugins
from scanlators import get_scanlator_by_name
```

**Frontend imports:**
```typescript
// API client
import { getManga, getChapters, markAsRead } from '@/lib/api';

// Utils
import { formatDate, truncate } from '@/lib/utils';
```

### Naming Conventions

**Python (Backend):**
- **Files:** `snake_case.py`
- **Classes:** `PascalCase` (e.g., `NotificationService`, `TrackerService`)
- **Functions:** `snake_case` (e.g., `get_tracker_service`, `mark_chapter_read`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_CHAPTERS_PER_PAGE`)

**TypeScript (Frontend):**
- **Files:** `camelCase.ts` or `kebab-case.astro`
- **Functions:** `camelCase` (e.g., `getManga`, `formatDate`)
- **Components:** `PascalCase.astro` (e.g., `ChapterList.astro`)

**Database:**
- **Tables:** `snake_case` (e.g., `manga_scanlator`)
- **Columns:** `snake_case` (e.g., `chapter_number`, `detected_date`)

### Configuration Files

**Backend:**
- `.env` - Environment variables (NEVER commit)
- `.env.example` - Template (safe to commit)
- `requirements.txt` - Python dependencies

**Frontend:**
- `frontend/.env` - Frontend env vars
- `frontend/package.json` - Node dependencies
- `frontend/astro.config.mjs` - Astro configuration
- `frontend/tailwind.config.mjs` - TailwindCSS config

---

## 🎨 Key Design Decisions

### 1. Why FastAPI?

- **Async support:** Native async/await for Playwright scraping
- **Auto docs:** OpenAPI/Swagger UI at `/docs`
- **Type safety:** Pydantic validation
- **Performance:** Faster than Flask/Django for async I/O

### 2. Why Astro?

- **SSR:** Server-side rendering for better SEO
- **Island architecture:** Client JS only where needed
- **Fast builds:** Faster than Next.js for static sites
- **TailwindCSS:** Easy styling with utilities

### 3. Why Playwright?

- **Async:** Native async/await support
- **Modern:** Better than Selenium for modern sites
- **Headless:** Can run without display
- **Reliable:** Handles dynamic content well

### 4. Why Singleton Services?

```python
# Services use singleton pattern
_notification_service = NotificationService()

def get_notification_service() -> NotificationService:
    return _notification_service
```

**Reasons:**
- **State management:** TrackerService maintains job dictionary
- **Resource efficiency:** One service instance per app
- **Dependency injection:** Easy to mock for testing

### 5. Why Background Jobs?

Tracking is slow (30-60 seconds per manga), so:
- API returns immediately with job ID (202 Accepted)
- Tracking runs in background (asyncio.create_task)
- User polls `/api/tracking/jobs/{job_id}` for status

This prevents HTTP timeouts and allows concurrent tracking.

### 6. Plugin Architecture

**Why abstract base class?**
- **Extensibility:** Easy to add new scanlators
- **Consistency:** All plugins have same interface
- **Type safety:** IDE autocomplete and type checking

**Auto-discovery:** Plugins register automatically by class name. No manual registration needed.

---

## 🔧 Development Workflows

### Adding a New Scanlator Plugin

1. **Copy template:**
   ```bash
   cp scanlators/template.py scanlators/new_scanlator.py
   ```

2. **Implement required methods:**
   ```python
   class NewScanlator(BaseScanlator):
       def __init__(self, playwright_page: Page):
           super().__init__(playwright_page)
           self.name = "NewScanlator"
           self.base_url = "https://newscanlator.com"

       async def buscar_manga(self, titulo: str) -> list[dict]:
           # Return list of {"titulo", "url", "portada"}

       async def obtener_capitulos(self, manga_url: str) -> list[dict]:
           # Return list of {"numero", "titulo", "url", "fecha"}

       def parsear_numero_capitulo(self, texto: str) -> str:
           # Extract "42" from "Chapter 42" or similar
   ```

3. **Test the plugin:**
   ```bash
   python scripts/test_new_scanlator.py
   ```

4. **Add manga-scanlator mapping:**
   ```bash
   python scripts/add_manga_source.py
   ```

5. **Run tracking:**
   ```bash
   python scripts/track_chapters.py --scanlator-id <id> --visible
   ```

### Adding a New API Endpoint

1. **Add Pydantic schema** (`api/schemas.py`):
   ```python
   class NewFeatureRequest(BaseModel):
       param: str
       optional: Optional[int] = None

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

3. **Test endpoint:**
   ```bash
   curl -X POST http://localhost:8008/api/path/new-feature \
     -H "Content-Type: application/json" \
     -d '{"param": "value"}'
   ```

4. **Update API client** (`frontend/src/lib/api.ts`):
   ```typescript
   export async function newFeature(param: string): Promise<NewFeatureResponse> {
       const response = await fetch(`${API_URL}/path/new-feature`, {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ param })
       });
       return response.json();
   }
   ```

### Adding a Frontend Page

1. **Create page** (`frontend/src/pages/newpage.astro`):
   ```astro
   ---
   import Layout from '@/layouts/Layout.astro';
   import { getDataFromAPI } from '@/lib/api';

   const data = await getDataFromAPI();
   ---

   <Layout title="New Page">
       <h1>New Page</h1>
       <!-- Content -->
   </Layout>
   ```

2. **Add navigation link** (`frontend/src/layouts/Layout.astro`):
   ```astro
   <a href="/newpage">New Page</a>
   ```

3. **Test:**
   ```bash
   cd frontend && npm run dev
   # Visit http://localhost:4343/newpage
   ```

---

## 📝 Common Tasks

### Start Development Environment

```bash
# Terminal 1: API
cd /data/mangataro
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8008

# Terminal 2: Frontend
cd /data/mangataro/frontend
npm run dev

# Access:
# Frontend: http://localhost:4343
# API Docs: http://localhost:8008/docs
```

### Run Chapter Tracking Manually

```bash
# Track all verified manga
python scripts/track_chapters.py

# Track specific manga
python scripts/track_chapters.py --manga-id 60

# Track with visible browser (debugging)
python scripts/track_chapters.py --visible --limit 1
```

### Add a Manga-Scanlator Mapping

```bash
# Interactive CLI
python scripts/add_manga_source.py

# Or via API
curl -X POST http://localhost:8008/api/tracking/manga-scanlators \
  -H "Content-Type: application/json" \
  -d '{
    "manga_id": 60,
    "scanlator_id": 3,
    "scanlator_manga_url": "https://asura-scans.com/manga/solo-leveling",
    "manually_verified": true
  }'
```

### Trigger Tracking via API

```bash
# Trigger tracking job
curl -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"notify": true}'

# Get job status
curl http://localhost:8008/api/tracking/jobs/{job_id}

# List recent jobs
curl http://localhost:8008/api/tracking/jobs
```

### Database Queries

```bash
# Connect to database
mysql -u mangataro_user -p mangataro

# Common queries
SELECT COUNT(*) FROM mangas;  # Total manga
SELECT COUNT(*) FROM chapters WHERE `read` = 0;  # Unread chapters
SELECT * FROM manga_scanlator WHERE manually_verified = 1;  # Verified mappings
```

### View Logs

```bash
# Tracking logs
ls -lh /data/mangataro/logs/

# API logs (if using systemd)
sudo journalctl -u mangataro-api -f

# Frontend logs
sudo journalctl -u mangataro-frontend -f
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue: "No plugin found for AsuraScans"**

**Cause:** Scanlator name in database doesn't match plugin class name.

**Fix:**
```sql
-- Check scanlator name in database
SELECT id, name FROM scanlators WHERE name LIKE '%Asura%';

-- Plugin discovery looks for class name matching database name
-- Ensure database has "AsuraScans" not "Asura Scans" or "asurascans"
```

**Issue: Chapters not appearing after tracking**

**Causes:**
1. `manually_verified = 0` on manga_scanlator mapping
2. Wrong scanlator URL
3. Plugin failed to scrape

**Debug:**
```bash
# Run tracking with visible browser
python scripts/track_chapters.py --manga-id 60 --visible

# Check logs
tail -f /data/mangataro/logs/track_chapters_*.log

# Test plugin directly
python scripts/test_asura_scans.py
```

**Issue: Frontend can't connect to API**

**Causes:**
1. API not running
2. Wrong API_URL in frontend/.env
3. CORS not configured

**Fix:**
```bash
# Check API is running
curl http://localhost:8008/health

# Check frontend .env
cat frontend/.env
# Should have: PUBLIC_API_URL=http://localhost:8008

# Check API CORS settings in .env
# Should include: CORS_ORIGINS=http://localhost:4343
```

**Issue: Playwright browser crashes**

**Causes:**
1. Missing system dependencies
2. Out of memory
3. Too many concurrent browsers

**Fix:**
```bash
# Install Playwright dependencies
playwright install-deps chromium

# Limit concurrent tracking
python scripts/track_chapters.py --limit 5

# Use headless mode (uses less memory)
# Don't use --visible flag
```

### Debug Mode

Enable debug logging:

```python
# In scripts/track_chapters.py or api/services/tracker_service.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🔒 What NOT to Change

### 1. Spanish Field Names in Plugins

**DON'T change** the plugin interface to use English field names. This would break AsuraScans plugin.

**If you need English internally:** Map at the service layer (like TrackerService does).

### 2. Database Schema

**DON'T change** column names or table structure without migration:
- Column renames break existing code
- Table changes need SQLAlchemy migration
- Foreign key changes can cascade delete data

**If schema change needed:**
1. Create migration script
2. Update models.py
3. Update all queries
4. Test thoroughly

### 3. API Response Formats

**DON'T change** existing endpoint response structures. This breaks the frontend.

**If new fields needed:** Add them as optional fields (don't remove existing).

**If major changes needed:** Create new endpoint version (v2).

### 4. Singleton Service Pattern

**DON'T change** services to create new instances per request. TrackerService needs singleton to maintain job state across requests.

### 5. Async/Await Pattern

**DON'T add** synchronous blocking code in async functions. This will block the event loop and cause performance issues.

**Wrong:**
```python
async def track_chapters():
    time.sleep(5)  # BLOCKS EVENT LOOP!
```

**Right:**
```python
async def track_chapters():
    await asyncio.sleep(5)  # NON-BLOCKING
```

---

## 📚 Key Files Reference

### Must Read Before Changing

- `api/services/tracker_service.py` - **Read lines 192-230** (plugin integration + field mapping)
- `scanlators/base.py` - **Abstract interface** for all plugins
- `api/main.py` - **CORS and router configuration**
- `api/models.py` - **Database schema** (understand relationships!)

### Configuration Files

- `.env` - **Environment variables** (never commit!)
- `requirements.txt` - **Python dependencies**
- `frontend/package.json` - **Node dependencies**
- `scripts/create_db.sql` - **Database schema**

### Documentation Files

- `README.md` - **Project overview** for users
- `docs/USER_GUIDE.md` - **How to use** the system
- `docs/SETUP.md` - **Installation** instructions
- `docs/DEPLOYMENT.md` - **Production** deployment
- `docs/api_guide.md` - **API reference**

### Implementation Plans

- `docs/plans/2026-02-01-manga-tracker-implementation.md` - **Original design**
- `docs/plans/2026-02-02-frontend-implementation.md` - **Frontend architecture**
- `docs/plans/2026-02-03-remaining-tasks-implementation.md` - **Final features**

---

## 🎓 Learning Resources

### Understanding the Codebase

**Start here (in order):**

1. **README.md** - Get the big picture
2. **TOMORROW.md** - See what's done and what's pending
3. **api/main.py** - Understand API structure
4. **api/routers/tracking.py** - See tracking endpoints
5. **api/services/tracker_service.py** - Understand background jobs
6. **scanlators/asura_scans.py** - See plugin implementation
7. **frontend/src/pages/index.astro** - See frontend structure

### Testing Your Changes

**Backend:**
```bash
# Test API endpoint
curl http://localhost:8008/api/manga/?limit=5

# Test tracking
python scripts/track_chapters.py --limit 1 --visible
```

**Frontend:**
```bash
cd frontend
npm run dev
# Visit http://localhost:4343 and test UI
```

**Database:**
```sql
-- Verify data
SELECT m.titulo, s.name, COUNT(c.id) as chapter_count
FROM mangas m
JOIN manga_scanlator ms ON m.id = ms.manga_id
JOIN scanlators s ON ms.scanlator_id = s.id
LEFT JOIN chapters c ON ms.id = c.manga_scanlator_id
WHERE ms.manually_verified = 1
GROUP BY m.id, s.id;
```

---

## 🚀 Quick Start for Future Sessions

**If you're a future Claude session starting work:**

1. **Read this file first** (you're doing it!)
2. **Read TOMORROW.md** to see current status
3. **Read the relevant plan** in `docs/plans/` for context
4. **Check git log** to see recent changes:
   ```bash
   git log --oneline -20
   ```
5. **Review the user's request** to understand what they want
6. **Ask clarifying questions** if anything is unclear
7. **Read the code** you'll be modifying
8. **Make changes** following the patterns here
9. **Test thoroughly** before committing
10. **Update this file** if you discover new patterns or gotchas!

---

## 📝 Conventions for This File

**When updating CLAUDE.md:**

- **Date stamp** your changes
- **Add new gotchas** to Critical Information section
- **Document new patterns** in Development Workflows
- **Keep it practical** - focus on what future Claude needs to know
- **Use examples** - code snippets are better than descriptions
- **Be specific** - "Line 192 in tracker_service.py" not "the tracker service"

**This is a living document** - keep it updated as the project evolves!

---

**Last Updated:** 2026-02-03
**Updated By:** Claude (via Subagent-Driven Development)
**Version:** 1.0
**Project Status:** Production Ready ✅

