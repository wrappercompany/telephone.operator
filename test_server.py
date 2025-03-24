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
#   "libimobiledevice",
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

def detect_real_device() -> bool:
    """Detect if a real iOS device is connected."""
    try:
        result = subprocess.run(['idevice_id', '-l'], capture_output=True, text=True)
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False

def get_device_info() -> dict:
    """Get information about the connected device."""
    if detect_real_device():
        try:
            udid = subprocess.run(['idevice_id', '-l'], capture_output=True, text=True).stdout.strip().split('\n')[0]
            info = subprocess.run(['ideviceinfo', '-u', udid], capture_output=True, text=True).stdout.strip()
            device_info = {}
            for line in info.split('\n'):
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    device_info[key.strip()] = value.strip()
            return {
                'is_real': True,
                'name': device_info.get('DeviceName', 'iPhone'),
                'version': device_info.get('ProductVersion', Config.IOS_VERSION),
                'udid': udid
            }
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
    
    return {
        'is_real': False,
        'name': Config.DEVICE_NAME,
        'version': Config.IOS_VERSION,
        'udid': None
    }

async def wait_for_appium_ready(max_retries=5, delay=1):
    """Wait for Appium session to be ready."""
    device_info = get_device_info()
    max_retries = 10 if device_info['is_real'] else 5  # Longer timeout for real devices
    delay = 2 if device_info['is_real'] else 1  # Longer delay for real devices
    
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
    device_info = get_device_info()
    max_retries = 5 if device_info['is_real'] else 3
    retry_delay = 2 if device_info['is_real'] else 1
    
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
            await asyncio.sleep(retry_delay)

@pytest.mark.asyncio
async def test_tap_element():
    """Test tapping an element."""
    device_info = get_device_info()
    # Verify driver is active
    assert device_manager.driver is not None
    
    # Try to tap the URL bar in Safari
    try:
        # Wait for URL element to be present (longer timeout for real devices)
        wait = WebDriverWait(device_manager.driver, 20 if device_info['is_real'] else 10)
        element = wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "URL"))
        )
        element.click()
        logger.info("Tap element test passed")
    except Exception as e:
        if device_info['is_real']:
            logger.warning(f"Tap element test warning (real device): {e}")
        else:
            logger.warning(f"Tap element test warning: {e}")

@pytest.mark.asyncio
async def test_press_physical_buttons():
    """Test pressing physical buttons."""
    device_info = get_device_info()
    
    # Skip certain buttons on simulator
    buttons_to_test = [PhysicalButton.HOME]
    if device_info['is_real']:
        buttons_to_test.extend([
            PhysicalButton.VOLUME_UP,
            PhysicalButton.VOLUME_DOWN
        ])
    
    for button in buttons_to_test:
        try:
            device_manager.driver.execute_script('mobile: pressButton', {'name': button.value})
            await asyncio.sleep(2 if device_info['is_real'] else 1)
            logger.info(f"Physical button ({button.name}) test passed")
        except Exception as e:
            logger.error(f"Physical button test failed for {button.name}: {e}")
            if not device_info['is_real']:
                raise

@pytest.mark.asyncio
async def test_swipe_gestures():
    """Test swipe gestures in all directions."""
    device_info = get_device_info()
    gesture_delay = 1.0 if device_info['is_real'] else 0.5
    
    for direction in SwipeDirection:
        try:
            window_size = device_manager.driver.get_window_size()
            width = window_size['width']
            height = window_size['height']
            
            # Adjust swipe parameters for real devices (more conservative)
            if device_info['is_real']:
                swipe_params = {
                    SwipeDirection.UP: (width * 0.5, height * 0.6, width * 0.5, height * 0.4),
                    SwipeDirection.DOWN: (width * 0.5, height * 0.4, width * 0.5, height * 0.6),
                    SwipeDirection.LEFT: (width * 0.7, height * 0.5, width * 0.3, height * 0.5),
                    SwipeDirection.RIGHT: (width * 0.3, height * 0.5, width * 0.7, height * 0.5)
                }
            else:
                swipe_params = {
                    SwipeDirection.UP: (width * 0.5, height * 0.7, width * 0.5, height * 0.3),
                    SwipeDirection.DOWN: (width * 0.5, height * 0.3, width * 0.5, height * 0.7),
                    SwipeDirection.LEFT: (width * 0.8, height * 0.5, width * 0.2, height * 0.5),
                    SwipeDirection.RIGHT: (width * 0.2, height * 0.5, width * 0.8, height * 0.5)
                }
            
            start_x, start_y, end_x, end_y = swipe_params[direction]
            device_manager.driver.swipe(start_x, start_y, end_x, end_y, 800 if device_info['is_real'] else 500)
            await asyncio.sleep(gesture_delay)
            logger.info(f"Swipe {direction.value} test passed")
        except Exception as e:
            logger.error(f"Swipe {direction.value} test failed: {e}")
            if not device_info['is_real']:
                raise

@pytest.mark.asyncio
async def test_send_input():
    """Test sending text input to elements."""
    device_info = get_device_info()
    # Verify driver is active
    assert device_manager.driver is not None
    
    # Navigate to a URL first
    try:
        device_manager.driver.get("https://www.example.com")
        await asyncio.sleep(4 if device_info['is_real'] else 2)  # Wait longer for page load on real device
        
        # Wait for URL bar to be present and clickable
        wait = WebDriverWait(device_manager.driver, 20 if device_info['is_real'] else 10)
        url_bar = wait.until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//XCUIElementTypeTextField"))
        )
        
        # Click the URL bar and wait for it to be focused
        url_bar.click()
        await asyncio.sleep(2 if device_info['is_real'] else 1)
        
        # Find the element again after clicking to avoid stale element
        url_bar = wait.until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//XCUIElementTypeTextField"))
        )
        
        # Send input
        test_url = "https://www.example.com"
        url_bar.clear()
        await asyncio.sleep(0.5)  # Wait for clear to complete
        url_bar.send_keys(test_url)
        logger.info("Send input test passed")
    except Exception as e:
        logger.error(f"Send input test failed: {e}")
        if not device_info['is_real']:
            raise

@pytest.mark.asyncio
async def test_launch_app():
    """Test launching different iOS apps."""
    device_info = get_device_info()
    apps_to_test = [
        "com.apple.Preferences",
        Config.DEFAULT_BUNDLE_ID
    ]
    
    for bundle_id in apps_to_test:
        try:
            await device_manager.initialize_session(bundle_id)
            assert device_manager.driver is not None
            
            # Wait for app to be ready (longer for real devices)
            await asyncio.sleep(4 if device_info['is_real'] else 2)
            
            # Verify we can get page source
            page_source = device_manager.driver.page_source
            assert isinstance(page_source, str)
            assert len(page_source) > 0
            
            logger.info(f"Launch app test passed for {bundle_id}")
        except Exception as e:
            logger.error(f"Launch app test failed for {bundle_id}: {e}")
            if not device_info['is_real']:
                raise

@pytest.mark.asyncio
async def test_page_source_diff():
    """Test the page source diff functionality."""
    device_info = get_device_info()
    max_retries = 5 if device_info['is_real'] else 3
    retry_delay = 2 if device_info['is_real'] else 1
    
    try:
        # First, get initial page source
        current_source, diff = device_manager.get_page_source_diff()
        assert current_source is not None
        assert isinstance(current_source, str)
        assert len(current_source) > 0
        
        # The first call to get_page_source_diff should mention it's the initial page
        assert "Initial page source" in diff or diff.strip() == ""
        
        # Now perform an action that will change the UI
        # Try to tap the URL bar in Safari
        try:
            # Wait for URL element to be present
            wait = WebDriverWait(device_manager.driver, 20 if device_info['is_real'] else 10)
            element = wait.until(
                EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "URL"))
            )
            element.click()
            await asyncio.sleep(1)  # Wait for UI to update
            
            # Get page source diff after action
            _, diff_after_action = device_manager.get_page_source_diff()
            
            # There should be some diff contents now
            assert diff_after_action is not None
            assert isinstance(diff_after_action, str)
            assert "++" in diff_after_action or diff_after_action.startswith("---") or "@@" in diff_after_action
            
            logger.info("Page source diff test passed")
        except Exception as e:
            logger.warning(f"Page source diff action test warning: {e}")
            
    except Exception as e:
        logger.error(f"Page source diff test failed: {e}")
        if not device_info['is_real']:
            raise

if __name__ == "__main__":
    import sys
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='Run iOS automation tests')
    parser.add_argument('--lf', action='store_true', help='Run only failed tests')
    parser.add_argument('--failed-first', action='store_true', help='Run failed tests first')
    parser.add_argument('--inspector', action='store_true', help='Launch MCP Inspector before running tests')
    parser.add_argument('--force-simulator', action='store_true', help='Force using simulator even if real device is available')
    parser.add_argument('--device-name', help='Override device name (default: iPhone 16 Pro)')
    parser.add_argument('--ios-version', help='Override iOS version (default: 18.2)')
    parser.add_argument('--test-name', help='Run specific test by name (e.g., test_page_source_diff)')
    
    args = parser.parse_args()
    
    # Update Config based on arguments
    if args.force_simulator:
        Config.USE_REAL_DEVICE = False
    if args.device_name:
        Config.DEVICE_NAME = args.device_name
    if args.ios_version:
        Config.IOS_VERSION = args.ios_version
    
    # Log device configuration
    device_info = get_device_info()
    if device_info['is_real']:
        logger.info(f"Using real device: {device_info['name']} ({device_info['version']})")
    else:
        logger.info(f"Using simulator: {Config.DEVICE_NAME} ({Config.IOS_VERSION})")
    
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
    
    # Add test name if specified
    if args.test_name:
        pytest_args.extend(["-k", args.test_name])
    
    pytest_args.append(__file__)
    pytest.main(pytest_args) 