#!/usr/bin/env python3

import pytest
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow importing from src
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Load environment variables from .env file
load_dotenv()

# Register marks for pytest
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio coroutine")
    config.addinivalue_line("markers", "appium: mark test as requiring appium server")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    
# Skip appium tests if the server is not available
def pytest_runtest_setup(item):
    """Skip tests marked with 'appium' if Appium server is not available."""
    if "appium" in item.keywords:
        # Check if Appium tests should be skipped
        if os.environ.get("SKIP_APPIUM_TESTS", "").lower() in ("true", "1", "yes"):
            pytest.skip("Appium tests skipped via SKIP_APPIUM_TESTS environment variable") 