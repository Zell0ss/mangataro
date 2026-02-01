# Manga Tracker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a self-hosted manga tracking system that scrapes MangaTaro bookmarks urgently (before site closes in 15 days), then tracks new chapters from scanlation groups with automated notifications.

**Architecture:** Plugin-based scanlator scrapers (Playwright) → MariaDB storage → FastAPI backend → Astro frontend + n8n automation

**Tech Stack:** Python 3.11+, Playwright, SQLAlchemy, MariaDB, FastAPI, Astro, n8n, Tailwind CSS

---

## PHASE 1: URGENT EXTRACTION (Days 1-3) - CRITICAL

### Task 1: Database Setup

**Files:**
- Create: `api/models.py`
- Create: `api/database.py`
- Create: `scripts/create_db.sql`
- Create: `.env`
- Create: `.env.example`

**Step 1: Write database schema SQL**

Create `scripts/create_db.sql`:

```sql
CREATE DATABASE IF NOT EXISTS mangataro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mangataro;

CREATE TABLE mangas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mangataro_id VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    alternative_titles TEXT,
    cover_filename VARCHAR(255),
    mangataro_url VARCHAR(500),
    date_added DATETIME,
    last_checked DATETIME,
    status ENUM('reading', 'completed', 'on_hold', 'plan_to_read') DEFAULT 'reading',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_title (title),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE scanlators (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    class_name VARCHAR(100) NOT NULL,
    base_url VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE manga_scanlator (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_id INT NOT NULL,
    scanlator_id INT NOT NULL,
    scanlator_manga_url VARCHAR(500) NOT NULL,
    manually_verified BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE,
    FOREIGN KEY (scanlator_id) REFERENCES scanlators(id) ON DELETE CASCADE,
    UNIQUE KEY unique_manga_scanlator (manga_id, scanlator_id),
    INDEX idx_manga (manga_id),
    INDEX idx_scanlator (scanlator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT NOT NULL,
    chapter_number VARCHAR(20) NOT NULL,
    chapter_title VARCHAR(255),
    chapter_url VARCHAR(500) NOT NULL,
    published_date DATETIME,
    detected_date DATETIME NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id) ON DELETE CASCADE,
    UNIQUE KEY unique_chapter (manga_scanlator_id, chapter_number),
    INDEX idx_detected (detected_date DESC),
    INDEX idx_read (read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE scraping_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT,
    error_type VARCHAR(50),
    error_message TEXT,
    timestamp DATETIME NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id) ON DELETE CASCADE,
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_resolved (resolved)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Step 2: Create environment template**

Create `.env.example`:

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mangataro
DB_USER=mangataro_user
DB_PASSWORD=your_password_here

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Scraping
PLAYWRIGHT_TIMEOUT=30000
SCRAPING_DELAY_MIN=2
SCRAPING_DELAY_MAX=5
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Notifications
NOTIFICATION_TYPE=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**Step 3: Copy to actual .env file**

Run:
```bash
cp .env.example .env
```

Edit `.env` with real credentials.

**Step 4: Execute database creation**

Run:
```bash
mysql -u root -p < scripts/create_db.sql
```

Expected: Database and tables created successfully.

**Step 5: Create SQLAlchemy models**

Create `api/models.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class MangaStatus(str, enum.Enum):
    reading = "reading"
    completed = "completed"
    on_hold = "on_hold"
    plan_to_read = "plan_to_read"


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga_scanlators = relationship("MangaScanlator", back_populates="manga", cascade="all, delete-orphan")


class Scanlator(Base):
    __tablename__ = "scanlators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    class_name = Column(String(100), nullable=False)
    base_url = Column(String(255))
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga_scanlators = relationship("MangaScanlator", back_populates="scanlator", cascade="all, delete-orphan")


class MangaScanlator(Base):
    __tablename__ = "manga_scanlator"

    id = Column(Integer, primary_key=True, index=True)
    manga_id = Column(Integer, ForeignKey("mangas.id", ondelete="CASCADE"), nullable=False, index=True)
    scanlator_id = Column(Integer, ForeignKey("scanlators.id", ondelete="CASCADE"), nullable=False, index=True)
    scanlator_manga_url = Column(String(500), nullable=False)
    manually_verified = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga = relationship("Manga", back_populates="manga_scanlators")
    scanlator = relationship("Scanlator", back_populates="manga_scanlators")
    chapters = relationship("Chapter", back_populates="manga_scanlator", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    manga_scanlator_id = Column(Integer, ForeignKey("manga_scanlator.id", ondelete="CASCADE"), nullable=False)
    chapter_number = Column(String(20), nullable=False)
    chapter_title = Column(String(255))
    chapter_url = Column(String(500), nullable=False)
    published_date = Column(DateTime)
    detected_date = Column(DateTime, nullable=False, index=True)
    read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga_scanlator = relationship("MangaScanlator", back_populates="chapters")


class ScrapingError(Base):
    __tablename__ = "scraping_errors"

    id = Column(Integer, primary_key=True, index=True)
    manga_scanlator_id = Column(Integer, ForeignKey("manga_scanlator.id", ondelete="CASCADE"))
    error_type = Column(String(50))
    error_message = Column(Text)
    timestamp = Column(DateTime, nullable=False, index=True)
    resolved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 6: Create database connection module**

Create `api/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER", "mangataro_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "mangataro")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 7: Create requirements.txt**

Create `requirements.txt`:

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pymysql==1.1.0
pydantic==2.5.0
playwright==1.41.0
beautifulsoup4==4.12.3
requests==2.31.0
loguru==0.7.2
python-dotenv==1.0.0
```

**Step 8: Install dependencies**

Run:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Expected: All packages installed successfully.

**Step 9: Commit**

```bash
git init
git add scripts/create_db.sql api/models.py api/database.py requirements.txt .env.example .gitignore
git commit -m "feat: setup database schema and SQLAlchemy models"
```

---

### Task 2: MangaTaro Extractor Script

**Files:**
- Create: `scripts/extract_mangataro.py`
- Create: `api/utils.py`

**Step 1: Create utilities module**

Create `api/utils.py`:

```python
import requests
from pathlib import Path
from loguru import logger
import re
from urllib.parse import urlparse


def download_image(url: str, save_dir: str) -> str | None:
    """
    Download image from URL and save to directory.

    Returns:
        Filename if successful, None if failed
    """
    try:
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        # Extract filename from URL
        parsed = urlparse(url)
        filename = Path(parsed.path).name

        # Fallback if no extension
        if not Path(filename).suffix:
            ext = url.split('.')[-1].split('?')[0]
            filename = f"{filename}.{ext}"

        filepath = save_path / filename

        # Download
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        # Validate it's an image
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            logger.warning(f"URL doesn't appear to be an image: {url}")
            return None

        # Save
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Validate size
        if filepath.stat().st_size == 0:
            logger.error(f"Downloaded image is empty: {url}")
            filepath.unlink()
            return None

        logger.info(f"Downloaded: {filename}")
        return filename

    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return None


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def create_markdown_ficha(manga_data: dict, output_dir: str) -> Path:
    """
    Create markdown ficha for manga.

    Args:
        manga_data: Dict with keys: title, alternative_titles, cover_filename, scanlator_group
        output_dir: Directory to save markdown

    Returns:
        Path to created file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    slug = slugify(manga_data['title'])
    filename = output_path / f"{slug}.md"

    content = f"""# {manga_data['title']}

## {manga_data.get('alternative_titles', 'N/A')}

![Portada](../../data/img/{manga_data.get('cover_filename', 'placeholder.png')})

**Scanlation Group:** {manga_data.get('scanlator_group', 'Unknown')}

**MangaTaro URL:** {manga_data.get('mangataro_url', 'N/A')}

**Date Added:** {manga_data.get('date_added', 'N/A')}
"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"Created ficha: {filename}")
    return filename
```

**Step 2: Write extractor script skeleton**

Create `scripts/extract_mangataro.py`:

```python
#!/usr/bin/env python
import json
import sys
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import random

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api.database import SessionLocal
from api.models import Manga, Scanlator
from api.utils import download_image, create_markdown_ficha, slugify


# Configure logging
logger.add("logs/extract_mangataro.log", rotation="10 MB")


def scrape_manga_page(page, url: str) -> dict:
    """
    Scrape MangaTaro manga page for alternative titles and scanlation group.

    Returns:
        {
            'alternative_titles': str,
            'scanlator_group': str
        }
    """
    try:
        logger.info(f"Scraping: {url}")
        page.goto(url, wait_until="networkidle", timeout=30000)

        # Extract alternative titles
        # Looking for paragraph with multiple titles separated by " / "
        alternative_titles = ""
        try:
            # Try multiple selectors
            alt_selectors = [
                "p:has-text('/')",  # Paragraph containing "/"
                "div.manga-info p",
                ".alternative-titles"
            ]

            for selector in alt_selectors:
                elements = page.locator(selector).all()
                for elem in elements:
                    text = elem.inner_text().strip()
                    if '/' in text and len(text) > 20:  # Likely alternative titles
                        alternative_titles = text
                        break
                if alternative_titles:
                    break

        except Exception as e:
            logger.warning(f"Could not extract alternative titles: {e}")

        # Extract scanlation group
        scanlator_group = ""
        try:
            # Look for headings with group names
            group_selectors = [
                "h3:has-text('scanlation')",
                "h3:has-text('Scanlation')",
                "a[href*='/groups/']"
            ]

            for selector in group_selectors:
                elem = page.locator(selector).first
                if elem.count() > 0:
                    scanlator_group = elem.inner_text().strip()
                    break

        except Exception as e:
            logger.warning(f"Could not extract scanlator group: {e}")

        return {
            'alternative_titles': alternative_titles,
            'scanlator_group': scanlator_group
        }

    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return {
            'alternative_titles': '',
            'scanlator_group': ''
        }


def process_bookmarks(json_path: str, db_session):
    """Process all bookmarks from MangaTaro export"""

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    bookmarks = data.get('bookmarks', [])
    logger.info(f"Found {len(bookmarks)} bookmarks to process")

    scanlators_found = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        for idx, bookmark in enumerate(bookmarks, 1):
            logger.info(f"Processing {idx}/{len(bookmarks)}: {bookmark['title']}")

            # Download cover image
            cover_filename = download_image(bookmark['cover'], 'data/img')

            # Scrape manga page
            scraped_data = scrape_manga_page(page, bookmark['url'])

            # Create manga record
            manga = Manga(
                mangataro_id=bookmark['id'],
                title=bookmark['title'],
                alternative_titles=scraped_data['alternative_titles'] or None,
                cover_filename=cover_filename,
                mangataro_url=bookmark['url'],
                date_added=datetime.strptime(bookmark['dateAdded'], '%Y-%m-%d %H:%M:%S'),
                status='reading'
            )

            db_session.add(manga)
            db_session.flush()  # Get manga.id

            # Track scanlator
            if scraped_data['scanlator_group']:
                scanlators_found.add(scraped_data['scanlator_group'])

                # Create or get scanlator
                scanlator = db_session.query(Scanlator).filter_by(
                    name=scraped_data['scanlator_group']
                ).first()

                if not scanlator:
                    scanlator = Scanlator(
                        name=scraped_data['scanlator_group'],
                        class_name=f"{slugify(scraped_data['scanlator_group']).replace('-', '_').title()}Scanlator",
                        base_url="",  # To be filled manually
                        active=True
                    )
                    db_session.add(scanlator)
                    db_session.flush()

            # Create markdown ficha
            ficha_data = {
                'title': bookmark['title'],
                'alternative_titles': scraped_data['alternative_titles'],
                'cover_filename': cover_filename,
                'scanlator_group': scraped_data['scanlator_group'],
                'mangataro_url': bookmark['url'],
                'date_added': bookmark['dateAdded']
            }
            create_markdown_ficha(ficha_data, 'docs/fichas')

            # Commit after each manga
            db_session.commit()

            # Delay to be polite
            delay = random.uniform(2, 5)
            logger.info(f"Waiting {delay:.1f}s before next request...")
            time.sleep(delay)

        browser.close()

    # Generate scanlators.md
    generate_scanlators_list(scanlators_found)

    logger.info("Extraction complete!")


def generate_scanlators_list(scanlators: set):
    """Generate markdown list of scanlators found"""
    output_path = Path('docs/scanlators.md')

    content = "# Scanlation Groups Found\n\n"
    content += "Below are the scanlation groups detected from MangaTaro. "
    content += "You need to manually find the manga URLs on each group's site.\n\n"

    for scanlator in sorted(scanlators):
        content += f"- [ ] {scanlator}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"Created {output_path}")


def main():
    logger.info("Starting MangaTaro extraction...")

    # Create necessary directories
    Path('data/img').mkdir(parents=True, exist_ok=True)
    Path('docs/fichas').mkdir(parents=True, exist_ok=True)
    Path('logs').mkdir(exist_ok=True)

    # Get database session
    db = SessionLocal()

    try:
        process_bookmarks('data/mangataro-export.json', db)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

**Step 3: Test on one manga**

Comment out the loop in `process_bookmarks()` to only process first bookmark.

Run:
```bash
python scripts/extract_mangataro.py
```

Expected: One manga extracted, image downloaded, ficha created.

**Step 4: Review output and adjust selectors**

Check `docs/fichas/` and `data/img/` for output.
Adjust CSS selectors in `scrape_manga_page()` if needed.

**Step 5: Run full extraction**

Uncomment loop, run:
```bash
python scripts/extract_mangataro.py
```

Expected: All bookmarks processed (may take 1-2 hours with delays).

**Step 6: Commit**

```bash
git add scripts/extract_mangataro.py api/utils.py docs/fichas/ docs/scanlators.md data/img/
git commit -m "feat: implement MangaTaro extractor with Playwright"
```

---

### Task 3: Manual URL Mapping Helper

**Files:**
- Create: `scripts/add_manga_source.py`

**Step 1: Create helper script for adding manga-scanlator URLs**

Create `scripts/add_manga_source.py`:

```python
#!/usr/bin/env python
"""Interactive script to add scanlator URLs for mangas"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from api.database import SessionLocal
from api.models import Manga, Scanlator, MangaScanlator
from loguru import logger


def main():
    db = SessionLocal()

    try:
        # List all mangas
        mangas = db.query(Manga).order_by(Manga.title).all()
        print(f"\n=== Found {len(mangas)} mangas ===\n")

        for idx, manga in enumerate(mangas, 1):
            print(f"{idx}. {manga.title}")

        # Select manga
        manga_idx = int(input("\nSelect manga number (0 to exit): "))
        if manga_idx == 0:
            return

        manga = mangas[manga_idx - 1]
        print(f"\nSelected: {manga.title}")

        # List scanlators
        scanlators = db.query(Scanlator).filter_by(active=True).order_by(Scanlator.name).all()
        print(f"\n=== Available Scanlators ===\n")

        for idx, scanlator in enumerate(scanlators, 1):
            print(f"{idx}. {scanlator.name}")

        scanlator_idx = int(input("\nSelect scanlator number: "))
        scanlator = scanlators[scanlator_idx - 1]

        # Get URL
        url = input(f"\nEnter manga URL on {scanlator.name}: ").strip()

        # Check if already exists
        existing = db.query(MangaScanlator).filter_by(
            manga_id=manga.id,
            scanlator_id=scanlator.id
        ).first()

        if existing:
            print(f"\nWarning: Entry already exists with URL: {existing.scanlator_manga_url}")
            overwrite = input("Overwrite? (y/n): ").lower()
            if overwrite == 'y':
                existing.scanlator_manga_url = url
                existing.manually_verified = True
                db.commit()
                print("Updated!")
            return

        # Create new
        manga_scanlator = MangaScanlator(
            manga_id=manga.id,
            scanlator_id=scanlator.id,
            scanlator_manga_url=url,
            manually_verified=True
        )

        db.add(manga_scanlator)
        db.commit()

        print(f"\n✓ Added {manga.title} on {scanlator.name}")

        # Continue?
        continue_input = input("\nAdd another? (y/n): ").lower()
        if continue_input == 'y':
            main()  # Recursive call

    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

**Step 2: Test the helper**

Run:
```bash
python scripts/add_manga_source.py
```

Add one test entry.

**Step 3: Commit**

```bash
git add scripts/add_manga_source.py
git commit -m "feat: add interactive helper for mapping manga to scanlators"
```

---

## PHASE 2: TRACKING SYSTEM (Days 4-7)

### Task 4: Scanlator Plugin Architecture

**Files:**
- Create: `scanlators/__init__.py`
- Create: `scanlators/base.py`
- Create: `scanlators/template.py`

**Step 1: Create base scanlator class**

Create `scanlators/base.py`:

```python
from abc import ABC, abstractmethod
from playwright.async_api import Page
from datetime import datetime
from loguru import logger


class BaseScanlator(ABC):
    """Base class for all scanlator implementations"""

    def __init__(self, playwright_page: Page):
        self.page = playwright_page
        self.name = ""
        self.base_url = ""

    @abstractmethod
    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search for manga by title on scanlator site.

        Args:
            titulo: Manga title to search for

        Returns:
            List of candidates: [
                {
                    "titulo": "Manga Title",
                    "url": "https://...",
                    "portada": "https://..."
                },
                ...
            ]
        """
        pass

    @abstractmethod
    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Extract chapters from manga page.

        Args:
            manga_url: URL of manga on scanlator site

        Returns:
            List of chapters: [
                {
                    "numero": "42",
                    "titulo": "Chapter Title",
                    "url": "https://...",
                    "fecha": datetime or None
                },
                ...
            ]
        """
        pass

    @abstractmethod
    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Normalize chapter number from scanlator's format.

        Args:
            texto: Raw chapter text (e.g., "Chapter 42.5", "Ch. 10")

        Returns:
            Normalized number: "42.5", "10"
        """
        pass

    async def safe_goto(self, url: str, timeout: int = 30000):
        """Navigate with error handling"""
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=timeout)
        except Exception as e:
            logger.error(f"{self.name}: Failed to load {url}: {e}")
            raise
```

**Step 2: Create auto-discovery system**

Create `scanlators/__init__.py`:

```python
import importlib
import inspect
from pathlib import Path
from loguru import logger
from .base import BaseScanlator


def discover_scanlators() -> dict[str, type]:
    """
    Scan scanlators/ directory and register all BaseScanlator subclasses.

    Returns:
        Dict mapping class_name to ScanlatorClass
    """
    scanlators = {}
    scanlator_dir = Path(__file__).parent

    for file in scanlator_dir.glob("*.py"):
        if file.stem in ["__init__", "base", "template"]:
            continue

        try:
            module = importlib.import_module(f"scanlators.{file.stem}")

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseScanlator) and obj != BaseScanlator:
                    scanlators[name] = obj
                    logger.info(f"Registered scanlator: {name}")

        except Exception as e:
            logger.error(f"Failed to load scanlator module {file.stem}: {e}")

    return scanlators


__all__ = ["BaseScanlator", "discover_scanlators"]
```

**Step 3: Create template for new scanlators**

Create `scanlators/template.py`:

```python
"""
Template for implementing a new scanlator.

Copy this file and rename to <scanlator_name>.py
Implement the three abstract methods.
"""
from .base import BaseScanlator
from datetime import datetime
import re


class TemplateScanlator(BaseScanlator):
    """Template implementation - RENAME THIS CLASS"""

    def __init__(self, playwright_page):
        super().__init__(playwright_page)
        self.name = "Template"  # Change this
        self.base_url = "https://example.com"  # Change this

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """Search implementation"""
        # Example:
        # await self.safe_goto(f"{self.base_url}/search?q={titulo}")
        # results = []
        # for item in await self.page.locator(".search-result").all():
        #     results.append({
        #         "titulo": await item.locator(".title").inner_text(),
        #         "url": await item.locator("a").get_attribute("href"),
        #         "portada": await item.locator("img").get_attribute("src")
        #     })
        # return results
        pass

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """Extract chapters implementation"""
        # Example:
        # await self.safe_goto(manga_url)
        # chapters = []
        # for item in await self.page.locator(".chapter-item").all():
        #     raw_number = await item.locator(".chapter-number").inner_text()
        #     chapters.append({
        #         "numero": self.parsear_numero_capitulo(raw_number),
        #         "titulo": await item.locator(".chapter-title").inner_text(),
        #         "url": await item.locator("a").get_attribute("href"),
        #         "fecha": None  # Or parse date if available
        #     })
        # return chapters
        pass

    def parsear_numero_capitulo(self, texto: str) -> str:
        """Parse chapter number implementation"""
        # Example:
        # match = re.search(r'(\d+(?:\.\d+)?)', texto)
        # return match.group(1) if match else texto
        pass
```

**Step 4: Test discovery system**

Create test script `test_discovery.py`:

```python
from scanlators import discover_scanlators

scanlators = discover_scanlators()
print(f"Found {len(scanlators)} scanlators:")
for name, cls in scanlators.items():
    print(f"  - {name}: {cls}")
```

Run:
```bash
python test_discovery.py
```

Expected: Empty dict (no scanlators implemented yet).

**Step 5: Commit**

```bash
git add scanlators/
git commit -m "feat: implement scanlator plugin architecture with auto-discovery"
```

---

### Task 5: Implement First Scanlator (Example)

**Files:**
- Create: `scanlators/manganato.py` (or whichever scanlator you choose first)

**Step 1: Choose a scanlator from your list**

Review `docs/scanlators.md` and pick the most common one.
For this example, we'll use a generic aggregator pattern.

**Step 2: Implement the scanlator class**

Create `scanlators/manganato.py` (example):

```python
"""Manganato scanlator implementation (example aggregator)"""
from .base import BaseScanlator
from datetime import datetime
import re


class ManganatoScanlator(BaseScanlator):
    """Manganato.com scraper"""

    def __init__(self, playwright_page):
        super().__init__(playwright_page)
        self.name = "Manganato"
        self.base_url = "https://manganato.com"

    async def buscar_manga(self, titulo: str) -> list[dict]:
        """Search for manga"""
        search_url = f"{self.base_url}/search/story/{titulo.replace(' ', '_')}"
        await self.safe_goto(search_url)

        results = []
        items = self.page.locator(".search-story-item").all()

        for item in await items:
            try:
                title_elem = item.locator(".item-title")
                img_elem = item.locator(".img-loading")

                results.append({
                    "titulo": await title_elem.inner_text(),
                    "url": await title_elem.get_attribute("href"),
                    "portada": await img_elem.get_attribute("src")
                })
            except:
                continue

        return results

    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """Extract chapters from manga page"""
        await self.safe_goto(manga_url)

        chapters = []
        chapter_items = self.page.locator(".chapter-name").all()

        for item in await chapter_items:
            try:
                chapter_text = await item.inner_text()
                chapter_url = await item.get_attribute("href")

                # Extract chapter number
                numero = self.parsear_numero_capitulo(chapter_text)

                chapters.append({
                    "numero": numero,
                    "titulo": chapter_text,
                    "url": chapter_url,
                    "fecha": None  # Manganato doesn't show dates easily
                })
            except:
                continue

        return chapters

    def parsear_numero_capitulo(self, texto: str) -> str:
        """Parse chapter number from text like 'Chapter 42.5'"""
        # Look for pattern: "Chapter X" or "Ch. X" or just "X"
        match = re.search(r'(?:chapter|ch\.?)\s*(\d+(?:\.\d+)?)', texto, re.IGNORECASE)
        if match:
            return match.group(1)

        # Fallback: extract any number
        match = re.search(r'(\d+(?:\.\d+)?)', texto)
        return match.group(1) if match else texto
```

**Step 3: Test the scanlator**

Create `test_scanlator.py`:

```python
import asyncio
from playwright.async_api import async_playwright
from scanlators.manganato import ManganatoScanlator


async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        scanlator = ManganatoScanlator(page)

        # Test search
        print("Searching for 'chainsaw man'...")
        results = await scanlator.buscar_manga("chainsaw man")
        print(f"Found {len(results)} results")

        if results:
            # Test chapter extraction
            print(f"\nGetting chapters for: {results[0]['titulo']}")
            chapters = await scanlator.obtener_capitulos(results[0]['url'])
            print(f"Found {len(chapters)} chapters")
            for ch in chapters[:5]:
                print(f"  - Chapter {ch['numero']}: {ch['titulo']}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test())
```

Run:
```bash
python test_scanlator.py
```

Expected: Search results and chapters printed.

**Step 4: Adjust selectors based on actual site structure**

Visit the scanlator site manually, inspect HTML, update selectors in the class.

**Step 5: Commit**

```bash
git add scanlators/manganato.py
git commit -m "feat: implement Manganato scanlator"
```

**Step 6: Repeat for 2-3 more scanlators**

Follow same pattern for other scanlators from your list.

---

### Task 6: Chapter Tracking Script

**Files:**
- Create: `scripts/check_updates.py`

**Step 1: Write tracking script**

Create `scripts/check_updates.py`:

```python
#!/usr/bin/env python
"""Check for new chapters from all scanlators"""
import sys
from pathlib import Path
import asyncio
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from loguru import logger
from api.database import SessionLocal
from api.models import MangaScanlator, Chapter, ScrapingError, Manga
from scanlators import discover_scanlators


logger.add("logs/check_updates.log", rotation="10 MB")


async def check_manga_updates(manga_scanlator: MangaScanlator, scanlator_class, page) -> list[dict]:
    """
    Check for new chapters for a specific manga-scanlator pair.

    Returns:
        List of new chapters found
    """
    new_chapters = []

    try:
        # Instantiate scanlator
        scanlator = scanlator_class(page)

        logger.info(f"Checking {manga_scanlator.manga.title} on {scanlator.name}")

        # Get current chapters
        current_chapters = await scanlator.obtener_capitulos(manga_scanlator.scanlator_manga_url)

        # Get database session
        db = SessionLocal()

        try:
            # Get existing chapters from DB
            existing_numbers = {
                ch.chapter_number
                for ch in db.query(Chapter).filter_by(
                    manga_scanlator_id=manga_scanlator.id
                ).all()
            }

            # Find new chapters
            for chapter_data in current_chapters:
                if chapter_data['numero'] not in existing_numbers:
                    # New chapter!
                    new_chapter = Chapter(
                        manga_scanlator_id=manga_scanlator.id,
                        chapter_number=chapter_data['numero'],
                        chapter_title=chapter_data.get('titulo'),
                        chapter_url=chapter_data['url'],
                        published_date=chapter_data.get('fecha'),
                        detected_date=datetime.utcnow(),
                        read=False
                    )

                    db.add(new_chapter)
                    new_chapters.append(chapter_data)

                    logger.info(f"New chapter: {manga_scanlator.manga.title} - Ch. {chapter_data['numero']}")

            # Update last_checked
            manga_scanlator.manga.last_checked = datetime.utcnow()

            db.commit()

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error checking {manga_scanlator.manga.title}: {e}")

        # Log error to database
        db = SessionLocal()
        try:
            error = ScrapingError(
                manga_scanlator_id=manga_scanlator.id,
                error_type="scraping_failed",
                error_message=str(e),
                timestamp=datetime.utcnow(),
                resolved=False
            )
            db.add(error)
            db.commit()
        finally:
            db.close()

    return new_chapters


async def main():
    """Main tracking loop"""
    logger.info("Starting chapter tracking...")

    # Discover scanlators
    scanlator_classes = discover_scanlators()
    logger.info(f"Loaded {len(scanlator_classes)} scanlator classes")

    # Get all manga-scanlator pairs
    db = SessionLocal()
    manga_scanlators = db.query(MangaScanlator).join(
        MangaScanlator.scanlator
    ).filter(
        MangaScanlator.manually_verified == True,
        MangaScanlator.scanlator.has(active=True)
    ).all()
    db.close()

    logger.info(f"Checking {len(manga_scanlators)} manga-scanlator pairs")

    all_new_chapters = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for ms in manga_scanlators:
            # Find scanlator class
            scanlator_class = scanlator_classes.get(ms.scanlator.class_name)

            if not scanlator_class:
                logger.error(f"Scanlator class not found: {ms.scanlator.class_name}")
                continue

            # Check for updates
            new_chapters = await check_manga_updates(ms, scanlator_class, page)
            all_new_chapters.extend(new_chapters)

            # Delay between requests
            await asyncio.sleep(3)

        await browser.close()

    # Summary
    logger.info(f"Tracking complete. Found {len(all_new_chapters)} new chapters")

    for ch in all_new_chapters:
        print(f"NEW: {ch['titulo']} - Chapter {ch['numero']}")

    return all_new_chapters


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Test tracking script**

Run:
```bash
python scripts/check_updates.py
```

Expected: Script checks all verified manga-scanlator pairs, reports new chapters.

**Step 3: Commit**

```bash
git add scripts/check_updates.py
git commit -m "feat: implement chapter tracking script"
```

---

## PHASE 3: API (Days 8-10)

### Task 7: FastAPI Base Setup

**Files:**
- Create: `api/__init__.py`
- Create: `api/main.py`
- Create: `api/dependencies.py`
- Create: `api/schemas.py`

**Step 1: Create Pydantic schemas**

Create `api/schemas.py`:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# Manga Schemas
class MangaBase(BaseModel):
    title: str
    alternative_titles: Optional[str] = None
    status: Optional[str] = "reading"


class MangaCreate(MangaBase):
    cover_url: str
    scanlator_id: int
    manga_url: str


class MangaUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class MangaResponse(MangaBase):
    id: int
    cover_filename: Optional[str]
    date_added: Optional[datetime]
    last_checked: Optional[datetime]

    class Config:
        from_attributes = True


# Scanlator Schemas
class ScanlatorBase(BaseModel):
    name: str
    base_url: Optional[str] = None


class ScanlatorCreate(ScanlatorBase):
    class_name: str


class ScanlatorResponse(ScanlatorBase):
    id: int
    class_name: str
    active: bool

    class Config:
        from_attributes = True


# Chapter Schemas
class ChapterResponse(BaseModel):
    id: int
    chapter_number: str
    chapter_title: Optional[str]
    chapter_url: str
    published_date: Optional[datetime]
    detected_date: datetime
    read: bool

    class Config:
        from_attributes = True


# Manga-Scanlator Schemas
class MangaScanlatorCreate(BaseModel):
    scanlator_id: int
    url: str


class ReadUntilSchema(BaseModel):
    chapter_number: str
    scanlator_id: int
```

**Step 2: Create dependencies**

Create `api/dependencies.py`:

```python
from api.database import get_db

# Re-export for convenience
__all__ = ["get_db"]
```

**Step 3: Create main FastAPI app**

Create `api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

app = FastAPI(
    title="Manga Tracker API",
    description="Track manga updates from scanlation groups",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Manga Tracker API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Manga Tracker API shutting down...")


@app.get("/")
async def root():
    return {"message": "Manga Tracker API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
```

**Step 4: Test API**

Run:
```bash
python -m api.main
```

Visit: http://localhost:8000/docs

Expected: Swagger UI with basic endpoints.

**Step 5: Commit**

```bash
git add api/main.py api/schemas.py api/dependencies.py
git commit -m "feat: setup FastAPI base application"
```

---

### Task 8: API CRUD Operations

**Files:**
- Create: `api/crud.py`
- Modify: `api/views.py` (create new)

**Step 1: Implement CRUD functions**

Create `api/crud.py`:

```python
from sqlalchemy.orm import Session
from sqlalchemy import desc
from api.models import Manga, Scanlator, MangaScanlator, Chapter
from api.schemas import MangaCreate, ScanlatorCreate
from api.utils import download_image
from datetime import datetime


# Manga CRUD
def get_mangas(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    search: str | None = None
):
    """Get list of mangas with filters"""
    query = db.query(Manga)

    if status:
        query = query.filter(Manga.status == status)

    if search:
        query = query.filter(Manga.title.contains(search))

    return query.offset(skip).limit(limit).all()


def get_manga(db: Session, manga_id: int):
    """Get single manga by ID"""
    return db.query(Manga).filter(Manga.id == manga_id).first()


def create_manga(db: Session, manga: MangaCreate):
    """Create new manga"""
    # Download cover
    cover_filename = download_image(manga.cover_url, "data/img")

    db_manga = Manga(
        title=manga.title,
        alternative_titles=manga.alternative_titles,
        cover_filename=cover_filename,
        status=manga.status,
        date_added=datetime.utcnow()
    )

    db.add(db_manga)
    db.flush()

    # Add scanlator source
    manga_scanlator = MangaScanlator(
        manga_id=db_manga.id,
        scanlator_id=manga.scanlator_id,
        scanlator_manga_url=manga.manga_url,
        manually_verified=True
    )

    db.add(manga_scanlator)
    db.commit()
    db.refresh(db_manga)

    return db_manga


def update_manga_status(db: Session, manga_id: int, status: str):
    """Update manga reading status"""
    manga = db.query(Manga).filter(Manga.id == manga_id).first()
    if manga:
        manga.status = status
        db.commit()
        db.refresh(manga)
    return manga


def delete_manga(db: Session, manga_id: int):
    """Delete manga"""
    manga = db.query(Manga).filter(Manga.id == manga_id).first()
    if manga:
        db.delete(manga)
        db.commit()
        return True
    return False


# Scanlator CRUD
def get_scanlators(db: Session):
    """Get all scanlators"""
    return db.query(Scanlator).all()


def create_scanlator(db: Session, scanlator: ScanlatorCreate):
    """Create new scanlator"""
    db_scanlator = Scanlator(**scanlator.dict())
    db.add(db_scanlator)
    db.commit()
    db.refresh(db_scanlator)
    return db_scanlator


# Chapter CRUD
def get_recent_chapters(db: Session, limit: int = 50):
    """Get recently detected chapters"""
    return db.query(Chapter).order_by(
        desc(Chapter.detected_date)
    ).limit(limit).all()


def get_unread_chapters(db: Session):
    """Get unread chapters"""
    return db.query(Chapter).filter(Chapter.read == False).order_by(
        desc(Chapter.detected_date)
    ).all()


def mark_chapter_read(db: Session, chapter_id: int, read: bool = True):
    """Mark chapter as read/unread"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if chapter:
        chapter.read = read
        db.commit()
        db.refresh(chapter)
    return chapter


def mark_read_until(db: Session, manga_id: int, chapter_number: str, scanlator_id: int) -> int:
    """Mark all chapters up to and including chapter_number as read"""
    # Get manga_scanlator
    ms = db.query(MangaScanlator).filter_by(
        manga_id=manga_id,
        scanlator_id=scanlator_id
    ).first()

    if not ms:
        return 0

    # Get all chapters for this manga-scanlator
    chapters = db.query(Chapter).filter_by(
        manga_scanlator_id=ms.id
    ).all()

    # Sort by chapter number (convert to float for comparison)
    try:
        target_num = float(chapter_number)
        marked = 0

        for chapter in chapters:
            try:
                ch_num = float(chapter.chapter_number)
                if ch_num <= target_num and not chapter.read:
                    chapter.read = True
                    marked += 1
            except ValueError:
                continue

        db.commit()
        return marked

    except ValueError:
        return 0
```

**Step 2: Create API views**

Create `api/views.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api import crud, schemas
from api.dependencies import get_db

router = APIRouter(prefix="/api", tags=["api"])


# Manga endpoints
@router.get("/mangas", response_model=list[schemas.MangaResponse])
def list_mangas(
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db)
):
    return crud.get_mangas(db, skip=skip, limit=limit, status=status, search=search)


@router.get("/mangas/{manga_id}", response_model=schemas.MangaResponse)
def get_manga(manga_id: int, db: Session = Depends(get_db)):
    manga = crud.get_manga(db, manga_id)
    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")
    return manga


@router.post("/mangas", response_model=schemas.MangaResponse)
def create_manga(manga: schemas.MangaCreate, db: Session = Depends(get_db)):
    return crud.create_manga(db, manga)


@router.put("/mangas/{manga_id}", response_model=schemas.MangaResponse)
def update_manga(manga_id: int, update: schemas.MangaUpdate, db: Session = Depends(get_db)):
    if update.status:
        manga = crud.update_manga_status(db, manga_id, update.status)
        if not manga:
            raise HTTPException(status_code=404, detail="Manga not found")
        return manga
    raise HTTPException(status_code=400, detail="No update provided")


@router.delete("/mangas/{manga_id}")
def delete_manga(manga_id: int, db: Session = Depends(get_db)):
    success = crud.delete_manga(db, manga_id)
    if not success:
        raise HTTPException(status_code=404, detail="Manga not found")
    return {"success": True}


@router.put("/mangas/{manga_id}/read-until")
def mark_read_until(
    manga_id: int,
    payload: schemas.ReadUntilSchema,
    db: Session = Depends(get_db)
):
    count = crud.mark_read_until(db, manga_id, payload.chapter_number, payload.scanlator_id)
    return {"chapters_marked": count}


# Scanlator endpoints
@router.get("/scanlators", response_model=list[schemas.ScanlatorResponse])
def list_scanlators(db: Session = Depends(get_db)):
    return crud.get_scanlators(db)


@router.post("/scanlators", response_model=schemas.ScanlatorResponse)
def create_scanlator(scanlator: schemas.ScanlatorCreate, db: Session = Depends(get_db)):
    return crud.create_scanlator(db, scanlator)


# Chapter endpoints
@router.get("/chapters/recent", response_model=list[schemas.ChapterResponse])
def get_recent_chapters(limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_recent_chapters(db, limit)


@router.get("/chapters/unread", response_model=list[schemas.ChapterResponse])
def get_unread_chapters(db: Session = Depends(get_db)):
    return crud.get_unread_chapters(db)


@router.put("/chapters/{chapter_id}/read")
def mark_chapter_read(chapter_id: int, db: Session = Depends(get_db)):
    chapter = crud.mark_chapter_read(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {"success": True}
```

**Step 3: Register router in main.py**

Modify `api/main.py`, add after `app = FastAPI(...)`:

```python
from api.views import router as api_router

app.include_router(api_router)
```

**Step 4: Test API endpoints**

Run:
```bash
python -m api.main
```

Visit http://localhost:8000/docs and test each endpoint.

**Step 5: Commit**

```bash
git add api/crud.py api/views.py
git commit -m "feat: implement API CRUD operations for mangas, scanlators, chapters"
```

---

### Task 9: Check Updates API Endpoint

**Files:**
- Modify: `api/views.py`
- Create: `api/tracking.py`

**Step 1: Create tracking module for API**

Create `api/tracking.py`:

```python
"""Tracking logic callable from API"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from loguru import logger

from api.database import SessionLocal
from api.models import MangaScanlator, Chapter, ScrapingError
from scanlators import discover_scanlators


async def check_updates_for_manga(manga_id: int | None = None) -> dict:
    """
    Check for updates. If manga_id provided, only check that manga.

    Returns:
        {
            "new_chapters": int,
            "errors": int,
            "details": [...]
        }
    """
    scanlator_classes = discover_scanlators()

    db = SessionLocal()
    query = db.query(MangaScanlator).join(MangaScanlator.scanlator).filter(
        MangaScanlator.manually_verified == True,
        MangaScanlator.scanlator.has(active=True)
    )

    if manga_id:
        query = query.filter(MangaScanlator.manga_id == manga_id)

    manga_scanlators = query.all()
    db.close()

    new_chapters_count = 0
    errors_count = 0
    details = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for ms in manga_scanlators:
            scanlator_class = scanlator_classes.get(ms.scanlator.class_name)

            if not scanlator_class:
                errors_count += 1
                continue

            try:
                scanlator = scanlator_class(page)
                current_chapters = await scanlator.obtener_capitulos(ms.scanlator_manga_url)

                db = SessionLocal()
                existing_numbers = {
                    ch.chapter_number
                    for ch in db.query(Chapter).filter_by(manga_scanlator_id=ms.id).all()
                }

                for chapter_data in current_chapters:
                    if chapter_data['numero'] not in existing_numbers:
                        new_chapter = Chapter(
                            manga_scanlator_id=ms.id,
                            chapter_number=chapter_data['numero'],
                            chapter_title=chapter_data.get('titulo'),
                            chapter_url=chapter_data['url'],
                            published_date=chapter_data.get('fecha'),
                            detected_date=datetime.utcnow(),
                            read=False
                        )
                        db.add(new_chapter)
                        new_chapters_count += 1

                        details.append({
                            "manga": ms.manga.title,
                            "chapter": chapter_data['numero'],
                            "scanlator": ms.scanlator.name
                        })

                ms.manga.last_checked = datetime.utcnow()
                db.commit()
                db.close()

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error checking {ms.manga.title}: {e}")
                errors_count += 1

                db = SessionLocal()
                error = ScrapingError(
                    manga_scanlator_id=ms.id,
                    error_type="api_check_failed",
                    error_message=str(e),
                    timestamp=datetime.utcnow()
                )
                db.add(error)
                db.commit()
                db.close()

        await browser.close()

    return {
        "new_chapters": new_chapters_count,
        "errors": errors_count,
        "details": details
    }
```

**Step 2: Add endpoint to views**

Add to `api/views.py`:

```python
from api.tracking import check_updates_for_manga


@router.post("/check-updates")
async def check_updates():
    """Check all mangas for new chapters"""
    result = await check_updates_for_manga()
    return result


@router.post("/check-updates/{manga_id}")
async def check_updates_single(manga_id: int):
    """Check specific manga for new chapters"""
    result = await check_updates_for_manga(manga_id)
    return result
```

**Step 3: Test endpoint**

Run API, visit http://localhost:8000/docs

POST to `/api/check-updates`

Expected: Response with new chapters found.

**Step 4: Commit**

```bash
git add api/tracking.py api/views.py
git commit -m "feat: add check-updates API endpoint"
```

---

## PHASE 4: FRONTEND (Days 11-13)

### Task 10: Astro Setup

**Files:**
- Create: `frontend/` (new Astro project)

**Step 1: Create Astro project**

Run:
```bash
npm create astro@latest frontend
```

Choose:
- Template: Empty
- TypeScript: Yes
- Install dependencies: Yes

**Step 2: Install Tailwind**

```bash
cd frontend
npx astro add tailwind
```

**Step 3: Configure API base URL**

Create `frontend/src/config.ts`:

```typescript
export const API_BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
```

Add to `frontend/.env`:
```
PUBLIC_API_URL=http://localhost:8000
```

**Step 4: Create base layout**

Create `frontend/src/layouts/Layout.astro`:

```astro
---
interface Props {
  title: string;
}

const { title } = Astro.props;
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} - Manga Tracker</title>
  </head>
  <body class="bg-gray-100 min-h-screen">
    <nav class="bg-white shadow-lg">
      <div class="container mx-auto px-4 py-4">
        <div class="flex justify-between items-center">
          <a href="/" class="text-2xl font-bold">Manga Tracker</a>
          <div class="space-x-4">
            <a href="/" class="hover:text-blue-600">Home</a>
            <a href="/recent" class="hover:text-blue-600">Recent</a>
            <a href="/scanlators" class="hover:text-blue-600">Scanlators</a>
            <a href="/admin" class="hover:text-blue-600">Admin</a>
          </div>
        </div>
      </div>
    </nav>

    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>
  </body>
</html>
```

**Step 5: Test Astro dev server**

Run:
```bash
npm run dev
```

Visit: http://localhost:4321

**Step 6: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: setup Astro frontend with Tailwind"
```

---

### Task 11: Homepage with Manga Grid

**Files:**
- Create: `frontend/src/pages/index.astro`
- Create: `frontend/src/components/MangaCard.astro`

**Step 1: Create MangaCard component**

Create `frontend/src/components/MangaCard.astro`:

```astro
---
interface Props {
  id: number;
  title: string;
  coverFilename: string;
  unreadCount?: number;
}

const { id, title, coverFilename, unreadCount = 0 } = Astro.props;
const coverUrl = coverFilename ? `/data/img/${coverFilename}` : '/placeholder.png';
---

<a href={`/manga/${id}`} class="block group">
  <div class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition">
    <div class="relative">
      <img
        src={coverUrl}
        alt={title}
        class="w-full h-64 object-cover"
      />
      {unreadCount > 0 && (
        <span class="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded-full text-sm font-bold">
          {unreadCount}
        </span>
      )}
    </div>
    <div class="p-4">
      <h3 class="font-semibold text-lg truncate group-hover:text-blue-600">
        {title}
      </h3>
    </div>
  </div>
</a>
```

**Step 2: Create homepage**

Create `frontend/src/pages/index.astro`:

```astro
---
import Layout from '../layouts/Layout.astro';
import MangaCard from '../components/MangaCard.astro';
import { API_BASE_URL } from '../config';

// Fetch mangas from API
const response = await fetch(`${API_BASE_URL}/api/mangas`);
const mangas = await response.json();
---

<Layout title="My Manga Library">
  <div class="mb-6">
    <h1 class="text-3xl font-bold mb-4">My Manga Library</h1>

    <div class="flex gap-4 mb-4">
      <input
        type="text"
        placeholder="Search manga..."
        class="flex-1 px-4 py-2 border rounded-lg"
      />
      <select class="px-4 py-2 border rounded-lg">
        <option value="">All Status</option>
        <option value="reading">Reading</option>
        <option value="completed">Completed</option>
        <option value="on_hold">On Hold</option>
        <option value="plan_to_read">Plan to Read</option>
      </select>
    </div>
  </div>

  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
    {mangas.map((manga: any) => (
      <MangaCard
        id={manga.id}
        title={manga.title}
        coverFilename={manga.cover_filename}
        unreadCount={0}
      />
    ))}
  </div>
</Layout>
```

**Step 3: Test homepage**

Run:
```bash
cd frontend
npm run dev
```

Visit: http://localhost:4321

Expected: Grid of manga covers.

**Step 4: Commit**

```bash
git add frontend/src/pages/index.astro frontend/src/components/MangaCard.astro
git commit -m "feat: implement homepage with manga grid"
```

---

### Task 12: Manga Detail Page

**Files:**
- Create: `frontend/src/pages/manga/[id].astro`
- Create: `frontend/src/components/ChapterList.astro`

**Step 1: Create ChapterList component**

Create `frontend/src/components/ChapterList.astro`:

```astro
---
interface Props {
  chapters: any[];
  mangaId: number;
  scanlatorId: number;
}

const { chapters, mangaId, scanlatorId } = Astro.props;
---

<div class="bg-white rounded-lg shadow p-4">
  <table class="w-full">
    <thead>
      <tr class="border-b">
        <th class="text-left py-2">Chapter</th>
        <th class="text-left py-2">Title</th>
        <th class="text-left py-2">Detected</th>
        <th class="text-right py-2">Actions</th>
      </tr>
    </thead>
    <tbody>
      {chapters.map((chapter) => (
        <tr class="border-b hover:bg-gray-50">
          <td class="py-2">{chapter.chapter_number}</td>
          <td class="py-2">{chapter.chapter_title || '-'}</td>
          <td class="py-2">{new Date(chapter.detected_date).toLocaleDateString()}</td>
          <td class="py-2 text-right space-x-2">
            <a
              href={chapter.chapter_url}
              target="_blank"
              class="text-blue-600 hover:underline"
            >
              Read
            </a>
            <button
              class="text-green-600 hover:underline"
              data-chapter-id={chapter.id}
              onclick="markRead(this)"
            >
              Mark Read
            </button>
          </td>
        </tr>
      ))}
    </tbody>
  </table>

  {chapters.length > 0 && (
    <div class="mt-4">
      <button
        class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        data-manga-id={mangaId}
        data-scanlator-id={scanlatorId}
        data-chapter-number={chapters[chapters.length - 1].chapter_number}
        onclick="markReadUntil(this)"
      >
        Mark All as Read
      </button>
    </div>
  )}
</div>

<script>
  import { API_BASE_URL } from '../config';

  window.markRead = async function(button) {
    const chapterId = button.dataset.chapterId;
    const response = await fetch(`${API_BASE_URL}/api/chapters/${chapterId}/read`, {
      method: 'PUT'
    });

    if (response.ok) {
      button.textContent = '✓ Read';
      button.disabled = true;
    }
  }

  window.markReadUntil = async function(button) {
    const mangaId = button.dataset.mangaId;
    const scanlatorId = button.dataset.scanlatorId;
    const chapterNumber = button.dataset.chapterNumber;

    const response = await fetch(`${API_BASE_URL}/api/mangas/${mangaId}/read-until`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chapter_number: chapterNumber,
        scanlator_id: parseInt(scanlatorId)
      })
    });

    if (response.ok) {
      const data = await response.json();
      alert(`Marked ${data.chapters_marked} chapters as read`);
      location.reload();
    }
  }
</script>
```

**Step 2: Create detail page**

Create `frontend/src/pages/manga/[id].astro`:

```astro
---
import Layout from '../../layouts/Layout.astro';
import ChapterList from '../../components/ChapterList.astro';
import { API_BASE_URL } from '../../config';

const { id } = Astro.params;

const mangaResponse = await fetch(`${API_BASE_URL}/api/mangas/${id}`);
const manga = await mangaResponse.json();

// For now, mock chapters - you'll need an endpoint that returns manga with chapters
const chapters: any[] = [];
---

<Layout title={manga.title}>
  <div class="grid md:grid-cols-3 gap-6">
    <div class="md:col-span-1">
      <img
        src={manga.cover_filename ? `/data/img/${manga.cover_filename}` : '/placeholder.png'}
        alt={manga.title}
        class="w-full rounded-lg shadow-lg"
      />
    </div>

    <div class="md:col-span-2">
      <h1 class="text-4xl font-bold mb-2">{manga.title}</h1>
      {manga.alternative_titles && (
        <p class="text-gray-600 mb-4">{manga.alternative_titles}</p>
      )}

      <div class="mb-4">
        <label class="block text-sm font-medium mb-2">Status:</label>
        <select class="px-4 py-2 border rounded-lg">
          <option value="reading" selected={manga.status === 'reading'}>Reading</option>
          <option value="completed" selected={manga.status === 'completed'}>Completed</option>
          <option value="on_hold" selected={manga.status === 'on_hold'}>On Hold</option>
          <option value="plan_to_read" selected={manga.status === 'plan_to_read'}>Plan to Read</option>
        </select>
      </div>

      <div class="mt-6">
        <h2 class="text-2xl font-bold mb-4">Chapters</h2>
        <ChapterList chapters={chapters} mangaId={manga.id} scanlatorId={1} />
      </div>
    </div>
  </div>
</Layout>
```

**Step 3: Test detail page**

Click on a manga from homepage.

Expected: Detail page with manga info.

**Step 4: Commit**

```bash
git add frontend/src/pages/manga/ frontend/src/components/ChapterList.astro
git commit -m "feat: implement manga detail page with chapter list"
```

---

## PHASE 5: AUTOMATION (Day 14)

### Task 13: n8n Workflow

**Files:**
- Create: `n8n/workflows/check-updates.json`
- Create: `n8n/README.md`

**Step 1: Create workflow JSON**

Create `n8n/workflows/check-updates.json`:

```json
{
  "name": "Manga Tracker - Check Updates",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 6
            }
          ]
        }
      },
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/api/check-updates",
        "options": {}
      },
      "name": "Check Updates API",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [450, 300]
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{$json.new_chapters}}",
              "operation": "larger",
              "value2": 0
            }
          ]
        }
      },
      "name": "Has New Chapters?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [650, 300]
    },
    {
      "parameters": {
        "webhookUrl": "={{$env.DISCORD_WEBHOOK_URL}}",
        "text": "=🆕 {{$json.new_chapters}} new manga chapters detected!\n\nDetails:\n{{$json.details.map(d => `- ${d.manga} Ch. ${d.chapter} (${d.scanlator})`).join('\\n')}}"
      },
      "name": "Send Discord Notification",
      "type": "n8n-nodes-base.discord",
      "typeVersion": 1,
      "position": [850, 200]
    }
  ],
  "connections": {
    "Schedule Trigger": {
      "main": [[{"node": "Check Updates API", "type": "main", "index": 0}]]
    },
    "Check Updates API": {
      "main": [[{"node": "Has New Chapters?", "type": "main", "index": 0}]]
    },
    "Has New Chapters?": {
      "main": [[{"node": "Send Discord Notification", "type": "main", "index": 0}], []]
    }
  }
}
```

**Step 2: Create README**

Create `n8n/README.md`:

```markdown
# n8n Workflows for Manga Tracker

## Setup

1. Install n8n: `npm install -g n8n`
2. Run n8n: `n8n start`
3. Import workflow: Copy `check-updates.json` content in n8n UI
4. Set environment variables in n8n:
   - `DISCORD_WEBHOOK_URL` (or configure email/telegram)

## Workflows

### check-updates.json

Checks for new manga chapters every 6 hours and sends notifications.

**Trigger:** Schedule (every 6 hours)
**Steps:**
1. Call `/api/check-updates`
2. If new chapters found
3. Send notification to Discord/Email/Telegram

**Customization:**
- Change schedule interval in "Schedule Trigger" node
- Change notification method (Discord/Email/Telegram node)
```

**Step 3: Test manually (optional)**

If you have n8n running:
1. Import the workflow
2. Set webhook URL
3. Execute manually
4. Verify notification

**Step 4: Commit**

```bash
git add n8n/
git commit -m "feat: add n8n workflow for automated tracking"
```

---

## PHASE 6: DOCUMENTATION (Day 15)

### Task 14: Project Documentation

**Files:**
- Create: `README.md`
- Create: `CLAUDE.md`
- Create: `.gitignore`

**Step 1: Create comprehensive README**

Create `README.md`:

```markdown
# Manga Tracker

Self-hosted manga tracking system that follows your favorite manga across multiple scanlation groups with automated chapter detection and notifications.

## Features

- 📚 Track manga from multiple scanlation sources
- 🔄 Automatic chapter detection
- 🔔 Notifications (Discord/Telegram/Email)
- 🎨 Clean web interface (Astro)
- 🔌 Extensible scanlator plugin system
- 📊 Read progress tracking

## Quick Start

### Prerequisites

- Python 3.11+
- MariaDB 10.6+
- Node.js 18+
- n8n (optional, for automation)

### Setup

1. **Database Setup**

```bash
mysql -u root -p < scripts/create_db.sql
```

2. **Backend Setup**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

3. **Configure Environment**

```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. **Extract MangaTaro Data** (if applicable)

```bash
python scripts/extract_mangataro.py
```

5. **Start API**

```bash
python -m api.main
```

6. **Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

7. **n8n Setup** (optional)

```bash
npm install -g n8n
n8n start
# Import workflow from n8n/workflows/check-updates.json
```

## Usage

### Adding Manga Sources

```bash
python scripts/add_manga_source.py
```

### Manual Chapter Check

```bash
python scripts/check_updates.py
```

### Adding New Scanlator

1. Copy `scanlators/template.py` to `scanlators/yourscanlator.py`
2. Implement the three methods
3. Register in database via API or script

## Project Structure

```
mangataro/
├── api/          # FastAPI backend
├── scanlators/   # Scanlator plugins
├── scripts/      # Utility scripts
├── frontend/     # Astro frontend
├── n8n/          # Automation workflows
├── data/         # Images and exports
└── docs/         # Documentation
```

## API Endpoints

- `GET /api/mangas` - List mangas
- `POST /api/mangas` - Add manga
- `GET /api/chapters/recent` - Recent chapters
- `POST /api/check-updates` - Trigger update check
- `PUT /api/mangas/{id}/read-until` - Binge reading

See http://localhost:8000/docs for full API documentation.

## Contributing

This is a personal project, but feel free to fork and adapt for your needs.

## License

MIT
```

**Step 2: Create CLAUDE.md**

Create `CLAUDE.md`:

```markdown
# CLAUDE.md - Project Memory

## Architecture Decisions

### Why Playwright over Requests?

MangaTaro and scanlation sites use JavaScript heavily. Playwright renders the full DOM like a browser, ensuring we capture all dynamically loaded content. Trade-off: slower, more resources.

### Why Plugin Architecture for Scanlators?

Each scanlation site has unique HTML structure. Plugin system allows:
- Adding new scanlators without touching core code
- Isolating failures (one broken scraper doesn't affect others)
- Easy maintenance (update one file per scanlator)

### Why MariaDB over SQLite?

- User already has MariaDB running
- Better for concurrent access (API + n8n)
- Supports complex queries efficiently
- Handles UTF-8 manga titles properly

## Code Conventions

### Scanlators

- One class per file in `scanlators/`
- Must inherit from `BaseScanlator`
- Implement all three abstract methods
- Use async/await for Playwright operations
- Add error handling with try/except

### API

- `views.py`: Endpoints, input validation, response formatting
- `crud.py`: Business logic, database queries
- `schemas.py`: Pydantic models for validation
- `models.py`: SQLAlchemy ORM models

### Frontend

- Astro for SSG/SSR
- Tailwind for styling
- Fetch API for backend calls
- TypeScript for type safety

## Adding New Scanlator

1. Copy `scanlators/template.py`
2. Rename class and file
3. Set `name` and `base_url`
4. Implement:
   - `buscar_manga()`: Search functionality
   - `obtener_capitulos()`: Extract chapter list
   - `parsear_numero_capitulo()`: Normalize chapter numbers
5. Test with `test_scanlator.py`
6. Register in DB: `POST /api/scanlators`

## Known Issues

- Some scanlators use Cloudflare/captcha (mark as `active=false`)
- Chapter numbers can be inconsistent (handle in parser)
- Images may fail to download (fallback to placeholder)

## Environment Variables

Required:
- `DB_*`: Database credentials
- `PLAYWRIGHT_TIMEOUT`: Scraping timeout
- `NOTIFICATION_TYPE`: discord/telegram/email

Optional:
- `SCRAPING_DELAY_MIN/MAX`: Politeness delays
- n8n webhook URL for automation

## Future Improvements

- Add support for RSS feeds where available
- Implement manga recommendation based on reading history
- Add mobile app (React Native?)
- Support for reading lists/collections
```

**Step 3: Create .gitignore**

Create `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
.venv/
.env
*.log

# Node
node_modules/
.astro/
dist/

# Data
data/img/
logs/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Playwright
playwright-report/
test-results/
```

**Step 4: Commit**

```bash
git add README.md CLAUDE.md .gitignore
git commit -m "docs: add comprehensive project documentation"
```

---

## Execution Summary

Plan complete! This implementation plan covers:

✅ **Phase 1 (Days 1-3)**: Urgent MangaTaro extraction
- Database setup with MariaDB
- Extraction script with Playwright
- Manual URL mapping helper

✅ **Phase 2 (Days 4-7)**: Tracking system
- Plugin architecture for scanlators
- Auto-discovery system
- Chapter tracking script
- Example scanlator implementations

✅ **Phase 3 (Days 8-10)**: FastAPI backend
- Complete CRUD operations
- Pydantic schemas
- Check-updates endpoint
- API documentation

✅ **Phase 4 (Days 11-13)**: Astro frontend
- Homepage with manga grid
- Detail pages with chapter lists
- Binge reading functionality
- Responsive design with Tailwind

✅ **Phase 5 (Day 14)**: n8n automation
- Scheduled workflow
- Discord/Telegram/Email notifications
- Error handling

✅ **Phase 6 (Day 15)**: Documentation
- Comprehensive README
- CLAUDE.md for project memory
- Code comments and examples

Each task is broken into 2-5 minute steps with exact file paths, code, and commands.
