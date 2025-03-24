#!/usr/bin/env python3

from agents import Agent, AgentHooks
from ..appium.tools import (
    get_page_source,
    tap_element,
    press_physical_button,
    swipe,
    send_input,
    navigate_to,
    launch_app,
    take_screenshot
)
from ..appium.driver import IOSDriver
from pydantic import BaseModel

class AppState(BaseModel):
    current_app: str = ""
    bundle_id: str = ""
    last_action: str = ""
    screenshot_count: int = 0
    coverage_score: float = 0.0

class AppiumContext:
    def __init__(self, driver: IOSDriver):
        self.driver = driver
        self.state = AppState()

    async def update_state(self, **kwargs):
        self.state = self.state.model_copy(update=kwargs)

class AppiumHooks(AgentHooks):
    async def before_run(self, context: AppiumContext):
        # Pre-run setup
        await context.driver.initialize()
    
    async def after_run(self, context: AppiumContext):
        # Cleanup
        await context.driver.cleanup()

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
    hooks=AppiumHooks()
) 