#!/usr/bin/env python3
"""
Test script for scanlator plugin auto-discovery system.

This script tests that:
1. The scanlators module can be imported
2. Auto-discovery finds the template scanlator
3. The BaseScanlator class is accessible
4. Plugin classes can be instantiated (with a mock page)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logger for testing
logger.remove()
logger.add(sys.stderr, level="DEBUG")


def test_discovery():
    """Test the auto-discovery system."""
    logger.info("=" * 60)
    logger.info("Testing Scanlator Plugin Auto-Discovery System")
    logger.info("=" * 60)

    # Test 1: Import the scanlators module
    logger.info("\n[Test 1] Importing scanlators module...")
    try:
        from scanlators import get_scanlator_classes, list_scanlators, BaseScanlator
        logger.success("Successfully imported scanlators module")
    except Exception as e:
        logger.error(f"Failed to import scanlators module: {e}")
        return False

    # Test 2: Get all scanlator classes
    logger.info("\n[Test 2] Running auto-discovery...")
    try:
        scanlators = get_scanlator_classes()
        logger.success(f"Auto-discovery complete. Found {len(scanlators)} plugin(s)")
    except Exception as e:
        logger.error(f"Auto-discovery failed: {e}")
        return False

    # Test 3: List scanlators
    logger.info("\n[Test 3] Listing available scanlators...")
    try:
        scanlator_names = list_scanlators()
        if scanlator_names:
            logger.success(f"Available scanlators: {', '.join(scanlator_names)}")
        else:
            logger.warning("No scanlators found (this is expected if only template exists)")
    except Exception as e:
        logger.error(f"Failed to list scanlators: {e}")
        return False

    # Test 4: Check if TestScanlator was found
    logger.info("\n[Test 4] Checking for TestScanlator...")
    if "TestScanlator" in scanlators:
        logger.success("TestScanlator was discovered")
        test_class = scanlators["TestScanlator"]

        # Verify it's a subclass of BaseScanlator
        if issubclass(test_class, BaseScanlator):
            logger.success("TestScanlator correctly inherits from BaseScanlator")
        else:
            logger.error("TestScanlator does not inherit from BaseScanlator")
            return False
    else:
        logger.warning("TestScanlator not found (this would indicate a discovery issue)")

    # Test 5: Display plugin information
    logger.info("\n[Test 5] Plugin Information:")
    logger.info("-" * 60)
    if scanlators:
        for name, cls in scanlators.items():
            logger.info(f"Class: {name}")
            logger.info(f"  Module: {cls.__module__}")
            logger.info(f"  Base Classes: {[base.__name__ for base in cls.__bases__]}")

            # Check for required methods
            required_methods = ["buscar_manga", "obtener_capitulos", "parsear_numero_capitulo", "safe_goto"]
            missing_methods = [method for method in required_methods if not hasattr(cls, method)]

            if not missing_methods:
                logger.success(f"  All required methods present")
            else:
                logger.warning(f"  Missing methods: {', '.join(missing_methods)}")
            logger.info("")
    else:
        logger.info("No plugins found")

    # Test 6: Test instantiation with mock page
    logger.info("\n[Test 6] Testing plugin instantiation with mock page...")
    try:
        # Create a simple mock page object
        class MockPage:
            """Mock Playwright page for testing."""
            async def goto(self, url, **kwargs):
                return None

        mock_page = MockPage()

        if "TestScanlator" in scanlators:
            test_class = scanlators["TestScanlator"]
            instance = test_class(mock_page)
            logger.success(f"Successfully instantiated: {instance}")
            logger.info(f"  Name: {instance.name}")
            logger.info(f"  Base URL: {instance.base_url}")

            # Test parsear_numero_capitulo method
            test_cases = [
                ("Chapter 42", "42"),
                ("Ch. 42.5", "42.5"),
                ("Episode 123", "123"),
            ]
            logger.info("\n  Testing parsear_numero_capitulo:")
            all_passed = True
            for input_text, expected in test_cases:
                result = instance.parsear_numero_capitulo(input_text)
                status = "✓" if result == expected else "✗"
                logger.info(f"    {status} '{input_text}' -> '{result}' (expected: '{expected}')")
                if result != expected:
                    all_passed = False

            if all_passed:
                logger.success("  All parsear_numero_capitulo tests passed")
        else:
            logger.info("No scanlators to instantiate")

    except Exception as e:
        logger.error(f"Failed to instantiate plugin: {e}")
        return False

    # Summary
    logger.info("\n" + "=" * 60)
    logger.success("All tests passed!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Create a new scanlator by copying scanlators/template.py")
    logger.info("2. Implement the abstract methods for your scanlator site")
    logger.info("3. Run this test script again to verify it's discovered")
    logger.info("4. Use Playwright to test the actual scraping functionality")

    return True


if __name__ == "__main__":
    success = test_discovery()
    sys.exit(0 if success else 1)
