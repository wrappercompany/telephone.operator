#!/usr/bin/env python3

import asyncio
import argparse
from src.manager import ScreenshotManager

async def main() -> None:
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="iOS Screenshot Agent")
    parser.add_argument("--chat", action="store_true", help="Start in chat mode for direct interaction with the screenshot agent")
    args = parser.parse_args()
    
    # Configure target app
    target_app = {
        "name": "Messages",  # Human readable name
        "bundle_id": "com.apple.MobileSMS"  # Bundle ID for launching
    }

    # Create the screenshot manager
    manager = ScreenshotManager()
    
    # Run in the selected mode
    if args.chat:
        # Chat mode - direct interaction with the screenshot agent
        await manager.chat_with_screenshot_agent(target_app)
    else:
        # Normal automated screenshot capture mode
        await manager.run(target_app)

if __name__ == "__main__":
    asyncio.run(main()) 