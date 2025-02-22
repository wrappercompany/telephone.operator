#!/bin/bash

# Check if Appium is installed
if ! command -v appium &> /dev/null; then
    echo "Error: Appium is not installed. Please run setup.sh first."
    exit 1
fi

echo "Starting Appium server..."

# Default port for Appium
PORT=4723

# Check if the port is already in use
if lsof -i :$PORT > /dev/null; then
    echo "Warning: Port $PORT is already in use. Attempting to kill existing process..."
    lsof -ti :$PORT | xargs kill -9
    sleep 2
fi

# Clear the terminal to make logs more readable
clear

# Start Appium server with basic configuration in foreground mode
echo "Starting Appium server on port $PORT..."
echo "Logs will appear below. Press Ctrl+C to stop the server."
echo "----------------------------------------"

exec appium \
    --allow-insecure chromedriver_autodownload \
    --base-path / \
    --relaxed-security \
    --log-timestamp \
    --local-timezone \
    --no-perms-check 