"""
Base abstract class for scanlator plugins.

All scanlator plugins must inherit from BaseScanlator and implement
the required abstract methods for searching manga and extracting chapters.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger


class BaseScanlator(ABC):
    """
    Abstract base class for all scanlator plugins.

    Each scanlator plugin should inherit from this class and implement
    the abstract methods to provide site-specific scraping logic.

    Attributes:
        name: Human-readable name of the scanlator
        base_url: Base URL of the scanlator website
        page: Playwright Page instance for browser automation
    """

    def __init__(self, playwright_page: Page):
        """
        Initialize the scanlator plugin with a Playwright page.

        Args:
            playwright_page: An active Playwright Page instance for browser automation
        """
        self.page: Page = playwright_page
        self.name: str = ""
        self.base_url: str = ""

    @abstractmethod
    async def buscar_manga(self, titulo: str) -> list[dict]:
        """
        Search for manga by title and return a list of candidates.

        This method should navigate to the scanlator's search page,
        perform a search, and extract information about matching manga.

        Args:
            titulo: The manga title to search for

        Returns:
            A list of dictionaries with the following structure:
            [
                {
                    "titulo": "Manga Title",
                    "url": "https://scanlator.com/manga/title",
                    "portada": "https://scanlator.com/covers/title.jpg"
                },
                ...
            ]

        Raises:
            Exception: If search fails or page cannot be accessed
        """
        pass

    @abstractmethod
    async def obtener_capitulos(self, manga_url: str) -> list[dict]:
        """
        Extract all chapters from a manga's page.

        This method should navigate to the manga's page and extract
        information about all available chapters.

        Args:
            manga_url: Full URL to the manga's page on the scanlator site

        Returns:
            A list of dictionaries with the following structure:
            [
                {
                    "numero": "42",
                    "titulo": "Chapter Title",
                    "url": "https://scanlator.com/manga/title/chapter/42",
                    "fecha": datetime(2026, 1, 15, 12, 30)
                },
                ...
            ]
            Chapters should be sorted from oldest to newest.

        Raises:
            Exception: If page cannot be accessed or chapters cannot be extracted
        """
        pass

    @abstractmethod
    def parsear_numero_capitulo(self, texto: str) -> str:
        """
        Parse and normalize chapter numbers from various text formats.

        This method should extract and normalize chapter numbers from
        strings that may contain prefixes like "Chapter", "Ch.", "Cap.", etc.

        Args:
            texto: Raw text containing the chapter number (e.g., "Chapter 42.5", "Cap. 123")

        Returns:
            Normalized chapter number as a string (e.g., "42.5", "123")
            Should handle decimal chapters (e.g., "42.5", "123.1")

        Examples:
            "Chapter 42" -> "42"
            "Cap. 42.5" -> "42.5"
            "Ch. 123" -> "123"
            "Episode 5" -> "5"
        """
        pass

    async def safe_goto(self, url: str, timeout: int = 30000) -> bool:
        """
        Navigate to a URL with error handling and timeout.

        This helper method wraps Playwright's goto with proper error handling
        and logging. Use this instead of page.goto() directly.

        Args:
            url: The URL to navigate to
            timeout: Maximum time to wait for navigation in milliseconds (default: 30000)

        Returns:
            True if navigation succeeded, False otherwise

        Examples:
            if await self.safe_goto(manga_url):
                # Extract data from page
                pass
            else:
                logger.error(f"Failed to load {manga_url}")
                return []
        """
        try:
            logger.debug(f"[{self.name}] Navigating to: {url}")
            response = await self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            if response is None:
                logger.error(f"[{self.name}] No response received for {url}")
                return False

            if response.status >= 400:
                logger.error(f"[{self.name}] HTTP {response.status} error for {url}")
                return False

            logger.debug(f"[{self.name}] Successfully loaded {url}")
            return True

        except PlaywrightTimeoutError:
            logger.error(f"[{self.name}] Timeout loading {url} (timeout: {timeout}ms)")
            return False

        except Exception as e:
            logger.error(f"[{self.name}] Error navigating to {url}: {e}")
            return False

    def __repr__(self) -> str:
        """String representation of the scanlator plugin."""
        return f"<{self.__class__.__name__}(name='{self.name}', base_url='{self.base_url}')>"
