#!/usr/bin/env python3

import asyncio
from src.manager import ScreenshotManager

async def main() -> None:
    # Configure target app
    target_app = {
        "name": "Messages",  # Human readable name
        "bundle_id": "com.apple.MobileSMS"  # Bundle ID for launching
    }

    # Run the screenshot manager
    await ScreenshotManager().run(target_app)

if __name__ == "__main__":
    asyncio.run(main()) 