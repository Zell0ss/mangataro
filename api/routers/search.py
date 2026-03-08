"""
Cross-scanlator search endpoint.

Queries all registered scanlator plugins in parallel and returns
combined results grouped by scanlator.
"""

import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright
from loguru import logger

from api.dependencies import get_db
from api import models
from scanlators import get_scanlator_classes

router = APIRouter()

SEARCH_TIMEOUT = 30.0  # seconds per scanlator
_browser_lock = asyncio.Semaphore(1)  # one search at a time to prevent OOM


async def _search_one(plugin_class, page, query: str, scanlator_name: str) -> dict:
    """
    Run buscar_manga for one scanlator and return a result dict.
    Never raises — errors are captured in the 'error' field.
    """
    try:
        plugin = plugin_class(page)
        matches = await asyncio.wait_for(
            plugin.buscar_manga(query),
            timeout=SEARCH_TIMEOUT
        )
        return {"scanlator": scanlator_name, "matches": matches or [], "error": None}
    except asyncio.TimeoutError:
        logger.warning(f"[search] Timeout searching {scanlator_name}")
        return {"scanlator": scanlator_name, "matches": [], "error": "Timeout"}
    except Exception as e:
        logger.error(f"[search] Error searching {scanlator_name}: {e}")
        return {"scanlator": scanlator_name, "matches": [], "error": str(e)}


@router.get("/")
async def search_manga(
    q: str = Query(..., min_length=2, max_length=100, description="Title keywords to search"),
    db: Session = Depends(get_db)
):
    """
    Search for manga across all registered scanlators simultaneously.

    Returns results grouped by scanlator. Every registered scanlator
    appears in the response — with empty matches if nothing found,
    or an error string if the plugin failed.
    """
    logger.info(f"[search] Searching for: {q!r}")

    # Get all active scanlators that have an implemented plugin
    scanlators = db.query(models.Scanlator).filter(
        models.Scanlator.active == True
    ).order_by(models.Scanlator.name).all()

    # Filter to only those with an available plugin class
    plugin_classes = get_scanlator_classes()
    searchable = []
    for s in scanlators:
        plugin_class = plugin_classes.get(s.class_name)
        if plugin_class:
            searchable.append((s, plugin_class))
        else:
            logger.debug(f"[search] Skipping {s.name} — no plugin class found")

    if not searchable:
        return {"query": q, "results": []}

    async with _browser_lock:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            pages = []
            try:
                # Create one page per scanlator (shared browser, lower resource use)
                for _ in searchable:
                    pages.append(await browser.new_page())

                tasks = [
                    _search_one(plugin_class, pages[i], q, s.name)
                    for i, (s, plugin_class) in enumerate(searchable)
                ]

                results = await asyncio.gather(*tasks)
            finally:
                for page in pages:
                    await page.close()
                await browser.close()

    logger.info(f"[search] Done. {sum(len(r['matches']) for r in results)} total matches across {len(results)} scanlators")
    return {"query": q, "results": list(results)}
