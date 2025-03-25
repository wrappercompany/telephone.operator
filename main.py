#!/usr/bin/env python3

import asyncio
from src.manager import ScreenshotManager

async def main() -> None:
    # Configure target app
    target_app = {
        "name": "Settings",  # Human readable name
        "bundle_id": "com.apple.Preferences",  # Bundle ID for launching
        "description": "iOS Settings app that allows users to configure device settings, manage accounts, set up privacy options, and customize device behavior. It includes multiple sections like Wi-Fi, Bluetooth, Display, Sounds, and various app settings."
    }

    # Run the screenshot manager
    await ScreenshotManager().run(target_app)

if __name__ == "__main__":
    asyncio.run(main()) 