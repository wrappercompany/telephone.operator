#!/usr/bin/env python3

# /// script
# dependencies = [
#   "pytest>=7.0.0",
#   "pytest-asyncio>=0.23.0",
#   "Appium-Python-Client>=3.1.0",
#   "fastmcp>=0.1.0",
#   "urllib3<2.0.0",
#   "pydantic>=2.0.0",
#   "@modelcontextprotocol/inspector",
# ]
# ///

import pytest
import pytest_asyncio
import asyncio
import logging
import subprocess
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from server import (
    device_manager,
    LocatorStrategy,
    PhysicalButton,
    SwipeDirection,
    Config,
    AppiumBy
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
            if device_manager.driver:
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
        await device_manager.initialize_session()
        # Wait for session to be ready with timeout
        if not await wait_for_appium_ready():
            raise Exception("Appium session failed to initialize")
        yield
    finally:
        await device_manager.cleanup()

@pytest.mark.asyncio
async def test_get_page_source():
    """Test getting page source."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # page_source is a synchronous property
            result = device_manager.driver.page_source
            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0
            logger.info("Page source test passed")
            break
        except AssertionError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)

@pytest.mark.asyncio
async def test_tap_element():
    """Test tapping an element."""
    # Verify driver is active
    assert device_manager.driver is not None
    
    # Try to tap the URL bar in Safari
    try:
        # Wait for URL element to be present
        wait = WebDriverWait(device_manager.driver, 10)
        element = wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "URL"))
        )
        element.click()
        logger.info("Tap element test passed")
    except Exception as e:
        logger.warning(f"Tap element test warning: {e}")

@pytest.mark.asyncio
async def test_press_physical_buttons():
    """Test pressing physical buttons."""
    # Test home button
    try:
        device_manager.driver.execute_script('mobile: pressButton', {'name': PhysicalButton.HOME.value})
        await asyncio.sleep(1)
        logger.info("Physical button (HOME) test passed")
    except Exception as e:
        logger.error(f"Physical button test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_swipe_gestures():
    """Test swipe gestures in all directions."""
    for direction in SwipeDirection:
        try:
            window_size = device_manager.driver.get_window_size()
            width = window_size['width']
            height = window_size['height']
            
            swipe_params = {
                SwipeDirection.UP: (width * 0.5, height * 0.7, width * 0.5, height * 0.3),
                SwipeDirection.DOWN: (width * 0.5, height * 0.3, width * 0.5, height * 0.7),
                SwipeDirection.LEFT: (width * 0.8, height * 0.5, width * 0.2, height * 0.5),
                SwipeDirection.RIGHT: (width * 0.2, height * 0.5, width * 0.8, height * 0.5)
            }
            
            start_x, start_y, end_x, end_y = swipe_params[direction]
            device_manager.driver.swipe(start_x, start_y, end_x, end_y, 500)
            await asyncio.sleep(0.5)
            logger.info(f"Swipe {direction.value} test passed")
        except Exception as e:
            logger.error(f"Swipe {direction.value} test failed: {e}")
            raise

@pytest.mark.asyncio
async def test_send_input():
    """Test sending text input to elements."""
    # Verify driver is active
    assert device_manager.driver is not None
    
    # Navigate to a URL first
    try:
        device_manager.driver.get("https://www.example.com")
        await asyncio.sleep(2)  # Wait longer for page load
        
        # Wait for URL bar to be present and clickable
        wait = WebDriverWait(device_manager.driver, 10)
        url_bar = wait.until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//XCUIElementTypeTextField"))
        )
        
        # Click the URL bar and wait for it to be focused
        url_bar.click()
        await asyncio.sleep(1)
        
        # Find the element again after clicking to avoid stale element
        url_bar = wait.until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//XCUIElementTypeTextField"))
        )
        
        # Send input
        test_url = "https://www.example.com"
        url_bar.clear()
        url_bar.send_keys(test_url)
        logger.info("Send input test passed")
    except Exception as e:
        logger.error(f"Send input test failed: {e}")
        raise

@pytest.mark.asyncio
async def test_launch_app():
    """Test launching different iOS apps."""
    apps_to_test = [
        "com.apple.Preferences",
        Config.DEFAULT_BUNDLE_ID
    ]
    
    for bundle_id in apps_to_test:
        try:
            await device_manager.initialize_session(bundle_id)
            assert device_manager.driver is not None
            
            # Wait for app to be ready
            await asyncio.sleep(2)
            
            # Verify we can get page source
            page_source = device_manager.driver.page_source
            assert isinstance(page_source, str)
            assert len(page_source) > 0
            
            logger.info(f"Launch app test passed for {bundle_id}")
        except Exception as e:
            logger.error(f"Launch app test failed for {bundle_id}: {e}")
            raise

if __name__ == "__main__":
    import sys
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='Run iOS automation tests')
    parser.add_argument('--lf', action='store_true', help='Run only failed tests')
    parser.add_argument('--failed-first', action='store_true', help='Run failed tests first')
    parser.add_argument('--inspector', action='store_true', help='Launch MCP Inspector before running tests')
    
    args = parser.parse_args()
    
    # Default pytest arguments
    pytest_args = ["-v", "--asyncio-mode=strict"]
    
    # Launch inspector if flag is set
    if args.inspector:
        try:
            subprocess.run([
                "npx",
                "@modelcontextprotocol/inspector",
                "uv",
                "--directory", ".",
                "run"
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to launch inspector: {e}")
            sys.exit(1)
    
    # Add appropriate flags
    if args.lf:
        pytest_args.extend(["--lf"])
    elif args.failed_first:
        pytest_args.extend(["--failed-first"])
    
    pytest_args.append(__file__)
    pytest.main(pytest_args) 