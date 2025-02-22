#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any

# Initialize FastMCP server
mcp = FastMCP("calculator-server")

# Constants
SAMPLE_DATA = "This is a sample resource content."

@mcp.tool()
async def add(a: float, b: float) -> str:
    """Add two numbers together.
    
    Args:
        a: First number to add
        b: Second number to add
    """
    result = a + b
    return f"The sum of {a} and {b} is {result}"

@mcp.tool()
async def multiply(a: float, b: float) -> str:
    """Multiply two numbers together.
    
    Args:
        a: First number to multiply
        b: Second number to multiply
    """
    result = a * b
    return f"The product of {a} and {b} is {result}"

@mcp.resource("example://sample")
async def sample_resource() -> str:
    """A simple sample resource."""
    return SAMPLE_DATA

if __name__ == "__main__":
    # Initialize and run the server with SSE transport
    mcp.run(transport='sse') 