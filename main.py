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
#   "requests>=2.31.0",
# ]
# ///

import asyncio
import os
import requests
import subprocess
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, Tuple, Literal
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from agents import Agent, Runner, function_tool, ItemHelpers, TResponseInputItem, trace
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.appium_service import AppiumService
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install
from rich.table import Table
from rich.live import Live
from dotenv import load_dotenv

# Install rich traceback handler
install(show_locals=True)

# Configure logging
log_file = "telephone_operator.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),  # 'w' mode overwrites the file on each run
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

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

class ToolCallLogger:
    def __init__(self):
        self.tool_calls = []
        self.console = Console()
        self.live = None
        
    def log_tool_call(self, tool_name: str, args: Dict[str, Any]):
        self.tool_calls.append({
            "tool": tool_name,
            "args": args,
            "timestamp": datetime.now()
        })
        self._display_tool_calls()
    
    def _display_tool_calls(self):
        table = Table(title="Tool Calls History")
        table.add_column("Time", style="cyan")
        table.add_column("Tool", style="green")
        table.add_column("Arguments", style="yellow")
        
        for call in self.tool_calls:
            time_str = call["timestamp"].strftime("%H:%M:%S")
            args_str = ", ".join(f"{k}={v}" for k, v in call["args"].items())
            table.add_row(time_str, call["tool"], args_str)
        
        if self.live:
            self.live.update(table)
        else:
            self.console.print(table)

    def start_live_display(self):
        self.live = Live(auto_refresh=False)
        self.live.start()

    def stop_live_display(self):
        if self.live:
            self.live.stop()
            self.live = None

# Create global instances
tool_logger = ToolCallLogger()

# Wrap each tool function to add logging
def wrap_tool_with_logging(tool):
    original_on_invoke = tool.on_invoke_tool
    
    async def logged_invoke(*args, **kwargs):
        tool_logger.log_tool_call(tool.name, kwargs)
        return await original_on_invoke(*args, **kwargs)
    
    tool.on_invoke_tool = logged_invoke
    return tool

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
    Only taps elements that are visible on screen.
    
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
        
        # Check if element is visible
        if not element.is_displayed():
            error_msg = f"Element with {by_strategy}: {element_id} is not visible"
            console.print(f"[yellow]{error_msg}[/yellow]")
            return error_msg
            
        element.click()
        success_msg = f"Successfully tapped visible element with {by_strategy}: {element_id}"
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
    """Take a screenshot and save page source of the current app state."""
    if not ios_driver.driver:
        return "No active Appium session"
    
    try:
        # Get current app bundle ID or use "unknown_app" as fallback
        try:
            current_app = ios_driver.driver.current_package or "unknown_app"
            # Clean up bundle ID to make it filesystem friendly
            app_dir_name = current_app.split('.')[-1].lower()
        except:
            app_dir_name = "unknown_app"
        
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
        ios_driver.driver.get_screenshot_as_file(str(screenshot_path))
        
        # Get and save page source
        page_source = ios_driver.driver.page_source
        pagesource_path.write_text(page_source, encoding='utf-8')
        
        return f"Artifacts saved successfully:\nApp: {current_app}\nScreenshot: {screenshot_path}\nPage Source: {pagesource_path}"
    except Exception as e:
        return f"Failed to capture artifacts: {str(e)}"

@dataclass
class CoverageEvaluation:
    feedback: str
    score: Literal["complete", "needs_more", "insufficient"]
    missing_areas: list[str]

screenshot_taker = Agent(
    name="screenshot_taker",
    instructions=f"""You are a specialized iOS screenshot capture assistant. Your mission is to systematically capture screenshots of every screen, state, and interaction in the app to create a comprehensive visual reference library.

Key Responsibilities:
1. Complete Coverage
   - Start from app launch and methodically explore EVERY screen
   - Screenshot ALL unique screens and states
   - Continue until ALL main aspects of the app are captured

2. Required Screenshots
   - Main Screens: Every unique screen in the app
   - States: Default, active, empty, loading, error states
   - Flows: Each step in multi-step processes
   - Modals: Popups, alerts, overlays
   - System UI: Permission prompts, system dialogs

3. Screenshot Quality
   - Well-framed and complete
   - Free of temporary elements
   - Captured after animations complete
   - In correct device orientation

Remember: Be thorough and systematic in your exploration. After each set of actions, describe what you've captured and what you plan to explore next.""",
    tools=[
        get_page_source,
        tap_element,
        press_physical_button,
        swipe,
        send_input,
        navigate_to,
        launch_app,
        take_screenshot
    ]
)

coverage_evaluator = Agent[None](
    name="coverage_evaluator",
    instructions="""You are an expert iOS app coverage evaluator. Your job is to analyze the current screenshot coverage and provide specific, actionable feedback.

When evaluating, consider:
1. Have ALL main screens been captured?
2. Are there missing states (empty, loading, error)?
3. Are there uncaptured modals or system prompts?
4. Are all key user flows represented?

Evaluation Rules:
1. Never mark as complete on the first evaluation
2. Provide specific, actionable feedback about missing areas
3. Consider both breadth (all screens) and depth (all states)
4. Track progress across evaluations
5. Only mark as complete when you have strong evidence of thorough coverage

Your feedback should be:
1. Specific - Name exact screens or states missing
2. Actionable - Give clear next steps
3. Prioritized - Focus on most important missing areas first""",
    output_type=CoverageEvaluation
)

async def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        error_msg = "Error: OPENAI_API_KEY not found in environment variables or .env file"
        logger.error(error_msg)
        console.print(f"[red]{error_msg}[/red]")
        console.print("[yellow]Please create a .env file in the project root with your OpenAI API key:[/yellow]")
        console.print("OPENAI_API_KEY=your_api_key_here")
        return

    # Check and start Appium server if needed
    server_running, status_message = check_appium_server()
    if not server_running:
        logger.warning("Appium server is not running. Attempting to start it...")
        console.print("[yellow]Appium server is not running. Attempting to start it...[/yellow]")
        server_started, start_message = start_appium_server()
        if not server_started:
            logger.error(f"Failed to start Appium server: {start_message}")
            console.print(f"[red]Error: {start_message}[/red]")
            return
        logger.info(f"Appium server started: {start_message}")
        console.print(f"[green]{start_message}[/green]")
    else:
        logger.info(f"Appium server status: {status_message}")
        console.print(f"[green]{status_message}[/green]")
    
    try:
        # Create agent with target app configuration
        target_app = {
            "name": "Messages",  # Human readable name
            "bundle_id": "com.apple.MobileSMS"  # Bundle ID for launching
        }
        logger.info(f"Starting test session for app: {target_app['name']} ({target_app['bundle_id']})")

        input_items: list[TResponseInputItem] = [{
            "content": f"Please launch {target_app['name']} and start capturing screenshots systematically.",
            "role": "user"
        }]

        latest_screenshots: list[str] = []
        iteration_count = 0
        max_iterations = 20  # Increased from 10 to 20
        
        # Start tool logging
        tool_logger.start_live_display()
        logger.info("Started tool logging display")

        # Main workflow trace
        with trace("Screenshot Coverage Evaluation"):
            while iteration_count < max_iterations:
                iteration_count += 1
                logger.info(f"Starting iteration {iteration_count}/{max_iterations}")
                
                # Clear screen for new iteration
                console.clear()
                
                # Show iteration progress
                console.print(f"\nIteration {iteration_count}/{max_iterations}")
                
                # Run screenshot taker
                console.print("\nScreenshot Taker: Capturing screenshots...")
                logger.info("Running screenshot capture sequence")
                screenshot_result = await Runner.run(
                    screenshot_taker,
                    input_items,
                    max_turns=30  # Increased max turns for screenshot taker
                )

                input_items = screenshot_result.to_input_list()
                latest_action = ItemHelpers.text_message_outputs(screenshot_result.new_items)
                logger.info(f"Screenshot action completed: {latest_action[:200]}...")  # Log first 200 chars
                
                # Show screenshot results
                console.print("\nScreenshot Results:")
                console.print(Panel(latest_action, border_style="blue"))

                # Run coverage evaluator
                console.print("\nEvaluator: Analyzing coverage...")
                logger.info("Running coverage evaluation")
                evaluator_result = await Runner.run(
                    coverage_evaluator,
                    input_items,
                    max_turns=20  # Increased max turns for evaluator
                )
                result: CoverageEvaluation = evaluator_result.final_output
                logger.info(f"Coverage evaluation completed - Score: {result.score}")

                # Show evaluation results
                console.print("\nCoverage Analysis:")
                console.print(Panel(
                    f"Score: {result.score}\n\nFeedback:\n{result.feedback}\n\nMissing Areas:\n" + "\n".join([f"- {area}" for area in result.missing_areas]),
                    border_style="yellow",
                    title="Coverage Analysis"
                ))

                if result.score == "complete":
                    logger.info("Screenshot coverage is complete")
                    console.print("\nScreenshot coverage is complete.")
                    break

                if iteration_count == max_iterations:
                    logger.warning("Maximum iterations reached without complete coverage")
                    console.print("\nMaximum iterations reached. Please review coverage and run again if needed.")
                    break

                # Add feedback for next iteration
                input_items.append({
                    "content": f"Coverage Feedback: {result.feedback}\nPlease capture screenshots of: {', '.join(result.missing_areas)}",
                    "role": "user"
                })
                logger.info(f"Added feedback for next iteration. Missing areas: {', '.join(result.missing_areas)}")
                
                # Brief pause to show results
                await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"An error occurred during execution: {str(e)}", exc_info=True)
        raise
    finally:
        # Clean up resources
        tool_logger.stop_live_display()
        await ios_driver.cleanup()
        logger.info("Cleanup completed")
        console.print("[yellow]Cleanup completed[/yellow]")

def start_appium_server() -> Tuple[bool, str]:
    """Start the Appium server if it's not running."""
    try:
        # First check if it's already running
        if check_appium_server()[0]:
            return True, "Appium server is already running"
        
        # Start Appium server in the background
        console.print("[yellow]Starting Appium server...[/yellow]")
        subprocess.Popen(
            ["appium", "--address", "127.0.0.1", "--port", "4723"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for server to start (max 10 seconds)
        for _ in range(10):
            if check_appium_server()[0]:
                return True, "Successfully started Appium server"
            time.sleep(1)
            
        return False, "Failed to start Appium server after 10 seconds"
    except FileNotFoundError:
        return False, "Appium is not installed. Please install it with: npm install -g appium"
    except Exception as e:
        return False, f"Error starting Appium server: {str(e)}"

def check_appium_server() -> Tuple[bool, str]:
    """Check if Appium server is running and accessible."""
    try:
        response = requests.get('http://127.0.0.1:4723/status', timeout=2)
        if response.status_code == 200:
            return True, "Appium server is running"
        return False, f"Appium server returned status code: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Appium server is not running"
    except requests.exceptions.Timeout:
        return False, "Appium server connection timed out"
    except Exception as e:
        return False, f"Error checking Appium server: {str(e)}"

if __name__ == "__main__":
    asyncio.run(main()) 