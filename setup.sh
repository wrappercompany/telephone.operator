#!/bin/bash

echo "Starting Appium Setup..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js not found. Installing Node.js..."
    # For macOS, using Homebrew
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew install node
else
    echo "Node.js is already installed"
fi

# Install Appium globally
echo "Installing Appium..."
npm install -g appium

# Install Appium Doctor for system checks
echo "Installing Appium Doctor..."
npm install -g appium-doctor

# Install Appium Drivers
echo "Installing Appium Drivers..."
appium driver install xcuitest  # for iOS
appium driver install uiautomator2  # for Android

# Check system requirements
echo "Checking system requirements with Appium Doctor..."
appium-doctor

echo "Creating Appium configuration directory..."
mkdir -p ~/.appium

echo "Setup complete! You can now start Appium by running: 'appium'"
echo "Note: For iOS testing, make sure Xcode and Command Line Tools are installed"
echo "For Android testing, make sure Android SDK and JAVA_HOME are properly configured" 