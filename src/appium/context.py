from pydantic import BaseModel
from agents import AgentHooks
from .driver import IOSDriver

class AppState(BaseModel):
    """State of the current app being tested."""
    current_app: str = ""
    bundle_id: str = ""
    last_action: str = ""
    screenshot_count: int = 0
    coverage_score: float = 0.0

class AppiumContext:
    """Context for managing Appium session state."""
    def __init__(self, driver: IOSDriver):
        self.driver = driver
        self.state = AppState()

    async def update_state(self, **kwargs):
        """Update the current app state."""
        self.state = self.state.model_copy(update=kwargs)

class AppiumHooks(AgentHooks):
    """Hooks for managing Appium session lifecycle."""
    async def before_run(self, context: AppiumContext):
        """Initialize Appium session before agent run."""
        await context.driver.initialize()
    
    async def after_run(self, context: AppiumContext):
        """Clean up Appium session after agent run."""
        await context.driver.cleanup() 