#!/usr/bin/env python3

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional

from ..config import AppiumConfig

class IOSDriver:
    def __init__(self, config: Optional[AppiumConfig] = None):
        self.config = config or AppiumConfig()
        self.driver = None

    def init_driver(self, app_bundle_id: str):
        """Initialize the Appium driver with the given configuration."""
        if self.driver:
            return

        options = XCUITestOptions()
        options.platform_name = self.config.platform_name
        options.platform_version = self.config.platform_version
        options.device_name = self.config.device_name
        options.automation_name = self.config.automation_name
        options.bundle_id = app_bundle_id

        self.driver = webdriver.Remote(
            command_executor=f'http://{self.config.host}:{self.config.port}',
            options=options
        )

    def cleanup(self):
        """Clean up driver resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        self.cleanup()

# Global driver instance
ios_driver = IOSDriver() 