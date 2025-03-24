#!/usr/bin/env python3

# /// script
# dependencies = [
#   "openai-agents",
#   "pytest",
#   "pytest-asyncio",
#   "pytest-xdist",
#   "appium-python-client>=3.1.1",
#   "rich>=13.0.0,<14.0.0",
#   "python-dotenv>=1.0.0",
# ]
# ///

import asyncio
import os
from enum import Enum
from typing import Optional
from datetime import datetime
from pathlib import Path
from agents import Agent, Runner, function_tool
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.appium_service import AppiumService
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install
from dotenv import load_dotenv

# Install rich traceback handler
install(show_locals=True)

# Create rich console instance
console = Console()

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

@function_tool
async def get_page_source(*, diff_only: Optional[bool] = None, format_output: Optional[bool] = None) -> str:
    """
    Get the current page source of the application.
    
    Args:
        diff_only: If True, returns only the diff from the previous page source
        format_output: If True, formats the XML for better readability
    """
    if not ios_driver.driver:
        console.print("[red]No active Appium session[/red]")
        return "No active Appium session"
    
    try:
        page_source = ios_driver.driver.page_source
        if format_output:
            console.print(Panel(page_source, title="Page Source", border_style="blue"))
        return page_source
    except Exception as e:
        error_msg = f"Failed to get page source: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

@function_tool
async def tap_element(element_id: str, *, by: Optional[LocatorStrategy] = None) -> str:
    """
    Tap an element by its identifier.
    
    Args:
        element_id: The identifier of the element to tap
        by: The locator strategy to use
    """
    if not ios_driver.driver:
        console.print("[red]No active Appium session[/red]")
        return "No active Appium session"
    
    try:
        locator_map = {
            LocatorStrategy.ACCESSIBILITY_ID: AppiumBy.ACCESSIBILITY_ID,
            LocatorStrategy.XPATH: AppiumBy.XPATH,
            LocatorStrategy.NAME: AppiumBy.NAME,
            LocatorStrategy.CLASS_NAME: AppiumBy.CLASS_NAME
        }
        
        by_strategy = locator_map[by] if by else AppiumBy.ACCESSIBILITY_ID
        element = ios_driver.driver.find_element(by=by_strategy, value=element_id)
        element.click()
        success_msg = f"Successfully tapped element with {by_strategy}: {element_id}"
        console.print(f"[green]{success_msg}[/green]")
        return success_msg
    except Exception as e:
        error_msg = f"Failed to tap element: {str(e)}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

@function_tool
async def press_physical_button(button: PhysicalButton) -> str:
    """
    Press a physical button on the iOS device.
    
    Args:
        button: The button to press
    """
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        ios_driver.driver.execute_script('mobile: pressButton', {'name': button.value})
        return f"Successfully pressed {button.name} button"
    except Exception as e:
        return f"Failed to press button: {str(e)}"

@function_tool
async def swipe(direction: SwipeDirection) -> str:
    """
    Perform a swipe gesture in the specified direction.
    
    Args:
        direction: The direction to swipe
    """
    if not ios_driver.driver:
        return "No active Appium session"
    
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
        return f"Successfully performed {direction.value} swipe"
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
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
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
        return f"Successfully sent input '{text}' to element with {by_strategy}: {element_id}"
    except Exception as e:
        return f"Failed to send input: {str(e)}"

@function_tool
async def navigate_to(url: str) -> str:
    """
    Navigate to a URL in Safari.
    
    Args:
        url: The URL to navigate to
    """
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        ios_driver.driver.get(url)
        return f"Successfully navigated to {url}"
    except Exception as e:
        return f"Failed to navigate: {str(e)}"

@function_tool
async def launch_app(bundle_id: str) -> str:
    """
    Launch an iOS app by its bundle ID.
    
    Args:
        bundle_id: The bundle ID of the app to launch
    """
    try:
        if ios_driver.driver:
            ios_driver.driver.terminate_app(bundle_id)
            ios_driver.driver.activate_app(bundle_id)
            return f"Successfully launched app with bundle ID: {bundle_id}"
        
        await ios_driver.initialize(bundle_id)
        return f"Successfully launched app with bundle ID: {bundle_id}"
    except Exception as e:
        return f"Failed to launch app: {str(e)}"

@function_tool
async def take_screenshot() -> str:
    """Take a screenshot of the current app state."""
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshots_dir / f"screenshot_{timestamp}.png"
        
        ios_driver.driver.get_screenshot_as_file(str(screenshot_path))
        return f"Screenshot saved successfully at: {screenshot_path}"
    except Exception as e:
        return f"Failed to take screenshot: {str(e)}"

# Create the iOS testing agent with all available tools
ios_agent = Agent(
    name="iOS Testing Assistant",
    instructions="""You are a specialized iOS testing assistant that can help automate iOS app testing.
    You understand iOS automation and can help with device setup, navigation, and testing.
    You are configured to work with an iPhone 16 Pro running iOS 18.2.
    You can perform various actions like tapping elements, pressing buttons, swiping, and more.
    Before performing any actions, make sure to launch the appropriate app first.""",
    tools=[
        get_page_source,
        tap_element,
        press_physical_button,
        swipe,
        send_input,
        navigate_to,
        launch_app,
        take_screenshot
    ],
)

async def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]Error: OPENAI_API_KEY not found in environment variables or .env file[/red]")
        console.print("[yellow]Please create a .env file in the project root with your OpenAI API key:[/yellow]")
        console.print("OPENAI_API_KEY=your_api_key_here")
        return
    
    try:
        with console.status("[bold blue]Running iOS automation...[/bold blue]"):
            # Test the agent with a simple query
            result = await Runner.run(
                ios_agent, 
                input="Can you launch Safari and navigate to openai.com?"
            )
            console.print("\n[bold]Agent Response:[/bold]")
            console.print(Panel(result.final_output, border_style="green"))
    finally:
        # Clean up resources
        await ios_driver.cleanup()
        console.print("[yellow]Cleanup completed[/yellow]")

if __name__ == "__main__":
    asyncio.run(main()) 