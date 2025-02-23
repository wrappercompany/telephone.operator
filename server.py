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

    async def cleanup(self):
        """Cleanup resources."""
        if self.driver:
            self.driver.quit()
        if self.appium_service:
            self.appium_service.stop()

# Initialize global instances
device_manager = IOSDeviceManager()
mcp = FastMCP("appium-device-server")

@mcp.tool()
async def get_page_source() -> str:
    """Get the current page source of the application."""
    if not device_manager.driver:
        return "No active Appium session"
    return device_manager.driver.page_source

@mcp.tool()
async def tap_element(element_id: str, by: LocatorStrategy = LocatorStrategy.ACCESSIBILITY_ID) -> str:
    """Tap an element by its identifier."""
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
        return f"Successfully tapped element with {by}: {element_id}"
    except Exception as e:
        return f"Failed to tap element: {str(e)}"

@mcp.tool()
async def press_physical_button(button: PhysicalButton) -> str:
    """Press a physical button on the iOS device."""
    if not device_manager.driver:
        return "No active Appium session"
    
    try:
        device_manager.driver.execute_script('mobile: pressButton', {'name': button.value})
        return f"Successfully pressed {button.name} button"
    except Exception as e:
        return f"Failed to press button: {str(e)}"

@mcp.tool()
async def swipe(direction: SwipeDirection) -> str:
    """Perform a swipe gesture in the specified direction."""
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
        return f"Successfully performed {direction.value} swipe"
    except Exception as e:
        return f"Failed to perform swipe: {str(e)}"

@mcp.tool()
async def send_input(element_id: str, text: str, by: LocatorStrategy = LocatorStrategy.ACCESSIBILITY_ID) -> str:
    """Send text input to an element by its identifier."""
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
        return f"Successfully sent input '{text}' to element with {by}: {element_id}"
    except Exception as e:
        return f"Failed to send input: {str(e)}"

@mcp.tool()
async def navigate_to(url: str) -> str:
    """Navigate to a URL in Safari."""
    if not device_manager.driver:
        return "No active Appium session"
    
    try:
        device_manager.driver.get(url)
        return f"Successfully navigated to {url}"
    except Exception as e:
        return f"Failed to navigate: {str(e)}"

@mcp.tool()
async def launch_app(bundle_id: str) -> str:
    """Launch an iOS app by its bundle ID."""
    try:
        if device_manager.driver:
            device_manager.driver.terminate_app(bundle_id)
            device_manager.driver.activate_app(bundle_id)
            return f"Successfully launched app with bundle ID: {bundle_id}"
        
        await device_manager.initialize_session(bundle_id)
        return f"Successfully launched app with bundle ID: {bundle_id}"
    except Exception as e:
        return f"Failed to launch app: {str(e)}"

if __name__ == "__main__":
    try:
        asyncio.run(device_manager.initialize_session())
        mcp.run(transport='sse')
    finally:
        asyncio.run(device_manager.cleanup()) 