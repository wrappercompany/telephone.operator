#!/usr/bin/env python3

from agents import function_tool
from appium.webdriver.common.appiumby import AppiumBy
from enum import Enum
from datetime import datetime
from pathlib import Path
import logging
import traceback
import difflib
from typing import Optional, Dict, Any, Tuple
from .driver import ios_driver
from .enums import AppiumStatus, AppAction
from ..ui.console import console, Panel, print_error, print_warning, print_success

logger = logging.getLogger(__name__)

# Store the previous page source for diffing
previous_page_source = None

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

def xml_diff(old_xml: str, new_xml: str) -> str:
    """Generate a diff between two XML strings with color formatting."""
    if not old_xml:
        return new_xml
    
    old_lines = old_xml.splitlines()
    new_lines = new_xml.splitlines()
    
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile='before',
        tofile='after',
        lineterm=''
    ))
    
    # Add Rich color formatting
    formatted_lines = []
    for line in diff_lines:
        if line.startswith('+'):
            if not (line.startswith('+++') and line.startswith('+++ after')):
                # Green for additions
                formatted_lines.append(f"[bold green]{line}[/bold green]")
            else:
                formatted_lines.append(line)
        elif line.startswith('-'):
            if not (line.startswith('---') and line.startswith('--- before')):
                # Red for removals
                formatted_lines.append(f"[bold red]{line}[/bold red]")
            else:
                formatted_lines.append(line)
        elif line.startswith('@@'):
            # Cyan for line info
            formatted_lines.append(f"[cyan]{line}[/cyan]")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

@function_tool
async def get_page_source(*, diff_only: Optional[bool] = None, format_output: Optional[bool] = None, clean_output: Optional[bool] = None) -> str:
    """
    Get the current page source of the application.
    
    Args:
        diff_only: If True, returns only the diff from the previous page source
        format_output: If True, formats the XML for better readability
        clean_output: If None or True, returns a cleaned version of the XML containing only visible elements. Set to False for raw XML.
    """
    global previous_page_source
    
    logger.info("Tool called: get_page_source")
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        logger.debug("Requesting page source from driver")
        page_source = ios_driver.driver.page_source
        if not page_source:
            error_msg = "Page source is empty"
            logger.warning(error_msg)
            return error_msg
        
        # Clean the XML if requested (default behavior)
        if clean_output is not False:  # None or True
            try:
                from lxml import etree
                import re
                
                # Parse the XML
                parser = etree.XMLParser(remove_blank_text=True)
                tree = etree.fromstring(page_source.encode(), parser)
                
                # Essential attributes for navigation
                essential_attrs = {'name', 'label', 'value', 'type', 'enabled', 'accessible'}
                
                def is_visible_and_enabled(elem: etree._Element) -> bool:
                    """Check if element is visible and enabled."""
                    return (
                        elem.get('visible', '').lower() == 'true' and 
                        elem.get('enabled', '').lower() == 'true'
                    )
                
                # Remove invisible elements and their children
                for elem in tree.xpath('//*[not(@visible="true") or not(@enabled="true")]'):
                    parent = elem.getparent()
                    if parent is not None:
                        parent.remove(elem)
                
                # Clean up remaining visible elements
                for elem in tree.iter():
                    # Keep only essential attributes
                    for attr in list(elem.attrib.keys()):
                        if attr not in essential_attrs:
                            del elem.attrib[attr]
                    
                    # Remove empty attributes
                    for attr in list(elem.attrib.keys()):
                        if not elem.attrib[attr]:
                            del elem.attrib[attr]
                
                # Convert back to string with pretty printing
                page_source = etree.tostring(tree, pretty_print=True, encoding='unicode')
                
                # Remove empty lines
                page_source = re.sub(r'\n\s*\n', '\n', page_source)
                
            except ImportError:
                logger.warning("lxml not installed, returning unclean XML")
            except Exception as e:
                logger.warning(f"Failed to clean XML: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
        
        # Handle diffing if requested
        if diff_only and previous_page_source:
            diff = xml_diff(previous_page_source, page_source)
            if format_output:
                console.print(Panel(diff, title="XML Diff", border_style="green", expand=False))
            
            # Update the previous page source
            previous_page_source = page_source
            return diff
        else:
            # Store current page source for future diffs
            previous_page_source = page_source
            
            if format_output:
                console.print(Panel(page_source, title="Page Source", border_style="blue", expand=False))
            
            logger.info("Page source retrieved successfully")
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
    global previous_page_source
    
    logger.info(f"Tool called: tap_element with id={element_id}, by={by}")
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    if not element_id:
        error_msg = "Element ID cannot be empty"
        logger.error(error_msg)
        print_error(error_msg)
        return error_msg
    
    try:
        # Get page source before interaction
        before_source = ios_driver.driver.page_source
        
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
        
        # Get page source after interaction
        after_source = ios_driver.driver.page_source
        
        # Generate XML diff
        diff = xml_diff(before_source, after_source)
        
        # Update the previous page source
        previous_page_source = after_source
        
        # Display formatted diff in console
        console.print(Panel(diff, title=f"XML Diff - Tapped {element_id}", border_style="green", expand=False))
        
        success_msg = f"Successfully tapped visible element with {by_strategy}: {element_id}\n\nXML Diff:\n{diff}"
        logger.info(f"Successfully tapped visible element with {by_strategy}: {element_id}")
        print_success(f"Successfully tapped visible element with {by_strategy}: {element_id}")
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
    global previous_page_source
    
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        # Get page source before interaction
        before_source = ios_driver.driver.page_source
        
        ios_driver.driver.execute_script('mobile: pressButton', {'name': button.value})
        
        # Get page source after interaction
        after_source = ios_driver.driver.page_source
        
        # Generate XML diff
        diff = xml_diff(before_source, after_source)
        
        # Update the previous page source
        previous_page_source = after_source
        
        # Display formatted diff in console
        console.print(Panel(diff, title=f"XML Diff - Pressed {button.name} button", border_style="green", expand=False))
        
        return f"Successfully pressed {button.name} button\n\nXML Diff:\n{diff}"
    except Exception as e:
        return f"Failed to press button: {str(e)}"

@function_tool
async def swipe(direction: SwipeDirection) -> str:
    """
    Perform a swipe gesture in the specified direction.
    
    Args:
        direction: The direction to swipe
    """
    global previous_page_source
    
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        # Get page source before interaction
        before_source = ios_driver.driver.page_source
        
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
        
        # Get page source after interaction
        after_source = ios_driver.driver.page_source
        
        # Generate XML diff
        diff = xml_diff(before_source, after_source)
        
        # Update the previous page source
        previous_page_source = after_source
        
        # Display formatted diff in console
        console.print(Panel(diff, title=f"XML Diff - Swiped {direction.value}", border_style="green", expand=False))
        
        return f"Successfully performed {direction.value} swipe\n\nXML Diff:\n{diff}"
    except Exception as e:
        return f"Failed to perform swipe: {str(e)}"

@function_tool
async def send_input(element_id: str, text: str, *, by: Optional[LocatorStrategy] = None) -> str:
    """
    Send text input to an element by its identifier.
    
    Args:
        element_id: The identifier of the element
        text: The text to send
        by: The locator strategy to use
    """
    global previous_page_source
    
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        # Get page source before interaction
        before_source = ios_driver.driver.page_source
        
        locator_map = {
            LocatorStrategy.ACCESSIBILITY_ID: AppiumBy.ACCESSIBILITY_ID,
            LocatorStrategy.XPATH: AppiumBy.XPATH,
            LocatorStrategy.NAME: AppiumBy.NAME,
            LocatorStrategy.CLASS_NAME: AppiumBy.CLASS_NAME
        }
        
        by_strategy = locator_map[by] if by else AppiumBy.ACCESSIBILITY_ID
        element = ios_driver.driver.find_element(by=by_strategy, value=element_id)
        element.clear()
        element.send_keys(text)
        
        # Get page source after interaction
        after_source = ios_driver.driver.page_source
        
        # Generate XML diff
        diff = xml_diff(before_source, after_source)
        
        # Update the previous page source
        previous_page_source = after_source
        
        # Display formatted diff in console
        console.print(Panel(diff, title=f"XML Diff - Input '{text}' to {element_id}", border_style="green", expand=False))
        
        return f"Successfully sent input '{text}' to element with {by_strategy}: {element_id}\n\nXML Diff:\n{diff}"
    except Exception as e:
        return f"Failed to send input: {str(e)}"

@function_tool
async def navigate_to(url: str) -> str:
    """
    Navigate to a URL in Safari.
    
    Args:
        url: The URL to navigate to
    """
    global previous_page_source
    
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        # Get page source before interaction
        before_source = ios_driver.driver.page_source
        
        ios_driver.driver.get(url)
        
        # Get page source after interaction
        after_source = ios_driver.driver.page_source
        
        # Generate XML diff
        diff = xml_diff(before_source, after_source)
        
        # Update the previous page source
        previous_page_source = after_source
        
        # Display formatted diff in console
        console.print(Panel(diff, title=f"XML Diff - Navigated to {url}", border_style="green", expand=False))
        
        return f"Successfully navigated to {url}\n\nXML Diff:\n{diff}"
    except Exception as e:
        return f"Failed to navigate: {str(e)}"

@function_tool
async def launch_app(bundle_id: str) -> str:
    """
    Launch an iOS app by its bundle ID.
    
    Args:
        bundle_id: The bundle ID of the app to launch
    """
    global previous_page_source
    
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
                
                # Get page source after interaction
                after_source = ios_driver.driver.page_source
                
                # Update the previous page source
                previous_page_source = after_source
                
                # Display initial XML in console
                console.print(Panel(after_source, title=f"Initial XML - App {bundle_id} Relaunched", border_style="blue", expand=False))
                
                success_msg = f"Successfully relaunched app with bundle ID: {bundle_id}\n\nInitial XML:\n{after_source}"
                logger.info(f"Successfully relaunched app with bundle ID: {bundle_id}")
                print_success(f"Successfully relaunched app with bundle ID: {bundle_id}")
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
            # Get page source after launching
            after_source = ios_driver.driver.page_source
            
            # Update the previous page source
            previous_page_source = after_source
            
            # Display initial XML in console
            console.print(Panel(after_source, title=f"Initial XML - App {bundle_id} Launched", border_style="blue", expand=False))
            
            success_msg = f"Successfully launched app with bundle ID: {bundle_id}\n\nInitial XML:\n{after_source}"
            logger.info(f"Successfully launched app with bundle ID: {bundle_id}")
            print_success(f"Successfully launched app with bundle ID: {bundle_id}")
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
        page_source = ios_driver.driver.page_source
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