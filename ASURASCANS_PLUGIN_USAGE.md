# AsuraScans Plugin Usage Guide

## Quick Start

### Running the Test Suite

```bash
# Run with visible browser
python scripts/test_asura_scans.py

# Run in headless mode (faster)
python scripts/test_asura_scans.py --headless

# Search for specific manga
python scripts/test_asura_scans.py --headless --search "one piece"

# Test specific manga URL (skip search)
python scripts/test_asura_scans.py --headless --manga-url "https://asuracomic.net/series/..."
```

## Usage in Python Code

### Basic Usage

```python
import asyncio
from playwright.async_api import async_playwright
from scanlators.asura_scans import AsuraScans

async def main():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Initialize plugin
        scanlator = AsuraScans(page)

        # Search for manga
        results = await scanlator.buscar_manga("solo leveling")
        print(f"Found {len(results)} manga")

        for result in results:
            print(f"- {result['titulo']}: {result['url']}")

        # Get chapters from first result
        if results:
            chapters = await scanlator.obtener_capitulos(results[0]['url'])
            print(f"\nFound {len(chapters)} chapters:")

            for chapter in chapters[:5]:  # Show first 5
                print(f"  Ch. {chapter['numero']}: {chapter['titulo']}")
                print(f"    URL: {chapter['url']}")
                print(f"    Date: {chapter['fecha']}")

        await browser.close()

asyncio.run(main())
```

### Parse Chapter Numbers

```python
from scanlators.asura_scans import AsuraScans
from playwright.async_api import Page

# You still need a Page instance, but parsear_numero_capitulo doesn't use it
scanlator = AsuraScans(page)

# Parse various formats
print(scanlator.parsear_numero_capitulo("Chapter 42"))      # "42"
print(scanlator.parsear_numero_capitulo("Ch. 42.5"))        # "42.5"
print(scanlator.parsear_numero_capitulo("First Chapter"))   # "1"
print(scanlator.parsear_numero_capitulo("Episode 100"))     # "100"
```

## Method Reference

### buscar_manga(titulo: str) -> list[dict]

Search for manga by title on AsuraScans.

**Parameters:**
- `titulo` (str): The manga title to search for

**Returns:**
- `list[dict]`: List of manga results, each containing:
  - `titulo` (str): Manga title (genre tags filtered out)
  - `url` (str): Full URL to the manga page
  - `portada` (str): Cover image URL

**Example:**
```python
results = await scanlator.buscar_manga("solo leveling")
# [
#   {
#     'titulo': 'Solo Leveling: Ragnarok',
#     'url': 'https://asuracomic.net/series/solo-leveling-ragnarok-55b73268',
#     'portada': 'https://gg.asuracomic.net/...'
#   }
# ]
```

### obtener_capitulos(manga_url: str) -> list[dict]

Extract all chapters from a manga page.

**Parameters:**
- `manga_url` (str): Full URL to the manga's page

**Returns:**
- `list[dict]`: List of chapters (sorted oldest to newest), each containing:
  - `numero` (str): Normalized chapter number (e.g., "42", "42.5")
  - `titulo` (str): Chapter title/name
  - `url` (str): Full URL to the chapter
  - `fecha` (datetime): Publication date

**Features:**
- Automatically clicks "All" tab to show all chapters
- Deduplicates chapters
- Sorts numerically when possible

**Example:**
```python
chapters = await scanlator.obtener_capitulos(
    "https://asuracomic.net/series/solo-leveling-ragnarok-55b73268"
)
# [
#   {
#     'numero': '1',
#     'titulo': 'First Chapter',
#     'url': 'https://asuracomic.net/series/.../chapter/1',
#     'fecha': datetime(2026, 1, 15, 12, 30)
#   },
#   ...
# ]
```

### parsear_numero_capitulo(texto: str) -> str

Parse and normalize chapter numbers from various text formats.

**Parameters:**
- `texto` (str): Raw text containing the chapter number

**Returns:**
- `str`: Normalized chapter number (e.g., "42", "42.5")

**Supported Formats:**
- "Chapter 42" → "42"
- "Ch. 42.5" → "42.5"
- "First Chapter" → "1"
- "Episode 100" → "100"
- "Ch.200" → "200"
- "Chapter 42: Title" → "42"

**Example:**
```python
num = scanlator.parsear_numero_capitulo("Chapter 42.5: The Battle")
# "42.5"
```

## Advanced Features

### Date Parsing

The plugin automatically parses dates in various formats:

- Relative: "2 days ago", "1 week ago", "3 hours ago"
- Absolute: "January 15th 2026", "2026-01-15"
- Special: "yesterday", "today"

### Error Handling

All methods include comprehensive error handling:

```python
try:
    results = await scanlator.buscar_manga("test")
    if not results:
        print("No results found")
except Exception as e:
    print(f"Error: {e}")
```

### Logging

The plugin uses `loguru` for logging. Set log level as needed:

```python
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="DEBUG")  # Show debug messages
```

## Test Results

Recent test with "Return of the Mount Hua Sect":
- ✅ Found 1 manga result
- ✅ Extracted 157 chapters
- ✅ Handles decimal chapters (152.1, 152.2, etc.)
- ✅ Proper sorting from chapter 1 to 152.4

Recent test with "Solo Leveling":
- ✅ Found 2 manga results
- ✅ Extracted 68 chapters
- ✅ All chapter number parsing tests passed

## Performance Notes

- Search: ~2-4 seconds
- Chapter extraction: ~4-6 seconds (depends on number of chapters)
- Uses headless mode by default for better performance

## Troubleshooting

### TimeoutError

If you get timeout errors, increase the timeout:

```python
# In base.py safe_goto() or when waiting for selectors
await self.page.wait_for_selector(".grid", timeout=15000)  # 15 seconds
```

### No Results Found

- Check if the website is accessible
- Try a different search term
- Verify the website structure hasn't changed
- Enable debug logging to see what's happening

### Incorrect Chapter Numbers

- Check the `parsear_numero_capitulo()` method
- Add new patterns to the regex if needed
- Submit an issue with the problematic format

## Integration Example

Integrate with the database:

```python
from api.database import SessionLocal
from api.models import Manga, Chapter
from scanlators.asura_scans import AsuraScans

async def update_manga_chapters(manga_id: int):
    db = SessionLocal()
    manga = db.query(Manga).filter(Manga.id == manga_id).first()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        scanlator = AsuraScans(page)
        chapters = await scanlator.obtener_capitulos(manga.scanlator_url)

        for cap in chapters:
            # Add or update chapter in database
            chapter = Chapter(
                manga_id=manga.id,
                chapter_number=cap['numero'],
                title=cap['titulo'],
                url=cap['url'],
                published_date=cap['fecha']
            )
            db.add(chapter)

        db.commit()
        await browser.close()
```

## File Locations

- **Plugin**: `/data/mangataro/scanlators/asura_scans.py` (360 lines)
- **Test**: `/data/mangataro/scripts/test_asura_scans.py` (249 lines)
- **Base Class**: `/data/mangataro/scanlators/base.py`
- **Template**: `/data/mangataro/scanlators/template.py`

## Next Steps

Use this plugin as a reference for implementing other scanlators:
1. Copy `template.py` to `your_scanlator.py`
2. Follow the same pattern as AsuraScans
3. Test thoroughly with the test script pattern
4. Document any quirks specific to that scanlator
