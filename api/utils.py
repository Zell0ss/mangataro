import os
import re
import requests
from pathlib import Path
from loguru import logger
from datetime import datetime


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.

    Args:
        text: The text to slugify

    Returns:
        A lowercase slug with hyphens instead of spaces
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Remove non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def download_image(url: str, save_dir: str) -> str:
    """
    Download an image from a URL and save it to the specified directory.

    Args:
        url: The URL of the image to download
        save_dir: The directory where the image should be saved

    Returns:
        The filename of the saved image

    Raises:
        Exception: If the download fails
    """
    try:
        # Extract the filename from the URL
        filename = url.split('/')[-1]

        # Create full path
        save_path = Path(save_dir) / filename

        # Skip if file already exists
        if save_path.exists():
            logger.info(f"Image already exists: {filename}")
            return filename

        # Download the image
        logger.info(f"Downloading image from {url}")
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()

        # Save the image
        with open(save_path, 'wb') as f:
            f.write(response.content)

        logger.success(f"Image saved: {filename}")
        return filename

    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        raise


def create_markdown_ficha(
    title: str,
    alternative_titles: str,
    cover_filename: str,
    scanlator_group: str,
    mangataro_url: str,
    date_added: datetime,
    save_dir: str
) -> str:
    """
    Create a markdown ficha (info card) for a manga.

    Args:
        title: The main title of the manga
        alternative_titles: Alternative titles separated by " / "
        cover_filename: The filename of the cover image
        scanlator_group: The name of the scanlation group
        mangataro_url: The MangaTaro URL
        date_added: The date the manga was added
        save_dir: The directory where the ficha should be saved

    Returns:
        The filename of the saved ficha
    """
    try:
        # Create slug for filename
        slug = slugify(title)
        ficha_filename = f"{slug}.md"
        ficha_path = Path(save_dir) / ficha_filename

        # Format the date
        if isinstance(date_added, str):
            # Parse the date string from MangaTaro export format
            date_added = datetime.strptime(date_added, '%Y-%m-%d %H:%M:%S')
        date_str = date_added.strftime('%Y-%m-%d')

        # Create markdown content
        content = f"""# {title}
## {alternative_titles if alternative_titles else "N/A"}
![Portada](../../data/img/{cover_filename})

**Scanlation Group:** {scanlator_group if scanlator_group else "Unknown"}

**MangaTaro URL:** {mangataro_url}

**Date Added:** {date_str}
"""

        # Save the ficha
        with open(ficha_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.success(f"Markdown ficha created: {ficha_filename}")
        return ficha_filename

    except Exception as e:
        logger.error(f"Failed to create markdown ficha for {title}: {e}")
        raise


def create_scanlators_checklist(scanlators: list, save_path: str):
    """
    Create a markdown checklist of all scanlators found.

    Args:
        scanlators: List of scanlator names
        save_path: Path where the scanlators.md file should be saved
    """
    try:
        # Sort scanlators alphabetically
        scanlators_sorted = sorted(set(scanlators))

        # Create markdown content
        content = "# Scanlators Checklist\n\n"
        content += "Found scanlators from MangaTaro extraction:\n\n"

        for scanlator in scanlators_sorted:
            content += f"- [ ] {scanlator}\n"

        content += f"\n**Total scanlators:** {len(scanlators_sorted)}\n"
        content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        # Save the file
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.success(f"Scanlators checklist created: {save_path}")

    except Exception as e:
        logger.error(f"Failed to create scanlators checklist: {e}")
        raise
