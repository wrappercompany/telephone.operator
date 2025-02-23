#!/usr/bin/env python3

# /// script
# dependencies = [
#   "@modelcontextprotocol/inspector",
# ]
# ///

import subprocess
import sys

def main():
    # Run the MCP Inspector with UV
    subprocess.run([
        "npx",
        "@modelcontextprotocol/inspector",
        "uv",
        "--directory", ".",
        "run"
    ], check=True)

if __name__ == "__main__":
    main() 