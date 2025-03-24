from pydantic import BaseModel, Field, validator
from typing import Optional
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class AppiumConfig(BaseModel):
    """Appium server and device configuration."""
    host: str = Field("127.0.0.1", description="Appium server host")
    port: int = Field(4723, description="Appium server port")
    platform_name: str = Field("iOS", description="Target platform")
    device_name: str = Field("iPhone 16 Pro", description="Target device name")
    platform_version: str = Field("18.2", description="Platform version")
    automation_name: str = Field("XCUITest", description="Automation framework")
    
    @validator('port')
    def port_must_be_valid(cls, v):
        if not (1024 <= v <= 65535):
            logger.warning(f"Invalid port number: {v}, using default 4723")
            return 4723
        return v

class AppConfig(BaseModel):
    """Target app configuration."""
    name: str = Field(..., description="App name for display")
    bundle_id: str = Field(..., description="App bundle ID for launching")
    
    @validator('bundle_id')
    def bundle_id_must_be_valid(cls, v):
        if not v or not isinstance(v, str):
            logger.error("Bundle ID cannot be empty")
            raise ValueError("Bundle ID cannot be empty")
        return v

class Config(BaseModel):
    """Global configuration."""
    appium: AppiumConfig = Field(default_factory=AppiumConfig, description="Appium configuration")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    max_iterations: int = Field(20, description="Maximum iterations for screenshot capture")
    max_agent_turns: int = Field(30, description="Maximum turns per agent run")
    test_artifacts_dir: str = Field("test_artifacts", description="Directory for test artifacts")
    
    @validator('max_iterations', 'max_agent_turns')
    def positive_int(cls, v, values, field):
        if v <= 0:
            logger.warning(f"{field.name} must be positive, using default")
            return 20 if field.name == 'max_iterations' else 30
        return v
        
    @validator('test_artifacts_dir')
    def valid_directory(cls, v):
        if not v:
            logger.warning("Empty test_artifacts_dir, using default")
            return "test_artifacts"
        # Ensure directory exists
        try:
            os.makedirs(v, exist_ok=True)
            logger.info(f"Ensured test artifacts directory exists: {v}")
        except Exception as e:
            logger.error(f"Failed to create test artifacts directory {v}: {str(e)}")
        return v

def load_config() -> Config:
    """Load configuration from environment variables and defaults."""
    try:
        logger.info("Loading configuration")
        load_dotenv()
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("OpenAI API key not found in environment")
        
        config = Config(
            openai_api_key=openai_key,
            appium=AppiumConfig(
                host=os.getenv("APPIUM_HOST", "127.0.0.1"),
                port=int(os.getenv("APPIUM_PORT", "4723")),
                platform_name=os.getenv("IOS_PLATFORM_NAME", "iOS"),
                device_name=os.getenv("IOS_DEVICE_NAME", "iPhone 16 Pro"),
                platform_version=os.getenv("IOS_PLATFORM_VERSION", "18.2"),
                automation_name=os.getenv("IOS_AUTOMATION_NAME", "XCUITest")
            )
        )
        
        logger.info(f"Configuration loaded successfully: {config.dict(exclude={'openai_api_key'})}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        # Return default config as fallback
        logger.info("Using default configuration")
        return Config() 