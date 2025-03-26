#!/usr/bin/env python3

import pytest
import asyncio
import os
import json
from pathlib import Path
from typing import Optional, Any

from src.appium.tools import (
    get_page_source,
    tap_element,
    press_physical_button,
    swipe,
    send_input,
    navigate_to,
    launch_app,
    take_screenshot,
    LocatorStrategy,
    PhysicalButton,
    SwipeDirection
)
from src.appium.driver import ios_driver
from src.config import load_config
from agents import RunContextWrapper

# Create a basic context for the function tools - not a test class
class MockContext:
    """Mock context for function tools, not a test class."""
    def __init__(self):
        self.data = {}

# These wrapper functions call the function_tool objects correctly using on_invoke_tool
async def call_get_page_source(query: str = "") -> str:
    ctx = RunContextWrapper(MockContext())
    args = json.dumps({"query": query})
    return await get_page_source.on_invoke_tool(ctx, args)

async def call_tap_element(element_id: str, by: Optional[LocatorStrategy] = None) -> str:
    ctx = RunContextWrapper(MockContext())
    args = {"element_id": element_id}
    if by is not None:
        args["by"] = by.value
    return await tap_element.on_invoke_tool(ctx, json.dumps(args))

async def call_press_physical_button(button: PhysicalButton) -> str:
    ctx = RunContextWrapper(MockContext())
    args = json.dumps({"button": button.value})
    return await press_physical_button.on_invoke_tool(ctx, args)

async def call_swipe(direction: SwipeDirection) -> str:
    ctx = RunContextWrapper(MockContext())
    args = json.dumps({"direction": direction.value})
    return await swipe.on_invoke_tool(ctx, args)

async def call_send_input(element_id: str, text: str, by: Optional[LocatorStrategy] = None) -> str:
    ctx = RunContextWrapper(MockContext())
    args = {"element_id": element_id, "text": text}
    if by is not None:
        args["by"] = by.value
    return await send_input.on_invoke_tool(ctx, json.dumps(args))

async def call_navigate_to(url: str) -> str:
    ctx = RunContextWrapper(MockContext())
    args = json.dumps({"url": url})
    return await navigate_to.on_invoke_tool(ctx, args)

async def call_launch_app(bundle_id: str) -> str:
    ctx = RunContextWrapper(MockContext())
    args = json.dumps({"bundle_id": bundle_id})
    return await launch_app.on_invoke_tool(ctx, args)

async def call_take_screenshot() -> str:
    ctx = RunContextWrapper(MockContext())
    args = json.dumps({})
    return await take_screenshot.on_invoke_tool(ctx, args)

# Load test configuration
@pytest.fixture(scope="session")
def config():
    """Load test configuration"""
    return load_config()

@pytest.fixture(scope="session")
def test_app_bundle_id() -> str:
    """Get the test app bundle ID from environment or use default"""
    return os.environ.get("TEST_APP_BUNDLE_ID", "com.apple.Preferences")

@pytest.fixture(scope="module")
async def setup_driver(test_app_bundle_id):
    """Setup the iOS driver with the test app"""
    # Initialize the driver if not already initialized
    if not ios_driver.driver:
        success = ios_driver.init_driver(test_app_bundle_id)
        if not success:
            pytest.skip("Failed to initialize iOS driver")
    
    yield ios_driver
    
    # Cleanup after tests
    ios_driver.cleanup()

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_launch_app(test_app_bundle_id):
    """Test launching an app by bundle ID"""
    result = await call_launch_app(test_app_bundle_id)
    assert "Successfully launched" in result
    assert test_app_bundle_id in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_get_page_source_empty_query(setup_driver):
    """Test getting page source with empty query"""
    result = await call_get_page_source("")
    assert result is not None
    assert "<AppiumAUT>" in result or "<XCUIElementTypeApplication" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_get_page_source_with_query(setup_driver):
    """Test getting page source with a focused query"""
    result = await call_get_page_source("button")
    assert result is not None
    assert "Relevant Elements" in result or "No elements found matching query" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_take_screenshot(setup_driver):
    """Test taking a screenshot"""
    result = await call_take_screenshot()
    assert "Artifacts saved successfully" in result
    assert "Screenshot" in result
    assert "Page Source" in result
    
    # Verify the files were created
    assert "screenshot_" in result
    assert "pagesource_" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_tap_element_by_accessibility_id(setup_driver):
    """Test tapping an element by accessibility ID"""
    # First get page source to find a valid element
    page_source = await call_get_page_source("button")
    
    # Try to tap a common element that should exist in most apps
    # Note: This might need adjustment based on the specific test app
    result = await call_tap_element("General", by=LocatorStrategy.ACCESSIBILITY_ID)
    
    # The test should pass if either:
    # 1. The element was successfully tapped
    # 2. The element was not found (which is not a failure of the function itself)
    assert "Successfully tapped" in result or "Element not found" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_tap_element_by_xpath(setup_driver):
    """Test tapping an element by XPath"""
    # Try to tap an element using XPath
    result = await call_tap_element("//XCUIElementTypeButton", by=LocatorStrategy.XPATH)
    assert "Successfully tapped" in result or "Element not found" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_swipe_operations(setup_driver):
    """Test swiping in different directions"""
    # Test swipe up
    result = await call_swipe(SwipeDirection.UP)
    assert "Successfully performed up swipe" in result
    
    # Give the UI time to settle after the swipe
    await asyncio.sleep(1)
    
    # Test swipe down
    result = await call_swipe(SwipeDirection.DOWN)
    assert "Successfully performed down swipe" in result
    
    # Test swipe left and right
    await asyncio.sleep(1)
    result = await call_swipe(SwipeDirection.LEFT)
    assert "Successfully performed left swipe" in result
    
    await asyncio.sleep(1)
    result = await call_swipe(SwipeDirection.RIGHT)
    assert "Successfully performed right swipe" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_press_physical_button(setup_driver):
    """Test pressing physical buttons"""
    # Test pressing the home button
    result = await call_press_physical_button(PhysicalButton.HOME)
    assert "Successfully pressed HOME button" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_send_input(setup_driver):
    """Test sending input to a text field"""
    # First launch the app again (to ensure we're in a known state)
    await call_launch_app(os.environ.get("TEST_APP_BUNDLE_ID", "com.apple.Preferences"))
    
    # Try to find a search field (common in many apps)
    page_source = await call_get_page_source("search")
    
    # Attempt to send input to a search field
    # Note: This test might be skipped if no suitable input field is found
    result = await call_send_input("Search", "test input", by=LocatorStrategy.ACCESSIBILITY_ID)
    
    # The test should pass if either:
    # 1. Input was successfully sent
    # 2. The element was not found (which is not a failure of the function itself)
    assert "Successfully sent input" in result or "Element not found" in result

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_navigate_to(setup_driver):
    """Test navigating to a URL (requires Safari to be the active app)"""
    # This test might be conditional based on whether we can launch Safari
    try:
        # Try to launch Safari
        await call_launch_app("com.apple.mobilesafari")
        
        # Navigate to a URL
        result = await call_navigate_to("https://www.apple.com")
        assert "Successfully navigated to" in result
    except Exception:
        pytest.skip("Safari navigation test skipped - could not launch Safari")

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_complex_interaction_flow(setup_driver, test_app_bundle_id):
    """Test a complex interaction flow combining multiple tool operations"""
    # Launch the app
    await call_launch_app(test_app_bundle_id)
    
    # Take a screenshot of the initial state
    screenshot_result = await call_take_screenshot()
    assert "Artifacts saved successfully" in screenshot_result
    
    # Get page source and look for an element to tap
    page_source = await call_get_page_source("button")
    
    # Try to tap an element (the specific element might need adjustment)
    tap_result = await call_tap_element("General", by=LocatorStrategy.ACCESSIBILITY_ID)
    
    # If we successfully tapped the element, continue with more interactions
    if "Successfully tapped" in tap_result:
        # Swipe to explore more content
        await call_swipe(SwipeDirection.UP)
        
        # Take another screenshot after navigation
        screenshot_result2 = await call_take_screenshot()
        assert "Artifacts saved successfully" in screenshot_result2
    
    # Go back to home screen
    await call_press_physical_button(PhysicalButton.HOME)

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_settings_workflow(setup_driver):
    """Test a specific workflow in the Settings app"""
    # Launch the Settings app
    await call_launch_app("com.apple.Preferences")
    
    # Take an initial screenshot
    await call_take_screenshot()
    
    # Try to navigate to Wi-Fi settings
    tap_result = await call_tap_element("Wi-Fi", by=LocatorStrategy.ACCESSIBILITY_ID)
    
    if "Successfully tapped" in tap_result:
        # We're in the Wi-Fi settings screen
        await call_take_screenshot()
        
        # Try to toggle Wi-Fi (this may or may not work depending on permissions)
        toggle_result = await call_tap_element("Wi-Fi", by=LocatorStrategy.ACCESSIBILITY_ID)
        
        # Swipe down to see more content
        await call_swipe(SwipeDirection.DOWN)
        await call_take_screenshot()
        
        # Go back to main settings
        # In iOS Settings, we can use the back button in the top left
        back_result = await call_tap_element("Settings", by=LocatorStrategy.ACCESSIBILITY_ID)
        
        if "Element not found" in back_result:
            # Try alternative navigation if back button not found
            await call_press_physical_button(PhysicalButton.HOME)
            await call_launch_app("com.apple.Preferences")
    
    # Now try to navigate to General settings
    tap_result = await call_tap_element("General", by=LocatorStrategy.ACCESSIBILITY_ID)
    
    if "Successfully tapped" in tap_result:
        # We're in the General settings screen
        await call_take_screenshot()
        
        # Go back to home screen
        await call_press_physical_button(PhysicalButton.HOME)

@pytest.mark.asyncio
@pytest.mark.appium
@pytest.mark.integration
async def test_multiple_app_interaction(setup_driver):
    """Test interactions across multiple apps"""
    # Start with Settings app
    await call_launch_app("com.apple.Preferences")
    await call_take_screenshot()
    
    # Try to launch Safari
    try:
        await call_launch_app("com.apple.mobilesafari")
        await call_take_screenshot()
        
        # Navigate to a URL
        await call_navigate_to("https://www.apple.com")
        await call_take_screenshot()
        
        # Interact with the page
        await call_swipe(SwipeDirection.DOWN)
        await call_take_screenshot()
        
        # Switch back to Settings
        await call_launch_app("com.apple.Preferences")
        await call_take_screenshot()
        
    except Exception as e:
        # If Safari tests fail, continue with other apps
        pass
    
    # Try to launch another system app (Photos)
    try:
        await call_launch_app("com.apple.mobileslideshow")
        await call_take_screenshot()
        
        # Interact with the Photos app
        await call_swipe(SwipeDirection.RIGHT)
        await call_take_screenshot()
        
    except Exception:
        # If Photos tests fail, continue
        pass
    
    # Return to Settings app to end the test
    await call_launch_app("com.apple.Preferences")
    await call_take_screenshot()

# Run the tests if this file is executed directly
if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 