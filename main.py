#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv
import openai

from src.manager import ScreenshotManager
from src.ui.console import print_missing_api_key_instructions

async def main() -> None:
    # Load environment variables
    load_dotenv()
    
    # Check for OpenAI API key
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        print_missing_api_key_instructions()
        return

    # Configure target app
    target_app = {
        "name": "Messages",  # Human readable name
        "bundle_id": "com.apple.MobileSMS"  # Bundle ID for launching
    }

    # Run the screenshot manager
    await ScreenshotManager().run(target_app)

if __name__ == "__main__":
    asyncio.run(main()) 