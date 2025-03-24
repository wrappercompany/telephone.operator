from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

class AppiumConfig(BaseModel):
    """Appium server and device configuration."""
    host: str = "127.0.0.1"
    port: int = 4723
    platform_name: str = "iOS"
    device_name: str = "iPhone 16 Pro"
    platform_version: str = "18.2"
    automation_name: str = "XCUITest"

class AppConfig(BaseModel):
    """Target app configuration."""
    name: str
    bundle_id: str

class Config(BaseModel):
    """Global configuration."""
    appium: AppiumConfig = AppiumConfig()
    openai_api_key: Optional[str] = None
    max_iterations: int = 20
    max_agent_turns: int = 30
    test_artifacts_dir: str = "test_artifacts"

def load_config() -> Config:
    """Load configuration from environment variables and defaults."""
    load_dotenv()
    
    return Config(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        appium=AppiumConfig(
            host=os.getenv("APPIUM_HOST", "127.0.0.1"),
            port=int(os.getenv("APPIUM_PORT", "4723")),
            platform_name=os.getenv("IOS_PLATFORM_NAME", "iOS"),
            device_name=os.getenv("IOS_DEVICE_NAME", "iPhone 16 Pro"),
            platform_version=os.getenv("IOS_PLATFORM_VERSION", "18.2"),
            automation_name=os.getenv("IOS_AUTOMATION_NAME", "XCUITest")
        )
    ) 