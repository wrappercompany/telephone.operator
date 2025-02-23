#!/usr/bin/env python3

# /// script
# dependencies = [
#   "Appium-Python-Client>=3.1.0",
#   "fastmcp>=0.1.0",
#   "urllib3<2.0.0",
# ]
# ///

from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.appium_service import AppiumService
from appium.webdriver.common.appiumby import AppiumBy
import asyncio
import os
import logging
import datetime
import urllib3

# Suppress urllib3 connection warnings
urllib3.disable_warnings(urllib3.exceptions.NewConnectionError)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

# Configure logging
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_directory, f"app_{current_time}.log")

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Get our application logger
logger = logging.getLogger(__name__)

# Suppress uvicorn access logs and other noisy loggers
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
logging.getLogger("fastapi").setLevel(logging.ERROR)

# Initialize FastMCP server
mcp = FastMCP("appium-device-server")

# Global variables
driver = None
appium_service = None

async def initialize_appium_session():
    """Initialize the Appium session for iOS."""
    global driver, appium_service
    
    # Start Appium service with output to terminal
    appium_service = AppiumService()
    appium_service.start(
        args=[
            '--address', '127.0.0.1',
            '-p', '4723',
            '--log-level', 'info',  # Changed to info to see more details
            '--local-timezone',     # Use local timezone for timestamps
            '--debug-log-spacing'   # Better log formatting
        ],
        timeout_ms=20000
    )
    logger.info("Appium server started")
    
    # Configure simulator status bar
    try:
        import subprocess
        logger.info("Configuring simulator status bar...")
        subprocess.run([
            'xcrun', 'simctl', 'status_bar', 'iPhone 16 Pro', 'override',
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
        logger.info("Status bar configured successfully")
    except Exception as e:
        logger.warning(f"Failed to configure status bar: {str(e)}")
    
    # Default Appium server URL
    appium_url = "http://127.0.0.1:4723"
    
    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    options.device_name = "iPhone 16 Pro"   
    options.platform_version = "18.2"


    # Use Safari's bundle ID instead of an app path
    options.bundle_id = "com.apple.mobilesafari"
    logger.info("Initializing iOS Safari session...")

    try:
        driver = webdriver.Remote(appium_url, options=options)
        logger.info("iOS session initialized successfully")
        logger.debug(f"Device capabilities: {driver.capabilities}")  # Move capabilities to debug level
    except Exception as e:
        logger.error(f"Session initialization failed: {str(e)}")
        if appium_service:
            logger.info("Stopping Appium service")
            appium_service.stop()
        raise

@mcp.tool()
async def get_page_source() -> str:
    """Get the current page source of the application."""
    global driver
    if not driver:
        return "No active Appium session"
    return driver.page_source

@mcp.tool()
async def tap_element(element_id: str) -> str:
    """Tap an element by its ID/accessibility identifier."""
    global driver
    if not driver:
        return "No active Appium session"
    try:
        element = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value=element_id)
        element.click()
        return f"Successfully tapped element with ID: {element_id}"
    except Exception as e:
        return f"Failed to tap element: {str(e)}"

@mcp.tool()
async def press_physical_button(button: str) -> str:
    """Press a physical button on the iOS device.
    
    Args:
        button: The button to press. Valid values are:
            - "home"
            - "volumeup"
            - "volumedown"
            - "power"
    """
    global driver
    if not driver:
        return "No active Appium session"
    
    valid_buttons = {
        "home": "home",
        "volumeup": "volumeUp",
        "volumedown": "volumeDown",
        "power": "power"
    }
    
    try:
        if button.lower() not in valid_buttons:
            return f"Invalid button. Valid options are: {', '.join(valid_buttons.keys())}"
            
        driver.execute_script('mobile: pressButton', {'name': valid_buttons[button.lower()]})
        return f"Successfully pressed {button} button"
    except Exception as e:
        return f"Failed to press button: {str(e)}"

async def cleanup():
    """Cleanup resources before shutdown."""
    global driver, appium_service
    if driver:
        driver.quit()
    if appium_service:
        appium_service.stop()

if __name__ == "__main__":
    try:
        # Initialize Appium session before starting the server
        asyncio.run(initialize_appium_session())
        
        # Initialize and run the server with SSE transport
        mcp.run(transport='sse')
    finally:
        # Ensure cleanup runs
        asyncio.run(cleanup()) 