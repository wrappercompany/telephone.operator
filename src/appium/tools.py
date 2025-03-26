#!/usr/bin/env python3

from agents import function_tool
from appium.webdriver.common.appiumby import AppiumBy
from enum import Enum
from datetime import datetime
from pathlib import Path
import logging
import traceback
import difflib
from typing import Optional, Dict, Any, Tuple, Callable, TypeVar, Awaitable
from functools import wraps
from .driver import ios_driver
from .enums import AppiumStatus, AppAction
from ..ui.console import console, Panel, print_error, print_warning, print_success

logger = logging.getLogger(__name__)

class LocatorStrategy(str, Enum):
    ACCESSIBILITY_ID = "accessibility_id"
    XPATH = "xpath"
    NAME = "name"
    CLASS_NAME = "class_name"

class PhysicalButton(str, Enum):
    HOME = "home"
    VOLUME_UP = "volumeUp"
    VOLUME_DOWN = "volumeDown"
    POWER = "power"

class SwipeDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

def check_driver_connection() -> Tuple[bool, str]:
    """Check if driver is connected and return status."""
    if not ios_driver.driver:
        error_msg = "No active Appium session"
        logger.error(error_msg)
        print_error(error_msg)
        return False, error_msg
    return True, "Driver connected"

def get_clean_page_source() -> Optional[str]:
    """
    Get the current page source without any cleaning.
    Returns raw XML directly from the driver.
    """
    logger.debug("Getting page source (cleaning disabled)")
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        logger.error(f"Cannot get page source: {message}")
        return None
    
    try:
        # Get raw page source
        page_source = ios_driver.driver.page_source
        if not page_source:
            logger.warning("Page source is empty")
            return None
            
        # Simply return the raw page source
        logger.debug("Returning raw page source (cleaning disabled)")
        return page_source
    except Exception as e:
        logger.error(f"Error getting page source: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None

# Type variable for generic function signatures
T = TypeVar('T')

@function_tool
async def get_page_source() -> str:
    """
    Get the current page source of the application.
    """

    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Get raw page source
        page_source = get_clean_page_source()
        if not page_source:
            error_msg = "Page source is empty or could not be retrieved"
            logger.warning(error_msg)
            return error_msg
        
        # Display the full page source
        console.print(Panel(page_source, title="Full Page Source", border_style="blue", expand=False))
        
        logger.info("Returning full page source")
        return page_source
        
    except Exception as e:
        error_msg = f"Failed to get page source: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def tap_element(element_id: str, *, by: Optional[LocatorStrategy] = None) -> str:
    """
    Tap an element by its identifier.
    Only taps elements that are visible on screen.
    
    Args:
        element_id: The identifier of the element to tap
        by: The locator strategy to use
    """
    logger.info(f"Tool called: tap_element with id={element_id}, by={by}")
    
    if not element_id:
        error_msg = "Element ID cannot be empty"
        logger.error(error_msg)
        print_error(error_msg)
        return error_msg
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        locator_map = {
            LocatorStrategy.ACCESSIBILITY_ID: AppiumBy.ACCESSIBILITY_ID,
            LocatorStrategy.XPATH: AppiumBy.XPATH,
            LocatorStrategy.NAME: AppiumBy.NAME,
            LocatorStrategy.CLASS_NAME: AppiumBy.CLASS_NAME
        }
        
        by_strategy = locator_map[by] if by else AppiumBy.ACCESSIBILITY_ID
        logger.debug(f"Using locator strategy: {by_strategy} with value: {element_id}")
        
        try:
            element = ios_driver.driver.find_element(by=by_strategy, value=element_id)
        except Exception as e:
            error_msg = f"Element not found: {str(e)}"
            logger.warning(error_msg)
            print_warning(error_msg)
            return error_msg
        
        # Check if element is visible
        if not element.is_displayed():
            warning_msg = f"Element with {by_strategy}: {element_id} is not visible"
            logger.warning(warning_msg)
            print_warning(warning_msg)
            return warning_msg
            
        element.click()
        
        success_msg = f"Successfully tapped visible element with {by_strategy}: {element_id}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to tap element: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def press_physical_button(button: PhysicalButton) -> str:
    """
    Press a physical button on the iOS device.
    
    Args:
        button: The button to press
    """
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Execute the button press
        ios_driver.driver.execute_script('mobile: pressButton', {'name': button.value})
        
        success_msg = f"Successfully pressed {button.name} button"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to press button: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def swipe(direction: SwipeDirection = None, start_x: Optional[int] = None, start_y: Optional[int] = None, end_x: Optional[int] = None, end_y: Optional[int] = None) -> str:
    """
    Perform a swipe gesture in the specified direction or between coordinates.
    
    Args:
        direction: The direction to swipe (can be omitted if using coordinates)
        start_x: Starting X coordinate in pixels (actual screen coordinates, not normalized)
        start_y: Starting Y coordinate in pixels (actual screen coordinates, not normalized)
        end_x: Ending X coordinate in pixels (actual screen coordinates, not normalized)
        end_y: Ending Y coordinate in pixels (actual screen coordinates, not normalized)
    """
    logger.info(f"Tool called: swipe with direction={direction}, coordinates=({start_x}, {start_y}) to ({end_x}, {end_y})")
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        window_size = ios_driver.driver.get_window_size()
        width = window_size['width']
        height = window_size['height']
        
        # Check if we're using direction-based or coordinate-based swiping
        using_coordinates = all(coord is not None for coord in [start_x, start_y, end_x, end_y])
        using_direction = direction is not None
        
        if not using_coordinates and not using_direction:
            error_msg = "Either direction or all coordinates (start_x, start_y, end_x, end_y) must be provided"
            logger.error(error_msg)
            print_error(error_msg)
            return error_msg
        
        if using_coordinates:
            # Validate coordinates are within screen bounds
            if (start_x < 0 or start_x > width or start_y < 0 or start_y > height or 
                end_x < 0 or end_x > width or end_y < 0 or end_y > height):
                warning_msg = (f"Some coordinates are outside screen bounds ({width}x{height}). "
                              f"Coordinates: ({start_x}, {start_y}) to ({end_x}, {end_y})")
                logger.warning(warning_msg)
                print_warning(warning_msg)
                # Continue anyway as the user might know what they're doing
            
            logger.info(f"Swiping with raw coordinates: ({start_x}, {start_y}) to ({end_x}, {end_y})")
            ios_driver.driver.swipe(start_x, start_y, end_x, end_y, 500)
            
            success_msg = f"Successfully performed coordinate swipe from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            logger.info(success_msg)
            print_success(success_msg)
            return success_msg
        else:
            # Use direction-based swiping
            swipe_params = {
                SwipeDirection.UP: (width * 0.5, height * 0.7, width * 0.5, height * 0.3),
                SwipeDirection.DOWN: (width * 0.5, height * 0.3, width * 0.5, height * 0.7),
                SwipeDirection.LEFT: (width * 0.8, height * 0.5, width * 0.2, height * 0.5),
                SwipeDirection.RIGHT: (width * 0.2, height * 0.5, width * 0.8, height * 0.5)
            }
            
            start_x, start_y, end_x, end_y = swipe_params[direction]
            ios_driver.driver.swipe(start_x, start_y, end_x, end_y, 500)
            
            success_msg = f"Successfully performed {direction.value} swipe"
            logger.info(success_msg)
            print_success(success_msg)
            return success_msg
    except Exception as e:
        error_msg = f"Failed to perform swipe: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def send_input(element_id: str, text: str, *, by: Optional[LocatorStrategy] = None) -> str:
    """
    Send text input to an element by its identifier.
    
    Args:
        element_id: The identifier of the element
        text: The text to send
        by: The locator strategy to use
    """
    logger.info(f"Tool called: send_input with id={element_id}, text={text}, by={by}")
    
    if not element_id:
        error_msg = "Element ID cannot be empty"
        logger.error(error_msg)
        print_error(error_msg)
        return error_msg
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        locator_map = {
            LocatorStrategy.ACCESSIBILITY_ID: AppiumBy.ACCESSIBILITY_ID,
            LocatorStrategy.XPATH: AppiumBy.XPATH,
            LocatorStrategy.NAME: AppiumBy.NAME,
            LocatorStrategy.CLASS_NAME: AppiumBy.CLASS_NAME
        }
        
        by_strategy = locator_map[by] if by else AppiumBy.ACCESSIBILITY_ID
        
        try:
            element = ios_driver.driver.find_element(by=by_strategy, value=element_id)
        except Exception as e:
            error_msg = f"Element not found: {str(e)}"
            logger.warning(error_msg)
            print_warning(error_msg)
            return error_msg
            
        element.clear()
        element.send_keys(text)
        
        success_msg = f"Successfully sent input '{text}' to element with {by_strategy}: {element_id}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to send input: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def navigate_to(url: str) -> str:
    """
    Navigate to a URL in Safari.
    
    Args:
        url: The URL to navigate to
    """
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Navigate to URL
        ios_driver.driver.get(url)
        
        success_msg = f"Successfully navigated to {url}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to navigate: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def launch_app(bundle_id: str) -> str:
    """
    Launch an iOS app by its bundle ID.
    
    Args:
        bundle_id: The bundle ID of the app to launch
    """
    logger.info(f"Tool called: launch_app with bundle_id={bundle_id}")
    
    if not bundle_id:
        error_msg = "Bundle ID cannot be empty"
        logger.error(error_msg)
        print_error(error_msg)
        return error_msg
    
    try:
        # Check if driver exists and try to relaunch app
        if ios_driver.driver:
            logger.info(f"Driver exists, attempting to terminate and reactivate app: {bundle_id}")
            try:
                ios_driver.driver.terminate_app(bundle_id)
                ios_driver.driver.activate_app(bundle_id)
                
                success_msg = f"Successfully relaunched app with bundle ID: {bundle_id}"
                logger.info(success_msg)
                print_success(success_msg)
                return success_msg
            except Exception as e:
                logger.warning(f"Failed to relaunch app via existing driver: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                logger.info("Will try to re-initialize driver")
                ios_driver.cleanup()
        
        # Initialize driver
        logger.info(f"Initializing driver for app: {bundle_id}")
        result = ios_driver.init_driver(bundle_id)
        
        if result:
            success_msg = f"Successfully launched app with bundle ID: {bundle_id}"
            logger.info(success_msg)
            print_success(success_msg)
            return success_msg
        else:
            error_msg = f"Failed to initialize driver for app: {bundle_id}"
            logger.error(error_msg)
            print_error(error_msg)
            return error_msg
    except Exception as e:
        error_msg = f"Failed to launch app: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def take_screenshot() -> str:
    """Take a screenshot and save page source of the current app state."""
    logger.info("Tool called: take_screenshot")
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Get current app bundle ID or use "unknown_app" as fallback
        app_dir_name = "unknown_app"
        try:
            # For iOS, we get the bundle ID from capabilities
            bundle_id = ios_driver.driver.capabilities.get('bundleId')
            if bundle_id:
                # Clean up bundle ID to make it filesystem friendly
                app_dir_name = bundle_id.split('.')[-1].lower()
        except Exception as e:
            logger.warning(f"Could not get bundle ID: {str(e)}")
            # Continue with the default app_dir_name
        
        # Create base output directory structure
        output_dir = Path("artifacts")
        app_dir = output_dir / app_dir_name
        screenshots_dir = app_dir / "screenshots"
        pagesource_dir = app_dir / "pagesource"
        
        # Create directories if they don't exist
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        pagesource_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for both files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshots_dir / f"screenshot_{timestamp}.png"
        pagesource_path = pagesource_dir / f"pagesource_{timestamp}.xml"
        
        # Take screenshot
        logger.debug(f"Saving screenshot to: {screenshot_path}")
        ios_driver.driver.get_screenshot_as_file(str(screenshot_path))
        
        # Get and save page source
        logger.debug(f"Saving page source to: {pagesource_path}")
        # Get raw page source (cleaning is disabled)
        page_source = get_clean_page_source()
        if not page_source:
            # Fall back to raw page source if getting it fails
            page_source = ios_driver.driver.page_source
        
        # Add XML declaration at the top if not present
        if not page_source.startswith('<?xml'):
            page_source = '<?xml version="1.0" encoding="UTF-8"?>\n' + page_source
            
        pagesource_path.write_text(page_source, encoding='utf-8')
        
        success_msg = f"Artifacts saved successfully:\nApp: {bundle_id if 'bundleId' in ios_driver.driver.capabilities else app_dir_name}\nScreenshot: {screenshot_path}\nPage Source: {pagesource_path}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to capture artifacts: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg 