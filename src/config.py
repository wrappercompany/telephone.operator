from pydantic import BaseModel, Field, field_validator
from typing import Optional
import os
import logging
from dotenv import load_dotenv
from pydantic_core.core_schema import FieldValidationInfo

logger = logging.getLogger(__name__)

class AppiumConfig(BaseModel):
    """Appium server and device configuration."""
    host: str = Field("127.0.0.1", description="Appium server host")
    port: int = Field(4723, description="Appium server port")
    platform_name: str = Field("iOS", description="Target platform")
    device_name: str = Field("iPhone 16 Pro", description="Target device name")
    platform_version: str = Field("18.2", description="Platform version")
    automation_name: str = Field("XCUITest", description="Automation framework")
    udid: Optional[str] = Field(None, description="Real device UDID")
    team_id: Optional[str] = Field(None, description="Apple Developer Team ID")
    signing_id: Optional[str] = Field("iPhone Developer", description="Code signing identity")
    wda_local_port: Optional[int] = Field(8100, description="WebDriverAgent local port")
    wda_bundle_id: Optional[str] = Field("com.facebook.WebDriverAgentRunner.xctrunner", description="WebDriverAgent bundle ID")
    
    @field_validator('port', 'wda_local_port')
    def port_must_be_valid(cls, v, info: FieldValidationInfo):
        if not (1024 <= v <= 65535):
            field_name = info.field_name
            default = 4723 if field_name == 'port' else 8100
            logger.warning(f"Invalid {field_name}: {v}, using default {default}")
            return default
        return v

    @field_validator('udid')
    def validate_udid(cls, v):
        if v and not isinstance(v, str):
            logger.warning("Invalid UDID format, must be string")
            return None
        return v

    @field_validator('team_id')
    def validate_team_id(cls, v):
        if v and not isinstance(v, str):
            logger.warning("Invalid Team ID format, must be string")
            return None
        return v

class AppConfig(BaseModel):
    """Target app configuration."""
    name: str = Field(..., description="App name for display")
    bundle_id: str = Field(..., description="App bundle ID for launching")
    
    @field_validator('bundle_id')
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
    artifacts_dir: str = Field("artifacts", description="Directory for test artifacts")
    
    @field_validator('max_iterations', 'max_agent_turns')
    def positive_int(cls, v, info: FieldValidationInfo):
        field_name = info.field_name
        if v <= 0:
            logger.warning(f"{field_name} must be positive, using default")
            return 20 if field_name == 'max_iterations' else 30
        return v
        
    @field_validator('artifacts_dir')
    def valid_directory(cls, v):
        if not v:
            logger.warning("Empty artifacts_dir, using default")
            return "artifacts"
        # Ensure directory exists
        try:
            os.makedirs(v, exist_ok=True)
            logger.info(f"Ensured artifacts directory exists: {v}")
        except Exception as e:
            logger.error(f"Failed to create artifacts directory {v}: {str(e)}")
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
                automation_name=os.getenv("IOS_AUTOMATION_NAME", "XCUITest"),
                udid=os.getenv("IOS_DEVICE_UDID"),
                team_id=os.getenv("IOS_TEAM_ID"),
                signing_id=os.getenv("IOS_SIGNING_ID", "iPhone Developer"),
                wda_local_port=int(os.getenv("WDA_LOCAL_PORT", "8100")),
                wda_bundle_id=os.getenv("WDA_BUNDLE_ID", "com.facebook.WebDriverAgentRunner.xctrunner")
            )
        )
        
        logger.info(f"Configuration loaded successfully: {config.model_dump(exclude={'openai_api_key'})}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        # Return default config as fallback
        logger.info("Using default configuration")
        return Config() 