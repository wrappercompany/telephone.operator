from pydantic import BaseModel
from typing import Optional
from .driver import ios_driver

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

    def update_state(self, **kwargs):
        """Update the current app state."""
        if not self.state:
            self.state = AppState()
        self.state = self.state.model_copy(update=kwargs)

class AppiumHooks:
    """Handles Appium session lifecycle."""
    def __init__(self, context: AppiumContext):
        self.context = context

    def pre_run(self):
        """Initialize the Appium session."""
        if not ios_driver.driver and self.context.state:
            ios_driver.init_driver(self.context.state.bundle_id)

    def post_run(self):
        """Clean up the Appium session."""
        if ios_driver.driver:
            ios_driver.cleanup() 