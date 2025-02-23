# Telephone Operator

An MCP server that provides iOS device automation capabilities through Appium, primarily focused on iOS 18.2 and iPhone 16 Pro.

## Features

- iOS Safari automation
- Device interaction controls
- Touch gesture simulation
- Physical button control
- Element interaction
- Built using MCP Python SDK and Appium

## Prerequisites

- Xcode with iOS 18.2 simulator
- Node.js and npm (for Appium)
- Appium Server
- Python 3.x

## Installation

1. Install UV if you haven't already:
```bash
# On MacOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Install Appium and required drivers:
```bash
npm install -g appium
appium driver install xcuitest
```

3. Create and set up the environment:
```bash
# Create project and virtual environment
uv init telephone-operator
cd telephone-operator
uv venv

# Activate virtual environment
# On MacOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

## Running the Server

Start the server using UV:
```bash
uv run server.py
```

## Available Tools

The server provides the following tools:

1. `get_page_source`: Get the current page source of Safari
   - Returns: Current page HTML source

2. `tap_element`: Tap an element on screen
   - Parameters:
     - `element_id`: Element identifier
     - `by`: Locator strategy (accessibility_id, xpath, name, class_name)

3. `press_physical_button`: Simulate physical button press
   - Parameters:
     - `button`: Button to press (home, volumeup, volumedown, power)

4. `swipe`: Perform swipe gestures
   - Parameters:
     - `direction`: Swipe direction (up, down, left, right)

5. `send_input`: Input text into elements
   - Parameters:
     - `element_id`: Target element identifier
     - `text`: Text to input
     - `by`: Locator strategy

6. `navigate_to`: Navigate Safari to URL
   - Parameters:
     - `url`: Target URL

## Configuration with Cursor

1. Open Cursor Settings
2. Go to Features > MCP
3. Click "+ Add New MCP Server"
4. Fill out the form:
   - Type: stdio
   - Name: telephone-operator
   - Command: `python3 /absolute/path/to/server.py`

## Configuration with Claude for Desktop

Add the following to your Claude for Desktop configuration:

```json
{
    "mcpServers": {
        "telephone-operator": {
            "command": "uv",
            "args": [
                "--directory",
                "/ABSOLUTE/PATH/TO/PARENT/FOLDER",
                "run",
                "server.py"
            ]
        }
    }
}
```

For Windows users, use Windows-style paths:
```json
{
    "mcpServers": {
        "telephone-operator": {
            "command": "uv",
            "args": [
                "--directory",
                "C:\\ABSOLUTE\\PATH\\TO\\PARENT\\FOLDER",
                "run",
                "server.py"
            ]
        }
    }
}
```

## Logging

The server maintains detailed logs in the `logs` directory, with timestamps for each session.

## Testing

You can test this server using:
1. The MCP Inspector tool
2. Cursor
3. Claude for Desktop
4. Any other MCP client

## Note

This server is configured to work with iPhone 16 Pro running iOS 18.2. Make sure you have the appropriate simulator installed through Xcode. 