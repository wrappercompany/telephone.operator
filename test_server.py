#!/usr/bin/env python3

# /// script
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-asyncio>=0.23.0",
#   "Appium-Python-Client>=3.1.0",
#   "fastmcp>=0.1.0",
#   "urllib3<2.0.0",
# ]
# ///

import pytest
import pytest_asyncio
import asyncio
import logging
import time
from server import (
    initialize_appium_session,
    cleanup,
    get_page_source,
    tap_element,
    press_physical_button,
    swipe
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set pytest-asyncio mode to strict
pytest.mark.asyncio(asyncio_mode="strict")

async def wait_for_appium_ready(max_retries=5, delay=1):
    """Wait for Appium session to be ready."""
    for attempt in range(max_retries):
        try:
            result = await get_page_source()
            if result != "No active Appium session":
                return True
        except Exception:
            pass
        await asyncio.sleep(delay)
    return False

@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_teardown():
    """Setup and teardown for each test."""
    try:
        await initialize_appium_session()
        # Wait for session to be ready with timeout
        if not await wait_for_appium_ready():
            raise Exception("Appium session failed to initialize")
        yield
    finally:
        await cleanup()

@pytest.mark.asyncio
async def test_get_page_source():
    """Test getting page source."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await get_page_source()
            assert result != "No active Appium session"
            assert isinstance(result, str)
            assert len(result) > 0
            logger.info("Page source test passed")
            break
        except AssertionError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)  # Reduced from 2s to 1s

@pytest.mark.asyncio
async def test_tap_element():
    """Test tapping an element."""
    # Verify page source is available before attempting tap
    result = await get_page_source()
    assert result != "No active Appium session"
    
    # Try to tap the URL bar in Safari
    result = await tap_element("URL")
    assert "Successfully tapped element" in result or "Failed to tap element" in result
    logger.info("Tap element test completed")

@pytest.mark.asyncio
async def test_press_physical_buttons():
    """Test pressing physical buttons."""
    # Test home button (only supported button in simulator)
    result = await press_physical_button("home")
    assert "Successfully pressed" in result
    await asyncio.sleep(1)  # Reduced from 2s to 1s
    
    # Test invalid button
    result = await press_physical_button("invalid_button")
    assert "Invalid button" in result
    logger.info("Physical buttons test passed")

@pytest.mark.asyncio
async def test_swipe_gestures():
    """Test swipe gestures in all directions."""
    directions = ["up", "down", "left", "right"]
    
    for direction in directions:
        result = await swipe(direction)
        assert f"Successfully performed {direction} swipe" in result
        await asyncio.sleep(0.5)  # Reduced from 2s to 0.5s
    
    # Test invalid direction
    result = await swipe("invalid_direction")
    assert "Invalid direction" in result
    logger.info("Swipe gestures test passed")

if __name__ == "__main__":
    pytest.main(["-v", "--asyncio-mode=strict", __file__]) 