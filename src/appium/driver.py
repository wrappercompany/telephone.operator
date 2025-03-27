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
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Add the parent directory to sys.path to allow importing from src
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.config import load_config

logger = logging.getLogger(__name__)

class IOSDriver:
    _instances = set()
    
    def __init__(self):
        self.driver = None
        self.config = load_config()
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
        appium_config = self.config.appium
        
        # Try to detect real device first
        self.device_info = self.detect_real_device()
        
        # Create Appium options object for newer Appium versions
        from appium.options.ios import XCUITestOptions
        options = XCUITestOptions()
        
        # Set required capabilities
        options.platform_name = appium_config.platform_name
        options.automation_name = appium_config.automation_name
        
        # Use detected device info if available, otherwise fall back to config
        if self.device_info:
            logger.info("Using detected real device configuration")
            options.device_name = self.device_info['name']
            options.platform_version = self.device_info['ios_version']
            options.udid = self.device_info['udid']
            
            # Add WebDriverAgent configuration for real devices
            if appium_config.team_id:
                options.set_capability("appium:xcodeOrgId", appium_config.team_id)
                options.set_capability("appium:xcodeSigningId", appium_config.signing_id)
            
            # Configure WDA settings
            options.set_capability("appium:wdaLocalPort", appium_config.wda_local_port)
            options.set_capability("appium:updatedWDABundleId", appium_config.wda_bundle_id)
            options.set_capability("appium:useNewWDA", False)
            options.set_capability("appium:usePrebuiltWDA", False)
            options.set_capability("appium:wdaStartupRetries", 4)
            options.set_capability("appium:wdaStartupRetryInterval", 20000)
            options.set_capability("appium:shouldUseSingletonTestManager", False)
            options.set_capability("appium:shouldTerminateApp", True)
            options.set_capability("appium:isRealMobile", True)
            
            # Set status bar time to 9:41
            options.set_capability("appium:statusBarTime", "9:41")
            options.set_capability("appium:forceStatusBarTime", True)
        else:
            logger.info("No real device detected, using simulator configuration")
            options.device_name = appium_config.device_name
            options.platform_version = appium_config.platform_version
        
        options.bundle_id = bundle_id
        
        # Construct Appium server URL
        server_url = f'http://{appium_config.host}:{appium_config.port}'
        
        try:
            logger.debug(f"Connecting to Appium server at {server_url}")
            logger.debug(f"Using options: {options.to_capabilities()}")
            
            # Create the driver with options
            self.driver = webdriver.Remote(command_executor=server_url, options=options)
            
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