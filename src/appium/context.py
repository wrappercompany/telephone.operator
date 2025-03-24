from pydantic import BaseModel
from typing import Optional
import logging
from .driver import ios_driver

# Configure logger
logger = logging.getLogger(__name__)

class AppState(BaseModel):
    """State of the current app being tested."""
    current_app: str = ""
    bundle_id: str = ""
    last_action: str = ""
    screenshot_count: int = 0
    coverage_score: float = 0.0

class AppiumContext:
    """Manages the Appium session state."""
    def __init__(self):
        self.driver = ios_driver
        self.state: Optional[AppState] = None
        logger.debug("AppiumContext initialized")

    def update_state(self, **kwargs):
        """Update the current app state."""
        try:
            logger.debug(f"Updating state with: {kwargs}")
            if not self.state:
                logger.info("Creating new AppState")
                self.state = AppState()
            # Update for Pydantic v2 compatibility
            self.state = AppState.model_validate(self.state.model_dump() | kwargs)
            logger.debug(f"State updated: {self.state}")
        except Exception as e:
            logger.error(f"Error updating state: {str(e)}")
            # Ensure we always have a valid state
            if not self.state:
                self.state = AppState()

class AppiumHooks:
    """Handles Appium session lifecycle."""
    def __init__(self, context: AppiumContext):
        self.context = context
        logger.debug("AppiumHooks initialized")

    def pre_run(self):
        """Initialize the Appium session."""
        try:
            logger.info("Starting pre-run hook")
            if not ios_driver.driver and self.context.state:
                logger.info(f"Initializing driver for bundle ID: {self.context.state.bundle_id}")
                ios_driver.init_driver(self.context.state.bundle_id)
            else:
                logger.debug("Driver already initialized or no state available")
        except Exception as e:
            logger.error(f"Error in pre_run: {str(e)}")

    def post_run(self):
        """Clean up the Appium session."""
        logger.info("Running post-run hook")
        if ios_driver.driver:
            logger.info("Cleaning up driver")
            ios_driver.cleanup() 