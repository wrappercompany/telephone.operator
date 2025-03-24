#!/usr/bin/env python3

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.appium_service import AppiumService
import asyncio

class IOSDriver:
    def __init__(self):
        self.driver = None
        self.appium_service = None
        self.last_page_source = None
        
    async def initialize(self, bundle_id: str = "com.apple.mobilesafari"):
        """Initialize the iOS driver and Appium service"""
        # Start Appium service
        self.appium_service = AppiumService()
        self.appium_service.start(args=['--address', '127.0.0.1', '-p', '4723'])
        
        # Set up driver options
        options = XCUITestOptions()
        options.platform_name = "iOS"
        options.device_name = "iPhone 16 Pro"
        options.platform_version = "18.2"
        options.automation_name = "XCUITest"
        options.bundle_id = bundle_id
        
        # Initialize driver
        self.driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
        await asyncio.sleep(1)  # Brief pause for stability
        
    async def cleanup(self):
        """Clean up driver and service"""
        if self.driver:
            self.driver.quit()
        if self.appium_service:
            self.appium_service.stop()

# Create global driver instance
ios_driver = IOSDriver() 