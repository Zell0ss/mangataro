# Scanlator Plugin Quick Reference

One-page cheat sheet for adding a new scanlator plugin. Copy, modify, test, done.

## Step 1: Create Plugin File

```bash
cp scanlators/template.py scanlators/yoursite.py
```

## Step 2: Basic Setup

```python
from playwright.async_api import Page
from scanlators.base import BaseScanlator
from datetime import datetime
import re

class YourSite(BaseScanlator):
    def __init__(self, playwright_page: Page):
        super().__init__(playwright_page)
        self.name = "YourSite"
        self.base_url = "https://yoursite.com"
```

## Step 3: Implement Search

```python
async def buscar_manga(self, titulo: str) -> list[dict]:
    """Search for manga by title"""
    # 1. Build search URL
    search_url = f"{self.base_url}/search?q={titulo}"

    # 2. Navigate safely
    if not await self.safe_goto(search_url):
        return []

    # 3. Wait for results (CHANGE THIS SELECTOR)
    await self.page.wait_for_selector(".manga-card", timeout=10000)

    # 4. Extract results (CHANGE THESE SELECTORS)
    items = await self.page.locator(".manga-card").all()
    resultados = []

    for item in items:
        titulo = await item.locator(".title").text_content()
        url = await item.locator("a").get_attribute("href")
        portada = await item.locator("img").get_attribute("src")

        # 5. Return Spanish field names!
        resultados.append({
            "titulo": titulo.strip(),
            "url": url.strip() if url.startswith("http") else f"{self.base_url}{url}",
            "portada": portada
        })

    return resultados
```

## Step 4: Implement Chapter Extraction

```python
async def obtener_capitulos(self, manga_url: str) -> list[dict]:
    """Get all chapters from manga page"""
    if not await self.safe_goto(manga_url):
        return []

    # Wait for chapter list (CHANGE THIS SELECTOR)
    await self.page.wait_for_selector(".chapter-item", timeout=10000)

    items = await self.page.locator(".chapter-item").all()
    capitulos = []

    for item in items:
        # Extract chapter info (CHANGE THESE SELECTORS)
        link = item.locator("a").first  # .first is property, not async!
        titulo = await link.text_content()
        url = await link.get_attribute("href")

        # Parse chapter number
        numero = self.parsear_numero_capitulo(titulo)

        # Parse date (site-specific format)
        fecha_texto = await item.locator(".date").text_content()
        fecha = self._parse_date(fecha_texto.strip())

        # Return Spanish field names!
        capitulos.append({
            "numero": numero,
            "titulo": titulo.strip(),
            "url": url.strip() if url.startswith("http") else f"{self.base_url}{url}",
            "fecha": fecha
        })

    # Sort oldest to newest
    capitulos.sort(key=lambda x: (float(x["numero"]), x["fecha"]))
    return capitulos
```

## Step 5: Implement Chapter Number Parsing

```python
def parsear_numero_capitulo(self, texto: str) -> str:
    """Extract chapter number from text"""
    # Common patterns (choose one or write custom)

    # Pattern 1: "Chapter 42" or "Ch. 42.5"
    match = re.search(r'chapter\s*(\d+(?:\.\d+)?)', texto, re.I)

    # Pattern 2: "Episode 42" or "Ep. 42"
    # match = re.search(r'episode\s*(\d+(?:\.\d+)?)', texto, re.I)

    # Pattern 3: Just numbers "42" or "42.5"
    # match = re.search(r'(\d+(?:\.\d+)?)', texto)

    return match.group(1) if match else "0"
```

## Step 6: Helper Method for Date Parsing

```python
def _parse_date(self, texto: str) -> datetime:
    """Parse date from scanlator-specific format"""
    try:
        # Example 1: "January 15, 2025"
        return datetime.strptime(texto, "%B %d, %Y")

        # Example 2: "2025-01-15"
        # return datetime.strptime(texto, "%Y-%m-%d")

        # Example 3: "15/01/2025"
        # return datetime.strptime(texto, "%d/%m/%Y")

    except:
        # Fallback to current time if parsing fails
        return datetime.now()
```

---

## Common Patterns

### Handle Relative Dates

```python
def _parse_date(self, texto: str) -> datetime:
    """Parse dates like '3 days ago', 'yesterday', etc."""
    from datetime import timedelta

    texto = texto.lower()

    # Today/yesterday
    if "today" in texto or "just now" in texto:
        return datetime.now()
    if "yesterday" in texto:
        return datetime.now() - timedelta(days=1)

    # "X days/hours ago"
    match = re.search(r'(\d+)\s*(day|hour|minute)s?\s*ago', texto)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "day":
            return datetime.now() - timedelta(days=value)
        elif unit == "hour":
            return datetime.now() - timedelta(hours=value)
        elif unit == "minute":
            return datetime.now() - timedelta(minutes=value)

    # Fallback: try standard date formats
    for fmt in ["%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(texto, fmt)
        except:
            continue

    # Final fallback
    return datetime.now()
```

### Handle Pagination

```python
async def obtener_capitulos(self, manga_url: str) -> list[dict]:
    """Get chapters across multiple pages"""
    capitulos = []
    page_num = 1

    while True:
        # Build paginated URL
        url = f"{manga_url}?page={page_num}"
        if not await self.safe_goto(url):
            break

        # Wait for chapters
        await self.page.wait_for_selector(".chapter", timeout=5000)

        # Extract chapters from current page
        items = await self.page.locator(".chapter").all()
        if not items:
            break  # No more pages

        for item in items:
            # ... extract chapter data ...
            capitulos.append({...})

        page_num += 1

        # Safety limit
        if page_num > 50:
            break

    return capitulos
```

### Handle JavaScript-Rendered Content

```python
async def obtener_capitulos(self, manga_url: str) -> list[dict]:
    """For sites that render chapters with JavaScript"""
    if not await self.safe_goto(manga_url):
        return []

    # Wait for JavaScript to finish rendering
    await self.page.wait_for_selector(".chapter-list", timeout=10000)

    # Optional: wait for specific element count
    await self.page.wait_for_function(
        "document.querySelectorAll('.chapter').length > 0"
    )

    # Now extract chapters
    items = await self.page.locator(".chapter").all()
    # ... rest of extraction ...
```

---

## Selector Tips

### Finding Selectors

1. **Open browser DevTools** (F12)
2. **Click inspector** (arrow icon)
3. **Click element** on page
4. **Right-click in Elements tab** → Copy → Copy Selector

### Testing Selectors

In browser console:
```javascript
// Test if selector finds elements
document.querySelectorAll(".your-selector")

// Count how many
document.querySelectorAll(".your-selector").length

// Get text content
document.querySelector(".your-selector").textContent
```

### Selector Preferences

- ✅ **Good:** `.chapter-title`, `#manga-list`, `[data-chapter]`
- ⚠️ **OK:** `.container > .item:nth-child(2)`
- ❌ **Bad:** `body > div > div > div > span` (too fragile)

---

## Testing Your Plugin

### Quick Test Script

```python
# scripts/test_yoursite.py
import asyncio
from playwright.async_api import async_playwright
from scanlators.yoursite import YourSite

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        page = await browser.new_page()

        plugin = YourSite(page)

        # Test search
        print("Testing search...")
        results = await plugin.buscar_manga("solo leveling")
        print(f"Found {len(results)} manga")
        for r in results[:3]:
            print(f"  - {r['titulo']}: {r['url']}")

        # Test chapter extraction
        if results:
            print(f"\nTesting chapter extraction on: {results[0]['titulo']}")
            chapters = await plugin.obtener_capitulos(results[0]['url'])
            print(f"Found {len(chapters)} chapters")
            for ch in chapters[:5]:
                print(f"  Ch. {ch['numero']}: {ch['titulo']} ({ch['fecha'].strftime('%Y-%m-%d')})")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Run Test

```bash
python scripts/test_yoursite.py
```

### Integration Test

```bash
# 1. Add scanlator to database
mysql -u mangataro_user -p mangataro << EOF
INSERT INTO scanlators (name, base_url, class_name, active)
VALUES ('Your Site', 'https://yoursite.com', 'YourSite', 1);
EOF

# 2. Test with tracking script
python scripts/track_chapters.py --scanlator-id <id> --limit 1 --visible
```

---

## Critical Gotchas

⚠️ **Always use Spanish field names:**
- ✅ `"numero"`, `"titulo"`, `"url"`, `"fecha"`
- ❌ `"number"`, `"title"`, `"url"`, `"date"`

⚠️ **Pass Playwright page to constructor:**
- ✅ `plugin = YourSite(page)`
- ❌ `plugin = YourSite()` (crashes!)

⚠️ **Use class_name not name in database:**
- ✅ `class_name = "YourSite"` (matches Python class)
- ❌ `class_name = "Your Site"` (won't find plugin!)

⚠️ **Everything is async except parsear_numero_capitulo:**
- ✅ `async def buscar_manga(...)`, `async def obtener_capitulos(...)`
- ✅ `def parsear_numero_capitulo(...)` (NOT async!)

⚠️ **Locator `.first` is a property:**
- ✅ `link = item.locator("a").first` (no await)
- ❌ `link = await item.locator("a").first` (error!)

⚠️ **Locator `.all()` is async:**
- ✅ `items = await page.locator(".chapter").all()`
- ❌ `items = page.locator(".chapter").all()` (missing await!)

---

## Add to Database

```sql
INSERT INTO scanlators (name, base_url, class_name, active)
VALUES ('Your Site Name', 'https://yoursite.com', 'YourSite', 1);
```

**Remember:**
- `name` = Display name (for UI)
- `class_name` = Python class name (MUST match exactly!)
- `active` = 1 to enable

---

## Complete Example: AsuraScans

See [scanlators/asura_scans.py](../scanlators/asura_scans.py) for a working example.

**Key features:**
- Search implementation
- Chapter extraction with date parsing
- Handles standard date format: "January 15, 2025"
- Simple regex for chapter numbers

## Complete Example: RavenScans

See [scanlators/raven_scans.py](../scanlators/raven_scans.py) for JavaScript-rendered content.

**Key features:**
- Waits for `.chbox` JavaScript rendering
- Handles relative dates
- Note: `.first` is property not async method

---

## Need Help?

- **Template:** [scanlators/template.py](../scanlators/template.py)
- **Base class:** [scanlators/base.py](../scanlators/base.py)
- **Developer Guide:** [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Examples:** [scanlators/asura_scans.py](../scanlators/asura_scans.py), [scanlators/raven_scans.py](../scanlators/raven_scans.py)

Happy plugin development! 🚀
