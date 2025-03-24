#!/usr/bin/env python3

# /// script
# dependencies = [
#   "Appium-Python-Client>=3.1.0",
#   "fastmcp>=0.1.0",
#   "urllib3<2.0.0",
#   "pydantic>=2.0.0",
#   "libimobiledevice",
# ]
# ///

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import asyncio
import logging
import datetime
import urllib3
import subprocess
import json
import difflib  # This is a standard library module
from pydantic import BaseModel

from mcp.server.fastmcp import FastMCP
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.appium_service import AppiumService
from appium.webdriver.common.appiumby import AppiumBy

# Suppress urllib3 connection warnings
urllib3.disable_warnings(urllib3.exceptions.NewConnectionError)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

class Config:
    """Configuration settings for the Appium server."""
    DEVICE_NAME = "iPhone 16 Pro"  # Fallback simulator name
    IOS_VERSION = "18.2"  # Fallback iOS version
    APPIUM_HOST = "127.0.0.1"
    APPIUM_PORT = 4723
    LOG_DIR = Path("logs")
    DEFAULT_BUNDLE_ID = "com.apple.mobilesafari"
    USE_REAL_DEVICE = True  # Prefer real device over simulator

class LocatorStrategy(str, Enum):
    """Valid locator strategies for finding elements."""
    ACCESSIBILITY_ID = "accessibility_id"
    XPATH = "xpath"
    NAME = "name"
    CLASS_NAME = "class_name"

class PhysicalButton(str, Enum):
    """Valid physical buttons that can be pressed."""
    HOME = "home"
    VOLUME_UP = "volumeUp"
    VOLUME_DOWN = "volumeDown"
    POWER = "power"

class SwipeDirection(str, Enum):
    """Valid swipe directions."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

class IOSDeviceManager:
    """Manages iOS device interactions through Appium."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Remote] = None
        self.appium_service: Optional[AppiumService] = None
        self.logger = self._setup_logging()
        self.device_info: Optional[Dict[str, str]] = None
        self.last_page_source: Optional[str] = None

    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the application."""
        Config.LOG_DIR.mkdir(exist_ok=True)
        
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = Config.LOG_DIR / f"app_{current_time}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        # Suppress noisy loggers
        for logger_name in ["uvicorn.access", "uvicorn.error", "fastapi"]:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
            
        return logging.getLogger(__name__)

    def _detect_real_device(self) -> Optional[Dict[str, str]]:
        """Detect connected iOS device using libimobiledevice."""
        try:
            # Get list of connected devices
            result = subprocess.run(['idevice_id', '-l'], capture_output=True, text=True)
            if result.returncode != 0 or not result.stdout.strip():
                self.logger.info("No real devices detected")
                return None

            udid = result.stdout.strip().split('\n')[0]
            
            # Get device info
            info_result = subprocess.run(['ideviceinfo', '-u', udid], capture_output=True, text=True)
            if info_result.returncode != 0:
                return None

            info_lines = info_result.stdout.strip().split('\n')
            device_info = {}
            for line in info_lines:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    device_info[key.strip()] = value.strip()

            return {
                'udid': udid,
                'name': device_info.get('DeviceName', 'iPhone'),
                'version': device_info.get('ProductVersion', Config.IOS_VERSION)
            }
        except Exception as e:
            self.logger.error(f"Error detecting real device: {e}")
            return None

    async def initialize_session(self, bundle_id: str = Config.DEFAULT_BUNDLE_ID):
        """Initialize the Appium session for iOS."""
        try:
            if Config.USE_REAL_DEVICE:
                self.device_info = self._detect_real_device()
                
            await self._start_appium_service()
            
            if self.device_info:
                self.logger.info(f"Using real device: {self.device_info['name']} ({self.device_info['version']})")
            else:
                self.logger.info("Using simulator")
                await self._configure_simulator()
                
            await self._create_driver_session(bundle_id)
        except Exception as e:
            self.logger.error(f"Failed to initialize session: {e}")
            await self.cleanup()
            raise

    async def _start_appium_service(self):
        """Start the Appium server service."""
        self.appium_service = AppiumService()
        self.appium_service.start(
            args=[
                '--address', Config.APPIUM_HOST,
                '-p', str(Config.APPIUM_PORT),
                '--log-level', 'info',
                '--local-timezone',
                '--debug-log-spacing'
            ],
            timeout_ms=20000
        )
        self.logger.info("Appium server started")

    async def _configure_simulator(self):
        """Configure simulator status bar and settings."""
        import subprocess
        try:
            subprocess.run([
                'xcrun', 'simctl', 'status_bar', Config.DEVICE_NAME, 'override',
                '--time', '9:41',
                '--batteryState', 'charged',
                '--batteryLevel', '100',
                '--cellularMode', 'active',
                '--cellularBars', '4',
                '--operatorName', 'Carrier',
                '--dataNetwork', '5g-uc',
                '--wifiMode', 'active',
                '--wifiBars', '3'
            ], check=True)
            self.logger.info("Simulator status bar configured")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to configure simulator: {e}")

    async def _create_driver_session(self, bundle_id: str):
        """Create a new WebDriver session."""
        options = XCUITestOptions()
        options.platform_name = "iOS"
        options.automation_name = "XCUITest"
        
        if self.device_info:
            options.device_name = self.device_info['name']
            options.platform_version = self.device_info['version']
            options.udid = self.device_info['udid']
        else:
            options.device_name = Config.DEVICE_NAME
            options.platform_version = Config.IOS_VERSION
            
        options.bundle_id = bundle_id

        # Additional capabilities for real devices
        if self.device_info:
            options.additional_capabilities = {
                'xcodeOrgId': subprocess.getoutput('defaults read com.apple.Xcode XCIDETeamId').strip(),
                'xcodeSigningId': 'iPhone Developer',
                'wdaLocalPort': 8100,
                'useNewWDA': True,
                'derivedDataPath': str(Path.home() / 'Library/Developer/Xcode/DerivedData'),
                'preventWDAAttachments': True,
                'simpleIsVisibleCheck': True
            }

        appium_url = f"http://{Config.APPIUM_HOST}:{Config.APPIUM_PORT}"
        self.driver = webdriver.Remote(appium_url, options=options)
        self.logger.info(f"iOS session initialized with {bundle_id}")
        
        # Wait briefly for the app to stabilize
        await asyncio.sleep(1)
        
        # Initialize the last_page_source with the current page source
        try:
            self.last_page_source = self.driver.page_source
            self.logger.info("Initial page source captured")
        except Exception as e:
            self.logger.warning(f"Failed to capture initial page source: {e}")
            self.last_page_source = None

    async def cleanup(self):
        """Cleanup resources."""
        if self.driver:
            self.driver.quit()
        if self.appium_service:
            self.appium_service.stop()

    def get_page_source_diff(self) -> Tuple[str, str]:
        """
        Get the current page source and compute diff with the previous one.
        Returns a tuple of (current page source, diff from previous page source)
        """
        if not self.driver:
            return None, "No active Appium session"
        
        current_page_source = self.driver.page_source
        
        if self.last_page_source is None:
            diff = "Initial page source - no diff available"
        else:
            # Format both current and previous page sources for better diff readability
            # Always simplify for better readability
            formatted_current = self.format_page_source(current_page_source)
            formatted_previous = self.format_page_source(self.last_page_source)
            
            diff_lines = difflib.unified_diff(
                formatted_previous.splitlines(),
                formatted_current.splitlines(),
                fromfile="Previous Page",
                tofile="Current Page",
                lineterm="",
                n=3
            )
            diff = "\n".join(diff_lines)
        
        # Update the last page source
        self.last_page_source = current_page_source
        
        return current_page_source, diff

    def format_page_source(self, page_source: str) -> str:
        """
        Format page source for better readability.
        Always simplifies output by removing verbose XCUITest attributes.
        
        Args:
            page_source: The page source XML to format
        """
        if not page_source:
            return "Empty page source"
        
        # Simple XML formatting attempt
        try:
            import xml.dom.minidom
            
            # Always simplify for better readability
            import re
            # Remove verbose attributes like position/size coordinates
            cleaned_source = re.sub(r'(x|y|width|height|index)="[^"]+"', '', page_source)
            # Remove UIAApplication details which add noise
            cleaned_source = re.sub(r'UIAApplication[^>]+>', 'UIAApplication>', cleaned_source)
            dom = xml.dom.minidom.parseString(cleaned_source)
                
            formatted_source = dom.toprettyxml(indent='  ')
            return formatted_source
        except Exception as e:
            # If XML parsing fails, return original with basic line breaks
            return page_source

# Initialize global instances
device_manager = IOSDeviceManager()
mcp = FastMCP("appium-device-server")

@mcp.tool()
async def get_page_source(diff_only: bool = False, format_output: bool = True) -> str:
    """
    Get the current page source of the application.
    Output is always simplified by removing verbose attributes.
    
    Args:
        diff_only: If True, returns only the diff from the previous page source
        format_output: If True, formats the XML for better readability
    """
    if not device_manager.driver:
        return "No active Appium session"
    
    current_source, diff = device_manager.get_page_source_diff()
    
    if diff_only:
        return diff
    elif format_output:
        return device_manager.format_page_source(current_source)
    else:
        return current_source

@mcp.tool()
async def tap_element(element_id: str, by: LocatorStrategy = LocatorStrategy.ACCESSIBILITY_ID, return_diff: bool = True) -> str:
    """
    Tap an element by its identifier.
    
    Args:
        element_id: The identifier of the element to tap
        by: The locator strategy to use
        return_diff: If True, returns page source diff after tapping
    """
    if not device_manager.driver:
        return "No active Appium session"
    
    locator_map = {
        LocatorStrategy.ACCESSIBILITY_ID: AppiumBy.ACCESSIBILITY_ID,
        LocatorStrategy.XPATH: AppiumBy.XPATH,
        LocatorStrategy.NAME: AppiumBy.NAME,
        LocatorStrategy.CLASS_NAME: AppiumBy.CLASS_NAME
    }
    
    try:
        element = device_manager.driver.find_element(by=locator_map[by], value=element_id)
        element.click()
        
        # If we don't want the diff, just return success message
        if not return_diff:
            return f"Successfully tapped element with {by}: {element_id}"
            
        # Get page source diff after action
        _, diff = device_manager.get_page_source_diff()
        return f"Successfully tapped element with {by}: {element_id}\n\nPage Source Diff:\n{diff}"
    except Exception as e:
        return f"Failed to tap element: {str(e)}"

@mcp.tool()
async def press_physical_button(button: PhysicalButton, return_diff: bool = True) -> str:
    """
    Press a physical button on the iOS device.
    
    Args:
        button: The button to press
        return_diff: If True, returns page source diff after pressing
    """
    if not device_manager.driver:
        return "No active Appium session"
    
    try:
        device_manager.driver.execute_script('mobile: pressButton', {'name': button.value})
        
        # If we don't want the diff, just return success message
        if not return_diff:
            return f"Successfully pressed {button.name} button"
            
        # Get page source diff after action
        _, diff = device_manager.get_page_source_diff()
        return f"Successfully pressed {button.name} button\n\nPage Source Diff:\n{diff}"
    except Exception as e:
        return f"Failed to press button: {str(e)}"

@mcp.tool()
async def swipe(direction: SwipeDirection, return_diff: bool = True) -> str:
    """
    Perform a swipe gesture in the specified direction.
    
    Args:
        direction: The direction to swipe
        return_diff: If True, returns page source diff after swiping
    """
    if not device_manager.driver:
        return "No active Appium session"
    
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
        
        # If we don't want the diff, just return success message
        if not return_diff:
            return f"Successfully performed {direction.value} swipe"
            
        # Get page source diff after action
        _, diff = device_manager.get_page_source_diff()
        return f"Successfully performed {direction.value} swipe\n\nPage Source Diff:\n{diff}"
    except Exception as e:
        return f"Failed to perform swipe: {str(e)}"

@mcp.tool()
async def send_input(
    element_id: str, 
    text: str, 
    by: LocatorStrategy = LocatorStrategy.ACCESSIBILITY_ID,
    return_diff: bool = True
) -> str:
    """
    Send text input to an element by its identifier.
    
    Args:
        element_id: The identifier of the element
        text: The text to send
        by: The locator strategy to use
        return_diff: If True, returns page source diff after sending input
    """
    if not device_manager.driver:
        return "No active Appium session"
    
    locator_map = {
        LocatorStrategy.ACCESSIBILITY_ID: AppiumBy.ACCESSIBILITY_ID,
        LocatorStrategy.XPATH: AppiumBy.XPATH,
        LocatorStrategy.NAME: AppiumBy.NAME,
        LocatorStrategy.CLASS_NAME: AppiumBy.CLASS_NAME
    }
    
    try:
        element = device_manager.driver.find_element(by=locator_map[by], value=element_id)
        element.clear()
        element.send_keys(text)
        
        # If we don't want the diff, just return success message
        if not return_diff:
            return f"Successfully sent input '{text}' to element with {by}: {element_id}"
            
        # Get page source diff after action
        _, diff = device_manager.get_page_source_diff()
        return f"Successfully sent input '{text}' to element with {by}: {element_id}\n\nPage Source Diff:\n{diff}"
    except Exception as e:
        return f"Failed to send input: {str(e)}"

@mcp.tool()
async def navigate_to(url: str, return_diff: bool = True) -> str:
    """
    Navigate to a URL in Safari.
    
    Args:
        url: The URL to navigate to
        return_diff: If True, returns page source diff after navigation
    """
    if not device_manager.driver:
        return "No active Appium session"
    
    try:
        device_manager.driver.get(url)
        
        # If we don't want the diff, just return success message
        if not return_diff:
            return f"Successfully navigated to {url}"
            
        # Get page source diff after action
        _, diff = device_manager.get_page_source_diff()
        return f"Successfully navigated to {url}\n\nPage Source Diff:\n{diff}"
    except Exception as e:
        return f"Failed to navigate: {str(e)}"

@mcp.tool()
async def launch_app(bundle_id: str, return_diff: bool = True) -> str:
    """
    Launch an iOS app by its bundle ID.
    
    Args:
        bundle_id: The bundle ID of the app to launch
        return_diff: If True, returns page source diff after launching
    """
    try:
        if device_manager.driver:
            device_manager.driver.terminate_app(bundle_id)
            device_manager.driver.activate_app(bundle_id)
            
            if not return_diff:
                return f"Successfully launched app with bundle ID: {bundle_id}"
                
            # Get page source diff after action
            _, diff = device_manager.get_page_source_diff()
            return f"Successfully launched app with bundle ID: {bundle_id}\n\nPage Source Diff:\n{diff}"
        
        await device_manager.initialize_session(bundle_id)
        
        if not return_diff:
            return f"Successfully launched app with bundle ID: {bundle_id}"
        
        # No diff to return for initial launch, but get current page source
        current_source, _ = device_manager.get_page_source_diff()
        return f"Successfully launched app with bundle ID: {bundle_id}\n\nInitial Page Source (no diff available)"
    except Exception as e:
        return f"Failed to launch app: {str(e)}"

@mcp.tool()
async def take_screenshot() -> str:
    """Take a screenshot of the current app state."""
    if not device_manager.driver:
        return "No active Appium session"
    
    try:
        # Create screenshots directory if it doesn't exist
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshots_dir / f"screenshot_{timestamp}.png"
        
        # Take screenshot and save it
        device_manager.driver.get_screenshot_as_file(str(screenshot_path))
        return f"Screenshot saved successfully at: {screenshot_path}"
    except Exception as e:
        return f"Failed to take screenshot: {str(e)}"

if __name__ == "__main__":
    try:
        asyncio.run(device_manager.initialize_session())
        mcp.run(transport='sse')
    finally:
        asyncio.run(device_manager.cleanup()) 