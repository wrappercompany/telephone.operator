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
    
    try:
        from lxml import etree
        import re
        
        # Try to format both XMLs consistently before diffing
        def format_xml_string(xml_str):
            try:
                parser = etree.XMLParser(remove_blank_text=True)
                tree = etree.fromstring(xml_str.encode(), parser)
                formatted = etree.tostring(tree, pretty_print=True, encoding='unicode')
                
                # Apply consistent formatting
                lines = formatted.splitlines()
                indent_level = 0
                formatted_lines = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    
                    # Adjust indent level based on XML structure
                    if stripped.startswith('</'):
                        # Closing tag reduces indent level
                        indent_level = max(0, indent_level - 1)
                    
                    # Add proper indentation
                    formatted_lines.append('  ' * indent_level + stripped)
                    
                    # Opening tag or self-closing tag
                    if stripped.endswith('>') and not stripped.endswith('/>') and not stripped.startswith('</'):
                        # Check if this is not a self-closing tag
                        if '</' not in stripped:
                            indent_level += 1
                
                return '\n'.join(formatted_lines)
            except Exception:
                # If formatting fails, return original
                return xml_str
        
        # Format both XML strings consistently
        old_xml = format_xml_string(old_xml)
        new_xml = format_xml_string(new_xml)
        
    except ImportError:
        # If lxml not available, continue with raw strings
        pass
    
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
            if not (line.startswith('+++') and 'after' in line):
                # Green for additions
                formatted_lines.append(f"[bold green]{line}[/bold green]")
            else:
                formatted_lines.append(line)
        elif line.startswith('-'):
            if not (line.startswith('---') and 'before' in line):
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

def get_clean_page_source() -> Optional[str]:
    """
    Get and clean the current page source.
    Returns formatted XML with essential elements and attributes preserved.
    """
    logger.debug("Getting and cleaning page source")
    
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
        
        try:
            from lxml import etree
            import re
            
            # Parse the XML
            parser = etree.XMLParser(remove_blank_text=True)
            try:
                tree = etree.fromstring(page_source.encode(), parser)
            except etree.XMLSyntaxError as xml_err:
                logger.warning(f"XML parsing error: {str(xml_err)}")
                # If there's an XML syntax error, return the raw page source
                return page_source
            
            # Essential attributes to keep - expanded list
            essential_attrs = {
                'name', 'label', 'value', 'type', 'enabled', 'index', 'text'
            }
            
            def has_important_attributes(elem: etree._Element) -> bool:
                """Check if element has important attributes like name or label."""
                return (elem.get('name') is not None or 
                       elem.get('label') is not None or 
                       elem.get('value') is not None)
            
            def has_important_descendants(elem: etree._Element) -> bool:
                """Check if any descendant has a name or label."""
                return any(has_important_attributes(descendant) for descendant in elem.xpath('.//*'))
            
            def should_keep_element(elem: etree._Element) -> bool:
                """
                Determine if an element should be kept in the cleaned XML.
                Keep elements that have a name/label or have descendants with names/labels.
                Always keep root and structural elements.
                """
                # Always keep root and near-root elements
                if elem.getparent() is None or elem.getparent().getparent() is None:
                    return True
                
                # Keep if it has important attributes
                if has_important_attributes(elem):
                    return True
                
                # Keep if it has type and children with important attributes
                if elem.get('type') is not None and (len(elem) > 0 and has_important_descendants(elem)):
                    return True
                
                # Otherwise don't keep
                return False
            
            # First pass: identify elements to remove
            elements_to_remove = []
            for elem in tree.xpath('//*'):
                if not should_keep_element(elem):
                    elements_to_remove.append(elem)
            
            # Second pass: remove identified elements but preserve their children
            for elem in elements_to_remove:
                parent = elem.getparent()
                if parent is not None:  # Skip root element
                    # Get the index of the element to remove
                    idx = parent.index(elem)
                    
                    # Add all children to the parent at the same position
                    for i, child in enumerate(list(elem)):
                        # Remove the child from original parent first
                        elem.remove(child)
                        # Insert at the correct position in the grandparent
                        parent.insert(idx + i, child)
                    
                    # Now remove the empty element
                    parent.remove(elem)
            
            # Clean up remaining elements - remove non-essential attributes
            for elem in tree.xpath('//*'):
                for attr in list(elem.attrib.keys()):
                    if attr not in essential_attrs:
                        del elem.attrib[attr]
            
            # Convert back to string with pretty printing
            page_source = etree.tostring(tree, pretty_print=True, encoding='unicode')
            
            # Apply more readable formatting to the XML
            # Remove empty lines
            page_source = re.sub(r'\n\s*\n', '\n', page_source)
            # Clean up spacing between elements
            page_source = re.sub(r'>\s+<', '>\n<', page_source)
            # Add proper indentation for nested elements
            lines = page_source.splitlines()
            indent_level = 0
            formatted_lines = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                
                # Adjust indent level based on XML structure
                if stripped.startswith('</'):
                    # Closing tag reduces indent level
                    indent_level = max(0, indent_level - 1)
                
                # Add proper indentation
                formatted_lines.append('  ' * indent_level + stripped)
                
                # Opening tag or self-closing tag
                if stripped.endswith('>') and not stripped.endswith('/>') and not stripped.startswith('</'):
                    # Check if this is not a self-closing tag
                    if '</' not in stripped:
                        indent_level += 1
            
            page_source = '\n'.join(formatted_lines)
            
            logger.debug("Page source cleaned and formatted successfully")
            return page_source
            
        except ImportError:
            logger.warning("lxml not installed, returning unclean XML")
            return page_source
        except Exception as e:
            logger.warning(f"Failed to clean XML: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return page_source
    except Exception as e:
        logger.error(f"Error getting page source: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None

# Type variable for generic function signatures
T = TypeVar('T')

async def with_page_source_diff(
    action_fn: Callable[..., Awaitable[Any]],
    action_name: str,
    *args,
    **kwargs
) -> str:
    """
    Wrapper function that:
    1. Gets page source before action
    2. Performs the action
    3. Gets page source after action
    4. Generates and displays the diff
    
    Args:
        action_fn: The async function to perform the action
        action_name: Name of the action for display in diff panel
        *args, **kwargs: Arguments to pass to the action function
    
    Returns:
        A string with the action result and diff information
    """
    global previous_page_source
    
    # Check driver connection
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Get page source before action
        before_source = get_clean_page_source()
        if not before_source:
            logger.warning("Could not get page source before action")
            before_source = ""
        
        # Perform the action
        result = await action_fn(*args, **kwargs)
        if isinstance(result, tuple) and len(result) >= 2:
            success, message = result[0], result[1]
            if not success:
                return message
        
        # Get page source after action
        after_source = get_clean_page_source()
        if not after_source:
            logger.warning("Could not get page source after action")
            return f"Action completed, but could not get page source: {result}"
        
        # Generate diff
        diff = xml_diff(before_source, after_source)
        
        # Display diff in console
        console.print(Panel(diff, title=f"XML Diff - {action_name}", border_style="green", expand=False))
        
        # Update previous page source
        previous_page_source = after_source
        
        # Return result with diff
        if isinstance(result, str):
            return f"{result}\n\nXML Diff:\n{diff}"
        elif isinstance(result, tuple) and len(result) >= 2:
            return f"{result[1]}\n\nXML Diff:\n{diff}"
        else:
            return f"Action completed successfully\n\nXML Diff:\n{diff}"
    except Exception as e:
        error_msg = f"Error performing action with diff: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        print_error(error_msg)
        return error_msg

@function_tool
async def get_page_source() -> str:
    """
    Get the current page source of the application.
    Always returns a cleaned, formatted XML with diffs from the previous state.
    """
    global previous_page_source
    
    logger.info("Tool called: get_page_source")
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Get cleaned page source using our helper function
        page_source = get_clean_page_source()
        if not page_source:
            error_msg = "Page source is empty or could not be cleaned"
            logger.warning(error_msg)
            return error_msg
        
        # Generate diff if we have a previous page source
        if previous_page_source:
            diff = xml_diff(previous_page_source, page_source)
            # Display formatted diff
            console.print(Panel(diff, title="XML Diff", border_style="green", expand=False))
        
        # Always display formatted current page source
        console.print(Panel(page_source, title="Page Source", border_style="blue", expand=False))
        
        # Store current page source for future diffs
        previous_page_source = page_source
        
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
    logger.info(f"Tool called: tap_element with id={element_id}, by={by}")
    
    if not element_id:
        error_msg = "Element ID cannot be empty"
        logger.error(error_msg)
        print_error(error_msg)
        return error_msg
    
    async def perform_tap() -> Tuple[bool, str]:
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
                return False, error_msg
            
            # Check if element is visible
            if not element.is_displayed():
                warning_msg = f"Element with {by_strategy}: {element_id} is not visible"
                logger.warning(warning_msg)
                print_warning(warning_msg)
                return False, warning_msg
                
            element.click()
            
            success_msg = f"Successfully tapped visible element with {by_strategy}: {element_id}"
            logger.info(success_msg)
            print_success(success_msg)
            return True, success_msg
        except Exception as e:
            error_msg = f"Failed to tap element: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            print_error(error_msg)
            return False, error_msg
    
    # Use the common wrapper for page source diff handling
    return await with_page_source_diff(perform_tap, f"Tapped {element_id}")

@function_tool
async def press_physical_button(button: PhysicalButton) -> str:
    """
    Press a physical button on the iOS device.
    
    Args:
        button: The button to press
    """
    global previous_page_source
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Get page source before action
        before_source = get_clean_page_source()
        if not before_source:
            logger.warning("Could not get page source before button press")
            before_source = ""
        
        # Execute the button press
        ios_driver.driver.execute_script('mobile: pressButton', {'name': button.value})
        
        # Get page source after action
        after_source = get_clean_page_source()
        if not after_source:
            logger.warning("Could not get page source after button press")
            return f"Successfully pressed {button.name} button, but could not get updated page source"
        
        # Generate XML diff
        diff = xml_diff(before_source, after_source)
        
        # Update the previous page source
        previous_page_source = after_source
        
        # Display formatted diff in console
        console.print(Panel(diff, title=f"XML Diff - Pressed {button.name} button", border_style="green", expand=False))
        
        return f"Successfully pressed {button.name} button\n\nXML Diff:\n{diff}"
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
    
    async def perform_swipe() -> Tuple[bool, str]:
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
            return True, success_msg
        except Exception as e:
            error_msg = f"Failed to perform swipe: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            print_error(error_msg)
            return False, error_msg
    
    # Use the common wrapper for page source diff handling
    return await with_page_source_diff(perform_swipe, f"Swiped {direction.value}")

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
    
    async def perform_input() -> Tuple[bool, str]:
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
                return False, error_msg
                
            element.clear()
            element.send_keys(text)
            
            success_msg = f"Successfully sent input '{text}' to element with {by_strategy}: {element_id}"
            logger.info(success_msg)
            print_success(success_msg)
            return True, success_msg
        except Exception as e:
            error_msg = f"Failed to send input: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            print_error(error_msg)
            return False, error_msg
    
    # Use the common wrapper for page source diff handling
    return await with_page_source_diff(perform_input, f"Input '{text}' to {element_id}")

@function_tool
async def navigate_to(url: str) -> str:
    """
    Navigate to a URL in Safari.
    
    Args:
        url: The URL to navigate to
    """
    global previous_page_source
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        # Get page source before navigation
        before_source = get_clean_page_source()
        if not before_source:
            logger.warning("Could not get page source before navigation")
            before_source = ""
        
        # Navigate to URL
        ios_driver.driver.get(url)
        
        # Get page source after navigation
        after_source = get_clean_page_source()
        if not after_source:
            logger.warning("Could not get page source after navigation")
            return f"Successfully navigated to {url}, but could not get updated page source"
        
        # Generate XML diff
        diff = xml_diff(before_source, after_source)
        
        # Update the previous page source
        previous_page_source = after_source
        
        # Display formatted diff in console
        console.print(Panel(diff, title=f"XML Diff - Navigated to {url}", border_style="green", expand=False))
        
        return f"Successfully navigated to {url}\n\nXML Diff:\n{diff}"
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
    global previous_page_source
    
    logger.info(f"Tool called: launch_app with bundle_id={bundle_id}")
    
    if not bundle_id:
        error_msg = "Bundle ID cannot be empty"
        logger.error(error_msg)
        print_error(error_msg)
        return error_msg
    
    async def perform_launch() -> Tuple[bool, str]:
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
                    return True, success_msg
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
                return True, success_msg
            else:
                error_msg = f"Failed to initialize driver for app: {bundle_id}"
                logger.error(error_msg)
                print_error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"Failed to launch app: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            print_error(error_msg)
            return False, error_msg
    
    # Launch the app first
    result = await perform_launch()
    if isinstance(result, tuple) and not result[0]:
        return result[1]
    
    # Then get and display the page source
    page_source = get_clean_page_source()
    if page_source:
        # Update previous page source
        previous_page_source = page_source
        
        # Display initial XML in console
        console.print(Panel(page_source, title=f"Initial XML - App {bundle_id} Launched", border_style="blue", expand=False))
        
        return f"{result[1]}\n\nInitial XML:\n{page_source}"
    else:
        return result[1]

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
        # Get cleaned and properly formatted page source for better readability
        page_source = get_clean_page_source()
        if not page_source:
            # Fall back to raw page source if cleaning fails
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