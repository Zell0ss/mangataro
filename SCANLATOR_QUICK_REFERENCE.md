# Scanlator Plugin Quick Reference

## Creating a New Scanlator Plugin

### Step 1: Copy the Template

```bash
cp scanlators/template.py scanlators/mysite.py
```

### Step 2: Basic Setup

```python
from playwright.async_api import Page
from scanlators.base import BaseScanlator

class MySiteScanlator(BaseScanlator):
    def __init__(self, playwright_page: Page):
        super().__init__(playwright_page)
        self.name = "MySite"
        self.base_url = "https://mysite.com"
```

### Step 3: Implement Search

```python
async def buscar_manga(self, titulo: str) -> list[dict]:
    search_url = f"{self.base_url}/search?q={titulo}"

    if not await self.safe_goto(search_url):
        return []

    # Wait for results
    await self.page.wait_for_selector(".manga-item")

    # Extract results
    items = await self.page.locator(".manga-item").all()
    resultados = []

    for item in items:
        titulo = await item.locator(".title").text_content()
        url = await item.locator("a").get_attribute("href")
        portada = await item.locator("img").get_attribute("src")

        resultados.append({
            "titulo": titulo.strip(),
            "url": url,
            "portada": portada
        })

    return resultados
```

### Step 4: Implement Chapter Extraction

```python
async def obtener_capitulos(self, manga_url: str) -> list[dict]:
    if not await self.safe_goto(manga_url):
        return []

    # Wait for chapter list
    await self.page.wait_for_selector(".chapter-item")

    # Extract chapters
    items = await self.page.locator(".chapter-item").all()
    capitulos = []

    for item in items:
        texto = await item.locator(".chapter-title").text_content()
        url = await item.locator("a").get_attribute("href")
        fecha_texto = await item.locator(".date").text_content()

        capitulos.append({
            "numero": self.parsear_numero_capitulo(texto),
            "titulo": texto.strip(),
            "url": url,
            "fecha": self._parse_date(fecha_texto)
        })

    # Sort from oldest to newest
    capitulos.sort(key=lambda x: (float(x["numero"]), x["fecha"]))
    return capitulos
```

### Step 5: Implement Chapter Number Parsing

```python
import re

def parsear_numero_capitulo(self, texto: str) -> str:
    # Remove common prefixes
    texto = re.sub(r"(chapter|ch\.?|cap\.?)\s*", "", texto, flags=re.IGNORECASE)

    # Extract number (including decimals)
    match = re.search(r"(\d+(?:\.\d+)?)", texto)
    return match.group(1) if match else texto.strip()
```

### Step 6: (Optional) Add Date Parsing Helper

```python
from datetime import datetime, timedelta

def _parse_date(self, fecha_texto: str) -> datetime:
    # Try standard format
    try:
        return datetime.strptime(fecha_texto, "%b %d, %Y")
    except ValueError:
        pass

    # Handle relative dates
    if "days ago" in fecha_texto.lower():
        match = re.search(r"(\d+)\s+days?\s+ago", fecha_texto, re.IGNORECASE)
        if match:
            days = int(match.group(1))
            return datetime.now() - timedelta(days=days)

    if "yesterday" in fecha_texto.lower():
        return datetime.now() - timedelta(days=1)

    # Default to now
    return datetime.now()
```

## Using Your Plugin

### Discovery

```python
from scanlators import get_scanlator_classes, list_scanlators

# List all available
plugins = list_scanlators()
print(plugins)  # ['MySiteScanlator', 'OtherSiteScanlator']

# Get specific plugin
classes = get_scanlator_classes()
MySiteClass = classes['MySiteScanlator']
```

### Usage with Playwright

```python
from playwright.async_api import async_playwright

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Instantiate plugin
        mysite = MySiteClass(page)

        # Search for manga
        results = await mysite.buscar_manga("One Piece")
        for result in results[:5]:
            print(f"{result['titulo']}: {result['url']}")

        # Get chapters
        if results:
            chapters = await mysite.obtener_capitulos(results[0]['url'])
            for ch in chapters[:10]:
                print(f"Chapter {ch['numero']}: {ch['titulo']}")

        await browser.close()
```

## Common Patterns

### CSS Selectors

```python
# Wait for element
await self.page.wait_for_selector(".class-name", timeout=10000)

# Get all matching elements
items = await self.page.locator(".item").all()

# Get text content
text = await element.locator(".title").text_content()

# Get attribute
href = await element.locator("a").get_attribute("href")

# Get inner HTML
html = await element.inner_html()
```

### Using JavaScript

```python
# Execute JavaScript on page
results = await self.page.evaluate("""
    () => {
        const items = document.querySelectorAll('.manga-item');
        return Array.from(items).map(item => ({
            titulo: item.querySelector('.title')?.textContent,
            url: item.querySelector('a')?.href
        }));
    }
""")
```

### Error Handling

```python
try:
    # Your scraping code
    await self.page.wait_for_selector(".item", timeout=10000)
except Exception as e:
    logger.error(f"[{self.name}] Error: {e}")
    return []
```

### Navigation

```python
# Use safe_goto helper (recommended)
if not await self.safe_goto(url):
    return []

# Or direct (not recommended)
await self.page.goto(url, wait_until="domcontentloaded")
```

## Testing Your Plugin

### Quick Test

```bash
python test_scanlator_discovery.py
```

### Manual Test

```python
from scanlators import get_scanlator_by_name
from playwright.async_api import async_playwright
import asyncio

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        MySiteClass = get_scanlator_by_name('MySiteScanlator')
        plugin = MySiteClass(page)

        # Test search
        results = await plugin.buscar_manga("test")
        print(f"Found {len(results)} results")

        # Test chapters
        if results:
            chapters = await plugin.obtener_capitulos(results[0]['url'])
            print(f"Found {len(chapters)} chapters")

        await browser.close()

asyncio.run(test())
```

## Troubleshooting

### Plugin Not Discovered

- Check file is in `scanlators/` directory
- File must end with `.py`
- Class must inherit from `BaseScanlator`
- File should not start with `_` or be in skip list

### Abstract Method Error

- Ensure all three methods are implemented:
  - `buscar_manga`
  - `obtener_capitulos`
  - `parsear_numero_capitulo`

### Timeout Errors

- Increase timeout: `await self.safe_goto(url, timeout=60000)`
- Use `domcontentloaded` wait strategy
- Check if selector is correct

### Element Not Found

- Wait for element before accessing
- Verify selector with browser DevTools
- Check if element is in iframe
- Use `page.locator().count()` to check existence

## Best Practices

1. **Always use `safe_goto`** for navigation
2. **Wait for selectors** before extracting data
3. **Handle errors gracefully** - return empty list on failure
4. **Log important events** with `logger`
5. **Use proper async/await** - don't block
6. **Test with real data** - verify selectors work
7. **Handle relative dates** in date parsing
8. **Normalize chapter numbers** consistently
9. **Sort chapters properly** - oldest to newest
10. **Return expected formats** - match the spec exactly

## Return Format Reference

### buscar_manga

```python
[
    {
        "titulo": "Manga Title",
        "url": "https://site.com/manga/title",
        "portada": "https://site.com/covers/title.jpg"
    }
]
```

### obtener_capitulos

```python
[
    {
        "numero": "42.5",
        "titulo": "Chapter 42.5: The Fight",
        "url": "https://site.com/manga/title/42.5",
        "fecha": datetime(2026, 1, 15, 12, 30)
    }
]
```

### parsear_numero_capitulo

```python
Input:  "Chapter 42.5"
Output: "42.5"
```

## Resources

- Template: `/data/mangataro/scanlators/template.py`
- Base Class: `/data/mangataro/scanlators/base.py`
- Example: `/data/mangataro/example_scanlator_usage.py`
- Test: `/data/mangataro/test_scanlator_discovery.py`
- Playwright Docs: https://playwright.dev/python/docs/api/class-page
