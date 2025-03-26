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
async def get_page_source(query: str) -> str:
    """
    Get the current page source of the application with focused retrieval based on a query.
    If a query is provided, returns the most relevant elements matching the query.
    Otherwise, returns the full page source.
    
    Args:
        query: Search query to focus on specific elements or functionality. Use empty string for full page source.
    """
    logger.info(f"Tool called: get_page_source with query='{query}'")
    
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
        
        # If no query, return the full page source
        if not query:
            logger.info("Empty query provided, returning full page source")
            console.print(Panel(page_source, title="Full Page Source", border_style="blue", expand=False))
            return page_source
        
        # Otherwise, process the query and retrieve relevant parts
        try:
            from lxml import etree
            import re
            
            logger.info(f"Analyzing page source for query: '{query}'")
            
            # Parse the XML
            root = etree.fromstring(page_source.encode('utf-8'))
            
            # Prepare search terms from the query
            search_terms = query.lower().split()
            
            # Function to score element relevance
            def score_element(element):
                element_text = ' '.join([
                    element.get('name', ''),
                    element.get('label', ''),
                    element.get('value', ''),
                    element.get('hint', ''),
                    element.get('text', ''),
                    element.text or ''
                ]).lower()
                
                # Score based on attribute matches
                score = 0
                for term in search_terms:
                    if term in element_text:
                        score += 10  # Higher weight for exact matches
                    elif any(term in attr for attr in element_text.split()):
                        score += 5   # Lower weight for partial matches
                
                # Boost score for interactive elements when looking for functionality
                if ('button' in query.lower() or 'tap' in query.lower() or 'click' in query.lower()) and \
                   ('button' in element.tag.lower() or element.get('type') == 'XCUIElementTypeButton'):
                    score += 15
                
                # Boost score for input fields when looking for text entry
                if ('input' in query.lower() or 'text' in query.lower() or 'enter' in query.lower()) and \
                   ('field' in element.tag.lower() or 'text' in element.tag.lower() or 
                    element.get('type') in ['XCUIElementTypeTextField', 'XCUIElementTypeSecureTextField']):
                    score += 15
                
                # Boost score for navigation elements
                if ('menu' in query.lower() or 'navigation' in query.lower() or 'tab' in query.lower()) and \
                   ('tab' in element.tag.lower() or 'bar' in element.tag.lower() or 
                    element.get('type') in ['XCUIElementTypeTabBar', 'XCUIElementTypeNavigationBar']):
                    score += 15
                
                return score
            
            # Find all elements in the tree
            all_elements = root.xpath('//*')
            
            # Score each element
            scored_elements = [(element, score_element(element)) for element in all_elements]
            
            # Sort by score, descending
            scored_elements.sort(key=lambda x: x[1], reverse=True)
            
            # Take top N relevant elements
            top_n = 15
            relevant_elements = scored_elements[:top_n]
            
            # Filter out elements with zero score
            relevant_elements = [item for item in relevant_elements if item[1] > 0]
            
            # If no relevant elements found
            if not relevant_elements:
                logger.info(f"No elements found matching query: '{query}'")
                result = f"No elements found matching query: '{query}'\n\nFull page source is available if needed."
                console.print(Panel(result, title=f"Query Results: {query}", border_style="yellow", expand=False))
                return result
            
            # Format the relevant elements for display
            result = f"Query: '{query}'\n\nRelevant Elements:\n"
            for i, (element, score) in enumerate(relevant_elements, 1):
                # Get element attributes for display
                attrs = {
                    'name': element.get('name', ''),
                    'label': element.get('label', ''),
                    'value': element.get('value', ''),
                    'type': element.get('type', ''),
                    'enabled': element.get('enabled', ''),
                    'visible': element.get('visible', ''),
                    'accessible': element.get('accessible', ''),
                    'x': element.get('x', ''),
                    'y': element.get('y', ''),
                    'width': element.get('width', ''),
                    'height': element.get('height', '')
                }
                
                # Filter out empty attributes
                attrs = {k: v for k, v in attrs.items() if v}
                
                # Create formatted string of attributes
                attrs_str = ', '.join([f"{k}='{v}'" for k, v in attrs.items()])
                
                # Add to result
                result += f"{i}. Element (relevance score: {score}):\n"
                result += f"   Type: {element.tag}\n"
                result += f"   Attributes: {attrs_str}\n\n"
            
            result += "Use these elements with tap_element by specifying their 'name' or other attributes."
            
            # Display formatted results
            console.print(Panel(result, title=f"Query Results: {query}", border_style="green", expand=False))
            
            logger.info(f"Found {len(relevant_elements)} elements matching query: '{query}'")
            return result
            
        except ImportError:
            # If lxml not available, return full page source with a note
            logger.warning("lxml not available for element querying, returning full page source")
            return f"Note: Enhanced querying unavailable (lxml missing).\nQuery: '{query}'\n\n{page_source}"
        except Exception as e:
            # If parsing fails, still return the full page source
            logger.error(f"Error parsing page source for query: {str(e)}")
            return f"Error analyzing elements for query '{query}': {str(e)}\n\nReturning full page source:\n\n{page_source}"
        
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
async def swipe(direction: SwipeDirection) -> str:
    """
    Perform a swipe gesture in the specified direction.
    
    Args:
        direction: The direction to swipe
    """
    logger.info(f"Tool called: swipe with direction={direction}")
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        window_size = ios_driver.driver.get_window_size()
        width = window_size['width']
        height = window_size['height']
        
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
        output_dir = Path("test_artifacts")
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