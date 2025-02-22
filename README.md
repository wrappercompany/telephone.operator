# Calculator MCP Server

A simple MCP server that provides calculator functionality and a sample resource.

## Features

- Calculator tools for basic arithmetic operations
- Sample resource demonstration
- Built using MCP Python SDK

## Installation

1. Install UV if you haven't already:
```bash
# On MacOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Create and set up the environment:
```bash
# Create project and virtual environment
uv init calculator-server
cd calculator-server
uv venv

# Activate virtual environment
# On MacOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
uv add "mcp[cli]"
```

## Running the Server

Run the server using UV:
```bash
uv run server.py
```

## Available Tools

The server provides the following tools:

1. `add`: Add two numbers together
   - Parameters:
     - `a`: First number (float)
     - `b`: Second number (float)

2. `multiply`: Multiply two numbers together
   - Parameters:
     - `a`: First number (float)
     - `b`: Second number (float)

## Available Resources

- `sample_resource`: A simple text resource for demonstration purposes

## Testing

You can test this server using:
1. The MCP Inspector tool
2. Cursor
3. Claude for Desktop
4. Any other MCP client

## Configuration with Cursor

1. Open Cursor Settings
2. Go to Features > MCP
3. Click "+ Add New MCP Server"
4. Fill out the form:
   - Type: stdio
   - Name: calculator
   - Command: `python3 /absolute/path/to/server.py`

After adding the server, you may need to click the refresh button in the top right corner of the MCP server to populate the tool list.

## Configuration with Claude for Desktop

Add the following to your Claude for Desktop configuration file:

```json
{
    "mcpServers": {
        "calculator": {
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

Replace `/ABSOLUTE/PATH/TO/PARENT/FOLDER` with the absolute path to the directory containing your server.py file.

For Windows users, use Windows-style paths:
```json
{
    "mcpServers": {
        "calculator": {
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