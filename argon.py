#!/usr/bin/env python3

# /// script
# dependencies = [
#     "openai-agents",
#     "pytest",
#     "pytest-asyncio",
#     "pytest-xdist",
#     "appium-python-client>=3.1.1",
#     "rich>=13.0.0,<14.0.0",
#     "python-dotenv>=1.0.0",
#     "requests>=2.31.0",
#     "selenium>=4.0.0",
#     "mcp>=0.1.0",
#     "beautifulsoup4>=4.12.0",
#     "lxml>=4.9.0",
#     "openai>=1.0.0",
#     "numpy>=1.24.0",
#     "scikit-learn>=1.3.0"
# ]
# ///

"""
FastMCP Echo Server with Appium Integration
"""

import sys
import traceback

# Print Python path and version for debugging
print(f"Python version: {sys.version}", file=sys.stderr)
print(f"Python path: {sys.path}", file=sys.stderr)

try:
    # Standard library imports
    import atexit
    from datetime import datetime
    from enum import Enum
    from pathlib import Path
    import subprocess
    from typing import Dict, Optional, Tuple, List
    import logging
    import traceback
    import weakref
    import json
    from bs4 import BeautifulSoup
    import openai
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    # Third-party imports
    print("Attempting to import Appium...", file=sys.stderr)
    from appium import webdriver
    from appium.options.ios import XCUITestOptions
    from appium.webdriver.common.appiumby import AppiumBy
    print("Attempting to import MCP...", file=sys.stderr)
    from mcp.server.fastmcp import FastMCP
    print("Successfully imported MCP", file=sys.stderr)
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    print("Successfully imported all dependencies", file=sys.stderr)

except ImportError as e:
    print(f"Import Error: {str(e)}", file=sys.stderr)
    print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Starting server initialization...", file=sys.stderr)

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

class IOSDriver:
    _instances = set()
    
    def __init__(self):
        self.driver = None
        self.device_info = None
        # Add self to the set of instances
        self._instances.add(weakref.ref(self))
        logger.debug("IOSDriver instance created")
    
    @classmethod
    def _cleanup_all(cls):
        """Clean up all driver instances."""
        logger.info("Cleaning up all driver instances")
        for instance_ref in cls._instances:
            instance = instance_ref()
            if instance is not None:
                try:
                    instance.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up instance: {str(e)}")
    
    def detect_real_device(self) -> Optional[Dict[str, str]]:
        """Detect connected iOS device using libimobiledevice."""
        try:
            # Run ideviceinfo to get device information
            result = subprocess.run(['ideviceinfo'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.debug("No iOS device detected with ideviceinfo")
                return None
                
            # Parse the output to get device details
            lines = result.stdout.strip().split('\n')
            device_info = {}
            for line in lines:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    device_info[key.strip()] = value.strip()
            
            # Extract relevant information
            if 'UniqueDeviceID' in device_info:
                logger.info(f"Found iOS device with UDID: {device_info['UniqueDeviceID']}")
                return {
                    'udid': device_info['UniqueDeviceID'],
                    'name': device_info.get('DeviceName', 'iOS Device'),
                    'ios_version': device_info.get('ProductVersion', ''),
                    'product_type': device_info.get('ProductType', '')
                }
        except Exception as e:
            logger.error(f"Error detecting iOS device: {str(e)}")
        
        return None

    def init_driver(self, bundle_id: str):
        """Initialize the Appium driver with the given bundle ID."""
        if not bundle_id:
            logger.error("Cannot initialize driver: Empty bundle ID")
            return False
            
        if self.driver:
            logger.info("Driver already exists, cleaning up before re-initialization")
            self.cleanup()
            
        logger.info(f"Initializing iOS driver for bundle ID: {bundle_id}")
        
        # Try to detect real device first
        self.device_info = self.detect_real_device()
        
        # Create Appium options object
        options = XCUITestOptions()
        
        # Set required capabilities
        options.platform_name = "iOS"
        options.automation_name = "XCUITest"
        
        # Use detected device info if available, otherwise use defaults
        if self.device_info:
            logger.info("Using detected real device configuration")
            options.device_name = self.device_info['name']
            options.platform_version = self.device_info['ios_version']
            options.udid = self.device_info['udid']
            
            # Configure WDA settings for real device
            options.set_capability("appium:wdaLocalPort", 8100)
            options.set_capability("appium:useNewWDA", False)
            options.set_capability("appium:usePrebuiltWDA", False)
            options.set_capability("appium:wdaStartupRetries", 4)
            options.set_capability("appium:wdaStartupRetryInterval", 20000)
            options.set_capability("appium:shouldUseSingletonTestManager", False)
            options.set_capability("appium:shouldTerminateApp", True)
            options.set_capability("appium:isRealMobile", True)
            
            # Set status bar time
            options.set_capability("appium:statusBarTime", "9:41")
            options.set_capability("appium:forceStatusBarTime", True)
        else:
            logger.info("No real device detected, using simulator configuration")
            options.device_name = "iPhone 16 Pro"  # Default simulator
            options.platform_version = "18.2"  # Default iOS version
        
        options.bundle_id = bundle_id
        
        try:
            logger.debug(f"Connecting to Appium server at http://localhost:4723")
            logger.debug(f"Using options: {options.to_capabilities()}")
            
            # Create the driver with options
            self.driver = webdriver.Remote(command_executor='http://localhost:4723', options=options)
            
            if not self.driver:
                logger.error("Driver creation returned None")
                return False
                
            logger.info("Successfully initialized iOS driver")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize iOS driver: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return False

    def cleanup(self):
        """Clean up the driver instance."""
        logger.info("Cleaning up driver instance")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error during driver cleanup: {str(e)}")
            finally:
                self.driver = None

    def tap_element(self, **locator):
        """Tap an element identified by the given locator."""
        if not self.driver:
            logger.error("Cannot tap element: No active driver")
            return False, "No active driver"
            
        if not locator:
            logger.error("Cannot tap element: No locator provided")
            return False, "No locator provided"
            
        logger.info(f"Attempting to tap element with locator: {locator}")
        try:
            # Use the first available locator
            locator_type = next(iter(locator.keys()), None)
            locator_value = locator.get(locator_type)
            
            if not locator_type or not locator_value:
                logger.error("Invalid locator format")
                return False, "Invalid locator format"
                
            logger.debug(f"Using locator: {locator_type}={locator_value}")
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((AppiumBy.CLASS_NAME, locator.get('class_name')))
            )
            element.click()
            logger.info("Successfully tapped element")
            return True, "Successfully tapped element"
        except TimeoutException:
            logger.warning(f"Element not found within timeout: {locator}")
            return False, "Element not found within timeout"
        except Exception as e:
            logger.error(f"Failed to tap element: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return False, f"Failed to tap element: {str(e)}"

    def get_page_source(self):
        """Get the current page source."""
        if not self.driver:
            logger.error("Cannot get page source: No active driver")
            return None
            
        try:
            logger.info("Getting page source")
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Failed to get page source: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return None

# Register cleanup for all instances
atexit.register(IOSDriver._cleanup_all)

# Create a singleton instance
ios_driver = IOSDriver()

# Create server
mcp = FastMCP("Argon")

def init_appium():
    """Initialize connection to Appium server"""
    try:
        # Initialize with Safari as default
        result = ios_driver.init_driver("com.apple.mobilesafari")
        if not result:
            logger.error("Failed to initialize Appium connection")
            return False
        logger.info("Successfully initialized Appium connection")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Appium: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return False

# Initialize Appium connection
init_appium()

def check_driver_connection() -> Tuple[bool, str]:
    """Check if driver is connected and return status."""
    if not ios_driver.driver:
        error_msg = "No active Appium session"
        logger.error(error_msg)
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
        page_source = ios_driver.driver.page_source
        if not page_source:
            logger.warning("Page source is empty")
            return None
        return page_source
    except Exception as e:
        logger.error(f"Error getting page source: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None

class UIElement:
    """Represents a UI element with its properties and vector embedding."""
    def __init__(self, element_type: str, text: str, attributes: Dict[str, str]):
        self.element_type = element_type
        self.text = text
        self.attributes = attributes
        self.embedding: Optional[np.ndarray] = None
        
    def to_text(self) -> str:
        """Convert element to searchable text representation."""
        attrs = ' '.join(f'{k}="{v}"' for k, v in self.attributes.items())
        return f"Type: {self.element_type} Text: {self.text} Attributes: {attrs}"
        
    def __str__(self) -> str:
        return self.to_text()

class RAGPageSource:
    """RAG implementation for searching UI elements."""
    def __init__(self):
        self.elements: List[UIElement] = []
        self.embeddings: Optional[np.ndarray] = None
        
    async def compute_embedding(self, text: str) -> np.ndarray:
        """Compute embedding for a text string using OpenAI's API."""
        try:
            response = await openai.Embedding.acreate(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logger.error(f"Error computing embedding: {str(e)}")
            raise

    async def add_elements(self, page_source: str):
        """Parse page source and compute embeddings for all elements."""
        try:
            # Parse XML
            soup = BeautifulSoup(page_source, 'lxml')
            self.elements = []
            
            # Extract elements
            for element in soup.find_all(True):
                ui_element = UIElement(
                    element_type=element.name,
                    text=element.get_text(strip=True),
                    attributes=dict(element.attrs)
                )
                self.elements.append(ui_element)
            
            # Compute embeddings for all elements
            embeddings = []
            for element in self.elements:
                element_text = element.to_text()
                embedding = await self.compute_embedding(element_text)
                embeddings.append(embedding)
                
            self.embeddings = np.vstack(embeddings)
            
        except Exception as e:
            logger.error(f"Error adding elements: {str(e)}")
            raise

    async def search(self, query: str, top_k: int = 5) -> List[Tuple[UIElement, float]]:
        """Search for elements most similar to the query."""
        try:
            # Get query embedding
            query_embedding = await self.compute_embedding(query)
            
            # Compute similarities
            similarities = cosine_similarity(query_embedding.reshape(1, -1), self.embeddings)[0]
            
            # Get top k results
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            return [(self.elements[i], similarities[i]) for i in top_indices]
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            raise

def format_search_results(results: List[Tuple[UIElement, float]]) -> str:
    """Format search results into a readable string."""
    output = []
    for element, score in results:
        relevance = "High" if score > 0.8 else "Medium" if score > 0.5 else "Low"
        output.append(f"[Relevance: {relevance} ({score:.2f})]")
        output.append(f"Element Type: {element.element_type}")
        if element.text:
            output.append(f"Text: {element.text}")
        if element.attributes:
            output.append("Attributes:")
            for key, value in element.attributes.items():
                output.append(f"  {key}: {value}")
        output.append("")
    
    return "\n".join(output)

@mcp.tool()
async def get_page_source_tool(query: Optional[str] = None) -> str:
    """
    Get the current page source and search through it using RAG.
    
    Args:
        query: Optional search query to find specific elements
    """
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        page_source = get_clean_page_source()
        if not page_source:
            error_msg = "Page source is empty or could not be retrieved"
            logger.warning(error_msg)
            return error_msg
        
        # Initialize RAG
        rag = RAGPageSource()
        await rag.add_elements(page_source)
        
        if query:
            # Perform semantic search
            logger.info(f"Performing RAG search with query: {query}")
            results = await rag.search(query)
            return format_search_results(results)
        else:
            # Return summary
            total_elements = len(rag.elements)
            element_types = set(e.element_type for e in rag.elements)
            return f"Page contains {total_elements} elements of types: {', '.join(sorted(element_types))}. Use a search query to find specific elements."
        
    except Exception as e:
        error_msg = f"Failed to process page source: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

@mcp.tool()
async def tap_element_tool(element_id: str, by: LocatorStrategy = None) -> str:
    """
    Tap an element by its identifier.
    
    Args:
        element_id: The identifier of the element to tap
        by: The locator strategy to use (optional)
    """
    logger.info(f"Tool called: tap_element with id={element_id}, by={by}")
    
    if not element_id:
        error_msg = "Element ID cannot be empty"
        logger.error(error_msg)
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
            return error_msg
        
        if not element.is_displayed():
            warning_msg = f"Element with {by_strategy}: {element_id} is not visible"
            logger.warning(warning_msg)
            return warning_msg
        
        element.click()
        
        success_msg = f"Successfully tapped visible element with {by_strategy}: {element_id}"
        logger.info(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to tap element: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

@mcp.tool()
async def press_button_tool(button: PhysicalButton) -> str:
    """
    Press a physical button on the iOS device.
    
    Args:
        button: The button to press (HOME, VOLUME_UP, VOLUME_DOWN, POWER)
    """
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        ios_driver.driver.execute_script('mobile: pressButton', {'name': button.value})
        
        success_msg = f"Successfully pressed {button.name} button"
        logger.info(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to press button: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

@mcp.tool()
async def swipe_tool(direction: SwipeDirection = None, start_x: int = None, start_y: int = None, 
                    end_x: int = None, end_y: int = None) -> str:
    """
    Perform a swipe gesture in the specified direction or between coordinates.
    
    Args:
        direction: The direction to swipe (optional)
        start_x: Starting X coordinate (optional)
        start_y: Starting Y coordinate (optional)
        end_x: Ending X coordinate (optional)
        end_y: Ending Y coordinate (optional)
    """
    logger.info(f"Tool called: swipe with direction={direction}, coordinates=({start_x}, {start_y}) to ({end_x}, {end_y})")
    
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        window_size = ios_driver.driver.get_window_size()
        width = window_size['width']
        height = window_size['height']
        
        using_coordinates = all(coord is not None for coord in [start_x, start_y, end_x, end_y])
        using_direction = direction is not None
        
        if not using_coordinates and not using_direction:
            error_msg = "Either direction or all coordinates (start_x, start_y, end_x, end_y) must be provided"
            logger.error(error_msg)
            return error_msg
        
        if using_coordinates:
            if (start_x < 0 or start_x > width or start_y < 0 or start_y > height or 
                end_x < 0 or end_x > width or end_y < 0 or end_y > height):
                warning_msg = (f"Some coordinates are outside screen bounds ({width}x{height}). "
                              f"Coordinates: ({start_x}, {start_y}) to ({end_x}, {end_y})")
                logger.warning(warning_msg)
            
            logger.info(f"Swiping with raw coordinates: ({start_x}, {start_y}) to ({end_x}, {end_y})")
            ios_driver.driver.swipe(start_x, start_y, end_x, end_y, 500)
            
            success_msg = f"Successfully performed coordinate swipe from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            logger.info(success_msg)
            return success_msg
        else:
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
            return success_msg
    except Exception as e:
        error_msg = f"Failed to perform swipe: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

@mcp.tool()
async def send_input_tool(element_id: str, text: str, by: LocatorStrategy = None) -> str:
    """
    Send text input to an element by its identifier.
    
    Args:
        element_id: The identifier of the element
        text: The text to send
        by: The locator strategy to use (optional)
    """
    logger.info(f"Tool called: send_input with id={element_id}, text={text}, by={by}")
    
    if not element_id:
        error_msg = "Element ID cannot be empty"
        logger.error(error_msg)
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
            return error_msg
        
        element.clear()
        element.send_keys(text)
        
        success_msg = f"Successfully sent input '{text}' to element with {by_strategy}: {element_id}"
        logger.info(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to send input: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

@mcp.tool()
async def navigate_tool(url: str) -> str:
    """
    Navigate to a URL in Safari.
    
    Args:
        url: The URL to navigate to
    """
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        ios_driver.driver.get(url)
        
        success_msg = f"Successfully navigated to {url}"
        logger.info(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to navigate: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

@mcp.tool()
async def launch_app_tool(bundle_id: str) -> str:
    """
    Launch an iOS app by its bundle ID.
    
    Args:
        bundle_id: The bundle ID of the app to launch
    """
    logger.info(f"Tool called: launch_app with bundle_id={bundle_id}")
    
    if not bundle_id:
        error_msg = "Bundle ID cannot be empty"
        logger.error(error_msg)
        return error_msg
    
    try:
        if ios_driver.driver:
            logger.info(f"Driver exists, attempting to terminate and reactivate app: {bundle_id}")
            try:
                ios_driver.driver.terminate_app(bundle_id)
                ios_driver.driver.activate_app(bundle_id)
                
                success_msg = f"Successfully relaunched app with bundle ID: {bundle_id}"
                logger.info(success_msg)
                return success_msg
            except Exception as e:
                logger.warning(f"Failed to relaunch app via existing driver: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                logger.info("Will try to re-initialize driver")
                ios_driver.cleanup()
        
        logger.info(f"Initializing driver for app: {bundle_id}")
        result = ios_driver.init_driver(bundle_id)
        
        if result:
            success_msg = f"Successfully launched app with bundle ID: {bundle_id}"
            logger.info(success_msg)
            return success_msg
        else:
            error_msg = f"Failed to initialize driver for app: {bundle_id}"
            logger.error(error_msg)
            return error_msg
    except Exception as e:
        error_msg = f"Failed to launch app: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

@mcp.tool()
async def take_screenshot_tool() -> str:
    """Take a screenshot and save page source of the current app state."""
    logger.info("Tool called: take_screenshot")
    driver_status, message = check_driver_connection()
    if not driver_status:
        return message
    
    try:
        app_dir_name = "unknown_app"
        bundle_id = None
        try:
            bundle_id = ios_driver.driver.capabilities.get('bundleId')
            if bundle_id:
                app_dir_name = bundle_id.split('.')[-1].lower()
        except Exception as e:
            logger.warning(f"Could not get bundle ID: {str(e)}")
        
        output_dir = Path("artifacts")
        app_dir = output_dir / app_dir_name
        screenshots_dir = app_dir / "screenshots"
        pagesource_dir = app_dir / "pagesource"
        
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        pagesource_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshots_dir / f"screenshot_{timestamp}.png"
        pagesource_path = pagesource_dir / f"pagesource_{timestamp}.xml"
        
        logger.debug(f"Saving screenshot to: {screenshot_path}")
        ios_driver.driver.get_screenshot_as_file(str(screenshot_path))
        
        logger.debug(f"Saving page source to: {pagesource_path}")
        page_source = get_clean_page_source()
        if not page_source:
            page_source = ios_driver.driver.page_source
        
        if not page_source.startswith('<?xml'):
            page_source = '<?xml version="1.0" encoding="UTF-8"?>\n' + page_source
            
        pagesource_path.write_text(page_source, encoding='utf-8')
        
        success_msg = f"Artifacts saved successfully:\nApp: {bundle_id if bundle_id else app_dir_name}\nScreenshot: {screenshot_path}\nPage Source: {pagesource_path}"
        logger.info(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Failed to capture artifacts: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return error_msg

if __name__ == "__main__":
    mcp.run(transport="sse")
