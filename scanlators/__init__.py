"""
Scanlator plugin auto-discovery system.

This module automatically discovers and registers all scanlator plugins
in the scanlators directory. Plugins are classes that inherit from BaseScanlator.

Usage:
    from scanlators import get_scanlator_classes

    # Get all available scanlator classes
    scanlators = get_scanlator_classes()

    # Access a specific scanlator
    ManhuaPlusClass = scanlators.get('ManhuaPlusScanlator')

    # Instantiate with a Playwright page
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        manhuaplus = ManhuaPlusClass(page)
        results = await manhuaplus.buscar_manga("One Piece")
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, Type
from loguru import logger

from scanlators.base import BaseScanlator


def get_scanlator_classes() -> Dict[str, Type[BaseScanlator]]:
    """
    Auto-discover and return all scanlator plugin classes.

    Scans the scanlators directory for Python files and imports them dynamically.
    Finds all classes that inherit from BaseScanlator (excluding BaseScanlator itself)
    and returns them in a dictionary.

    Returns:
        Dictionary mapping class names to scanlator class objects.
        Example: {'ManhuaPlusScanlator': <class 'ManhuaPlusScanlator'>, ...}

    Files to skip:
        - __init__.py (this file)
        - base.py (contains the abstract base class)
        - template.py (template for new scanlators)
        - Any file starting with _ or .
    """
    scanlators: Dict[str, Type[BaseScanlator]] = {}

    # Get the scanlators directory path
    scanlators_dir = Path(__file__).parent

    # Files to skip during discovery
    skip_files = {"__init__.py", "base.py", "template.py"}

    logger.debug(f"Scanning for scanlator plugins in: {scanlators_dir}")

    # Scan all Python files in the scanlators directory
    for file_path in scanlators_dir.glob("*.py"):
        # Skip files that should not be loaded
        if file_path.name in skip_files or file_path.name.startswith("_") or file_path.name.startswith("."):
            logger.debug(f"Skipping {file_path.name}")
            continue

        # Get module name from file name (remove .py extension)
        module_name = file_path.stem

        try:
            # Import the module dynamically
            full_module_name = f"scanlators.{module_name}"

            # Check if module is already imported
            if full_module_name in sys.modules:
                module = sys.modules[full_module_name]
            else:
                module = importlib.import_module(full_module_name)

            logger.debug(f"Imported module: {full_module_name}")

            # Find all classes in the module that inherit from BaseScanlator
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a subclass of BaseScanlator (but not BaseScanlator itself)
                if (
                    issubclass(obj, BaseScanlator)
                    and obj is not BaseScanlator
                    and obj.__module__ == full_module_name  # Only classes defined in this module
                ):
                    scanlators[name] = obj
                    logger.info(f"Registered scanlator plugin: {name} from {module_name}.py")

        except ImportError as e:
            logger.error(f"Failed to import {module_name}.py: {e}")
            continue
        except Exception as e:
            logger.error(f"Error processing {module_name}.py: {e}")
            continue

    logger.info(f"Auto-discovery complete. Found {len(scanlators)} scanlator plugin(s)")

    return scanlators


def list_scanlators() -> list[str]:
    """
    Get a list of all available scanlator plugin names.

    Returns:
        List of scanlator class names (e.g., ['ManhuaPlusScanlator', 'AsuraScansScanlator'])
    """
    return list(get_scanlator_classes().keys())


def get_scanlator_by_name(class_name: str) -> Type[BaseScanlator] | None:
    """
    Get a specific scanlator class by name.

    Args:
        class_name: The name of the scanlator class (e.g., 'ManhuaPlusScanlator')

    Returns:
        The scanlator class if found, None otherwise

    Example:
        ManhuaPlusClass = get_scanlator_by_name('ManhuaPlusScanlator')
        if ManhuaPlusClass:
            scanlator = ManhuaPlusClass(page)
    """
    scanlators = get_scanlator_classes()
    return scanlators.get(class_name)


# Export the main functions
__all__ = [
    "get_scanlator_classes",
    "list_scanlators",
    "get_scanlator_by_name",
    "BaseScanlator",
]
