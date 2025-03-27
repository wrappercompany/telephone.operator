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
from .action_trace import action_tracer
from ..ui.console import console, Panel, print_error, print_warning, print_success
import time
import hashlib
import json

logger = logging.getLogger(__name__)

def require_appium_connection(func):
    """
    Decorator to ensure appium is properly set up and connected before executing agent tools.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        driver_status, message = check_driver_connection()
        if not driver_status:
            error_msg = f"Cannot execute {func.__name__}: {message}"
            logger.error(error_msg)
            print_error(error_msg)
            return error_msg
        return await func(*args, **kwargs)
    return wrapper

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
        
        # Update app state with current activity/view information if available
        try:
            # For iOS, try to get current activity/view
            current_view = ios_driver.driver.execute_script('mobile: activeAppInfo')
            if current_view:
                action_tracer.update_app_state(
                    current_activity=current_view.get('process'),
                    current_screen=current_view.get('bundleId'),
                    current_view=current_view.get('name', 'Unknown')
                )
        except Exception as e:
            logger.debug(f"Could not get current app view: {str(e)}")
        
        # Get the page source before the action
        try:
            page_source = get_clean_page_source()
            if page_source:
                # Store a hash of the page source to detect changes
                page_source_hash = hashlib.md5(page_source.encode()).hexdigest()
                action_tracer.update_app_state(last_page_source_hash=page_source_hash)
                
                # Save the page source to a temp file for reference
                page_source_dir = Path("artifacts") / "temp"
                page_source_dir.mkdir(parents=True, exist_ok=True)
                temp_page_source_path = page_source_dir / f"pre_tap_{int(time.time())}.xml"
                temp_page_source_path.write_text(page_source, encoding='utf-8')
            else:
                logger.debug("Could not get page source before tap action")
        except Exception as e:
            logger.debug(f"Error capturing page source: {str(e)}")
        
        try:
            element = ios_driver.driver.find_element(by=by_strategy, value=element_id)
        except Exception as e:
            error_msg = f"Element not found: {str(e)}"
            logger.warning(error_msg)
            print_warning(error_msg)
            
            # Log the failed action
            action_tracer.log_action("tap_element", {
                "element_id": element_id,
                "by": str(by) if by else "accessibility_id",
                "status": "failed",
                "reason": "element_not_found",
                "error": str(e),
                "selector_used": f"{by_strategy}={element_id}"
            })
            
            return error_msg
        
        # Check if element is visible
        if not element.is_displayed():
            warning_msg = f"Element with {by_strategy}: {element_id} is not visible"
            logger.warning(warning_msg)
            print_warning(warning_msg)
            
            # Log the failed action
            action_tracer.log_action("tap_element", {
                "element_id": element_id,
                "by": str(by) if by else "accessibility_id",
                "status": "failed",
                "reason": "element_not_visible",
                "selector_used": f"{by_strategy}={element_id}"
            })
            
            return warning_msg
        
        # Get comprehensive element attributes for better tracing
        element_attributes = {}
        try:
            element_attributes = {
                "text": element.text,
                "tag_name": element.tag_name,
                "location": element.location,
                "size": element.size,
                "enabled": element.is_enabled(),
                "selected": element.is_selected(),
                "rect": element.rect
            }
            
            # Get all available attributes
            for attr in ["name", "type", "label", "value"]:
                try:
                    attr_value = element.get_attribute(attr)
                    if attr_value is not None:
                        element_attributes[attr] = attr_value
                except:
                    pass
                    
            # Try to get the XPath of the element
            try:
                # Create an absolute XPath using attributes
                xpath = None
                if element.tag_name and element.get_attribute("label"):
                    xpath = f"//{element.tag_name}[@label='{element.get_attribute('label')}']"
                elif element.tag_name and element.get_attribute("name"):
                    xpath = f"//{element.tag_name}[@name='{element.get_attribute('name')}']"
                elif element.tag_name and element.text:
                    xpath = f"//{element.tag_name}[contains(text(),'{element.text}')]"
                    
                if xpath:
                    element_attributes["generated_xpath"] = xpath
            except Exception as e:
                logger.debug(f"Could not generate XPath: {str(e)}")
                
        except Exception as e:
            logger.debug(f"Error getting element attributes: {str(e)}")
            
        # Perform the tap action
        element.click()
        
        # Log the successful action with enhanced information
        action_tracer.log_action("tap_element", {
            "element_id": element_id,
            "by": str(by) if by else "accessibility_id",
            "status": "success",
            "element_details": element_attributes,
            "selector_used": f"{by_strategy}={element_id}"
        })
        
        success_msg = f"Successfully tapped visible element with {by_strategy}: {element_id}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to tap element: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        
        # Log the failed action
        action_tracer.log_action("tap_element", {
            "element_id": element_id,
            "by": str(by) if by else "accessibility_id",
            "status": "failed",
            "reason": "error",
            "error": str(e),
            "selector_used": f"{by_strategy}={element_id}"
        })
        
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
        # Log failed action
        action_tracer.log_action("swipe", {
            "status": "failed",
            "reason": "driver_not_connected",
            "message": message
        })
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
            
            # Log failed action
            action_tracer.log_action("swipe", {
                "status": "failed",
                "reason": "invalid_parameters",
                "message": error_msg
            })
            
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
            
            # Log successful action
            action_tracer.log_action("swipe", {
                "status": "success",
                "method": "coordinates",
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "screen_width": width,
                "screen_height": height
            })
            
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
            
            # Log successful action
            action_tracer.log_action("swipe", {
                "status": "success",
                "method": "direction",
                "direction": direction.value,
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "screen_width": width,
                "screen_height": height
            })
            
            success_msg = f"Successfully performed {direction.value} swipe"
            logger.info(success_msg)
            print_success(success_msg)
            return success_msg
    except Exception as e:
        error_msg = f"Failed to perform swipe: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        
        # Log failed action
        action_tracer.log_action("swipe", {
            "status": "failed",
            "reason": "error",
            "error": str(e),
            "direction": str(direction) if direction else None,
            "start_coords": f"({start_x}, {start_y})" if start_x is not None and start_y is not None else None,
            "end_coords": f"({end_x}, {end_y})" if end_x is not None and end_y is not None else None
        })
        
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
        
        # Log failed action
        action_tracer.log_action("send_input", {
            "status": "failed",
            "reason": "missing_element_id",
            "message": error_msg
        })
        
        return error_msg
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        # Log failed action
        action_tracer.log_action("send_input", {
            "status": "failed",
            "reason": "driver_not_connected",
            "message": message
        })
        
        return message
    
    try:
        locator_map = {
            LocatorStrategy.ACCESSIBILITY_ID: AppiumBy.ACCESSIBILITY_ID,
            LocatorStrategy.XPATH: AppiumBy.XPATH,
            LocatorStrategy.NAME: AppiumBy.NAME,
            LocatorStrategy.CLASS_NAME: AppiumBy.CLASS_NAME
        }
        
        by_strategy = locator_map[by] if by else AppiumBy.ACCESSIBILITY_ID
        
        # Update app state with current activity/view information
        try:
            current_view = ios_driver.driver.execute_script('mobile: activeAppInfo')
            if current_view:
                action_tracer.update_app_state(
                    current_activity=current_view.get('process'),
                    current_screen=current_view.get('bundleId'),
                    current_view=current_view.get('name', 'Unknown')
                )
        except Exception as e:
            logger.debug(f"Could not get current app view: {str(e)}")
            
        try:
            element = ios_driver.driver.find_element(by=by_strategy, value=element_id)
        except Exception as e:
            error_msg = f"Element not found: {str(e)}"
            logger.warning(error_msg)
            print_warning(error_msg)
            
            # Log failed action
            action_tracer.log_action("send_input", {
                "element_id": element_id,
                "text": text,
                "by": str(by) if by else "accessibility_id",
                "status": "failed",
                "reason": "element_not_found",
                "error": str(e),
                "selector_used": f"{by_strategy}={element_id}"
            })
            
            return error_msg
        
        # Get comprehensive element attributes BEFORE input
        pre_input_attributes = {}
        try:
            pre_input_attributes = {
                "text": element.text,
                "tag_name": element.tag_name,
                "location": element.location,
                "size": element.size,
                "enabled": element.is_enabled(),
                "selected": element.is_selected(),
                "rect": element.rect
            }
            
            # Get all available attributes
            for attr in ["name", "type", "label", "value"]:
                try:
                    attr_value = element.get_attribute(attr)
                    if attr_value is not None:
                        pre_input_attributes[attr] = attr_value
                except:
                    pass
                
            # Try to generate an XPath
            try:
                xpath = None
                if element.tag_name and element.get_attribute("label"):
                    xpath = f"//{element.tag_name}[@label='{element.get_attribute('label')}']"
                elif element.tag_name and element.get_attribute("name"):
                    xpath = f"//{element.tag_name}[@name='{element.get_attribute('name')}']"
                
                if xpath:
                    pre_input_attributes["generated_xpath"] = xpath
            except Exception as e:
                logger.debug(f"Could not generate XPath: {str(e)}")
                
        except Exception as e:
            logger.debug(f"Error getting pre-input element attributes: {str(e)}")
        
        # Save page source before input
        pre_input_page_source = None
        try:
            pre_input_page_source = get_clean_page_source()
            if pre_input_page_source:
                # Save the page source to a temp file for reference
                page_source_dir = Path("artifacts") / "temp"
                page_source_dir.mkdir(parents=True, exist_ok=True)
                temp_page_source_path = page_source_dir / f"pre_input_{int(time.time())}.xml"
                temp_page_source_path.write_text(pre_input_page_source, encoding='utf-8')
        except Exception as e:
            logger.debug(f"Error capturing pre-input page source: {str(e)}")
            
        # Perform the input operation
        element.clear()
        element.send_keys(text)
        
        # Get element attributes AFTER input
        post_input_attributes = {}
        try:
            post_input_attributes = {
                "text": element.text,
                "tag_name": element.tag_name,
                "value": element.get_attribute("value")
            }
            
            # Get other attributes that might have changed
            for attr in ["name", "label", "value"]:
                try:
                    attr_value = element.get_attribute(attr)
                    if attr_value is not None:
                        post_input_attributes[attr] = attr_value
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"Error getting post-input element attributes: {str(e)}")
            
        # Save page source after input if it changed
        post_input_page_source = None
        try:
            post_input_page_source = get_clean_page_source()
            if post_input_page_source and pre_input_page_source != post_input_page_source:
                # Save the page source to a temp file for reference
                page_source_dir = Path("artifacts") / "temp"
                page_source_dir.mkdir(parents=True, exist_ok=True)
                temp_page_source_path = page_source_dir / f"post_input_{int(time.time())}.xml"
                temp_page_source_path.write_text(post_input_page_source, encoding='utf-8')
        except Exception as e:
            logger.debug(f"Error capturing post-input page source: {str(e)}")
        
        # Log successful action with enhanced information
        action_tracer.log_action("send_input", {
            "element_id": element_id,
            "text": text,
            "by": str(by) if by else "accessibility_id",
            "status": "success",
            "selector_used": f"{by_strategy}={element_id}",
            "field_state": {
                "before": pre_input_attributes,
                "after": post_input_attributes,
                "page_source_changed": pre_input_page_source != post_input_page_source if pre_input_page_source and post_input_page_source else None
            }
        })
        
        success_msg = f"Successfully sent input '{text}' to element with {by_strategy}: {element_id}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to send input: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        
        # Log failed action
        action_tracer.log_action("send_input", {
            "element_id": element_id,
            "text": text,
            "by": str(by) if by else "accessibility_id",
            "status": "failed",
            "reason": "error",
            "error": str(e),
            "selector_used": f"{by_strategy}={element_id}"
        })
        
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
        # Log failed action
        action_tracer.log_action("navigate_to", {
            "status": "failed",
            "reason": "driver_not_connected",
            "message": message,
            "url": url
        })
        return message
    
    try:
        # Navigate to URL
        ios_driver.driver.get(url)
        
        # Log successful action
        action_tracer.log_action("navigate_to", {
            "status": "success",
            "url": url
        })
        
        success_msg = f"Successfully navigated to {url}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to navigate: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        
        # Log failed action
        action_tracer.log_action("navigate_to", {
            "status": "failed",
            "reason": "error",
            "error": str(e),
            "url": url
        })
        
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
                
                # Start action tracing for app
                app_dir_name = bundle_id.split('.')[-1].lower()
                action_tracer.start_new_trace(app_dir_name, bundle_id)
                action_tracer.log_action("app_launch", {"bundle_id": bundle_id, "status": "reactivated"})
                
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
            # Start action tracing for app
            app_dir_name = bundle_id.split('.')[-1].lower()
            action_tracer.start_new_trace(app_dir_name, bundle_id)
            action_tracer.log_action("app_launch", {"bundle_id": bundle_id, "status": "initialized"})
            
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
        # Log failed action
        action_tracer.log_action("take_screenshot", {
            "status": "failed",
            "reason": "driver_not_connected", 
            "message": message
        })
        return message
    
    try:
        # Get current app bundle ID or use "unknown_app" as fallback
        app_dir_name = "unknown_app"
        bundle_id = None
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
        
        # Log the successful action with file paths
        action_tracer.log_action("take_screenshot", {
            "status": "success",
            "app": app_dir_name,
            "bundle_id": bundle_id,
            "screenshot_path": str(screenshot_path),
            "pagesource_path": str(pagesource_path),
            "timestamp": timestamp
        })
        
        success_msg = f"Artifacts saved successfully:\nApp: {bundle_id if 'bundleId' in ios_driver.driver.capabilities else app_dir_name}\nScreenshot: {screenshot_path}\nPage Source: {pagesource_path}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to capture artifacts: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        
        # Log the failed action
        action_tracer.log_action("take_screenshot", {
            "status": "failed",
            "reason": "error",
            "error": str(e)
        })
        
        return error_msg 

@function_tool
async def end_action_trace() -> str:
    """
    Manually end the current action trace if active.
    This saves the trace file and finalizes it.
    """
    logger.info("Tool called: end_action_trace")
    
    try:
        action_tracer.end_trace()
        success_msg = "Action trace ended successfully"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to end action trace: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg 

def track_network_request(url: str, method: str, status: Optional[int] = None, 
                       request_data: Optional[Dict[str, Any]] = None,
                       response_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Track a network request in the action trace.
    
    Args:
        url: URL of the request
        method: HTTP method (GET, POST, etc.)
        status: HTTP status code if available
        request_data: Request data/body if available
        response_data: Response data if available
    """
    try:
        action_tracer.log_network_request(
            url=url,
            method=method,
            status=status,
            request_data=request_data,
            response_data=response_data
        )
    except Exception as e:
        logger.debug(f"Failed to track network request: {str(e)}")

@function_tool
async def capture_network_request(url: str, method: str, status: Optional[int] = None, 
                                request_body: Optional[str] = None,
                                response_body: Optional[str] = None) -> str:
    """
    Manually capture a network request in the action trace.
    
    Args:
        url: URL of the request
        method: HTTP method (GET, POST, etc.)
        status: HTTP status code (optional)
        request_body: Request body as string (optional)
        response_body: Response body as string (optional)
    """
    logger.info(f"Tool called: capture_network_request for {method} {url}")
    
    try:
        # Convert bodies to dictionaries if they are JSON
        request_data = None
        response_data = None
        
        if request_body:
            try:
                request_data = json.loads(request_body)
            except:
                request_data = {"raw": request_body}
                
        if response_body:
            try:
                response_data = json.loads(response_body)
            except:
                response_data = {"raw": response_body}
        
        # Track the network request
        action_tracer.log_network_request(
            url=url,
            method=method,
            status=status,
            request_data=request_data,
            response_data=response_data
        )
        
        success_msg = f"Successfully captured network request: {method} {url}"
        logger.info(success_msg)
        print_success(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to capture network request: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg 