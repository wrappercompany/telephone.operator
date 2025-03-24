#!/usr/bin/env python3

import atexit
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging
import weakref
import traceback

logger = logging.getLogger(__name__)

class IOSDriver:
    _instances = set()
    
    def __init__(self):
        self.driver = None
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
    
    def init_driver(self, bundle_id: str):
        """Initialize the Appium driver with the given bundle ID."""
        if not bundle_id:
            logger.error("Cannot initialize driver: Empty bundle ID")
            return False
            
        if self.driver:
            logger.info("Driver already exists, cleaning up before re-initialization")
            self.cleanup()
            
        logger.info(f"Initializing iOS driver for bundle ID: {bundle_id}")
        caps = {
            'platformName': 'iOS',
            'automationName': 'XCUITest',
            'deviceName': 'iPhone 15',
            'bundleId': bundle_id,
        }
        
        try:
            logger.debug(f"Connecting to Appium with capabilities: {caps}")
            self.driver = webdriver.Remote('http://localhost:4723', caps)
            logger.info("Successfully initialized iOS driver")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize iOS driver: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return False

    def cleanup(self):
        """Clean up the driver instance."""
        if hasattr(self, 'driver') and self.driver:
            logger.info("Cleaning up driver instance")
            try:
                self.driver.quit()
                logger.info("Driver quit successfully")
            except Exception as e:
                logger.warning(f"Error during driver quit: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
            finally:
                self.driver = None
        else:
            logger.debug("No driver to clean up")

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