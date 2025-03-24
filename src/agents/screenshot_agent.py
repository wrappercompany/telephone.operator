#!/usr/bin/env python3

from typing import Optional, List, Dict, Any
import asyncio
import logging
import traceback
from ..appium.tools import (
    get_page_source, tap_element, take_screenshot,
    swipe, SwipeDirection
)
from ..appium.driver import IOSDriver
from ..appium.context import AppState, AppiumContext, AppiumHooks
from ..config import Config, load_config
from agents import Agent, AgentHooks
from ..appium.tools import (
    press_physical_button,
    send_input,
    navigate_to,
    launch_app
)
from ..appium.driver import ios_driver
from ..ui.console import print_error, print_warning, print_success

logger = logging.getLogger(__name__)

class ScreenshotAgent:
    """Agent responsible for capturing screenshots and exploring the app."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.context = AppiumContext()
        self.hooks = AppiumHooks(self.context)
        logger.debug("ScreenshotAgent initialized")

    def start_session(self, app_name: str, bundle_id: str):
        """Start a new testing session for the given app."""
        try:
            logger.info(f"Starting session for {app_name} ({bundle_id})")
            
            if not app_name or not bundle_id:
                error_msg = "App name and bundle ID cannot be empty"
                logger.error(error_msg)
                print_error(error_msg)
                raise ValueError(error_msg)
            
            self.context.state = AppState(
                current_app=app_name,
                bundle_id=bundle_id,
                last_action="session_start",
                screenshot_count=0,
                coverage_score=0.0
            )
            
            logger.debug(f"Session state initialized: {self.context.state}")
            self.hooks.pre_run()
            logger.info("Session started successfully")
            print_success(f"Session started for {app_name}")
        except Exception as e:
            error_msg = f"Failed to start session: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            print_error(error_msg)
            # Re-raise to allow caller to handle
            raise

    def end_session(self):
        """End the current testing session."""
        try:
            logger.info("Ending session")
            self.hooks.post_run()
            self.context.state = None
            logger.info("Session ended successfully")
            print_success("Session ended")
        except Exception as e:
            error_msg = f"Error ending session: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            print_error(error_msg)

    async def capture_screen(self) -> Dict[str, Any]:
        """Capture the current screen state."""
        try:
            logger.info("Capturing screen")
            if not self.context.state:
                error_msg = "No active session"
                logger.error(error_msg)
                print_error(error_msg)
                raise RuntimeError(error_msg)

            screenshot_path = await take_screenshot()
            page_source = await get_page_source()
            
            # Update state with new screenshot count
            self.context.update_state(
                screenshot_count=self.context.state.screenshot_count + 1,
                last_action="capture_screen"
            )
            
            logger.info(f"Screen captured successfully. Total screenshots: {self.context.state.screenshot_count}")
            
            # Build and return result
            result = {
                "screenshot": screenshot_path,
                "page_source": page_source,
                "state": self.context.state.model_dump() if self.context.state else {}
            }
            
            logger.debug(f"Capture result: {result}")
            return result
        except Exception as e:
            error_msg = f"Error capturing screen: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            print_error(error_msg)
            # Return minimal result to avoid further errors
            return {
                "error": error_msg,
                "screenshot": None,
                "page_source": None,
                "state": self.context.state.model_dump() if self.context.state else {}
            }

screenshot_taker = Agent(
    name="screenshot_taker",
    instructions="""You are a specialized iOS screenshot capture assistant. Your mission is to systematically capture screenshots of every screen, state, and interaction in the app to create a comprehensive visual reference library.

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
    ],
    hooks=None
) 