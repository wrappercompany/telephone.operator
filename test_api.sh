#!/bin/bash

# Base URL for the API
BASE_URL="http://localhost:8080"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Test function
test_endpoint() {
    local description=$1
    local command=$2
    
    echo -e "\n${GREEN}Testing: $description${NC}"
    echo "Command: $command"
    eval $command
    echo "----------------------------------------"
}

# 1. List connected devices
test_endpoint "List connected devices" \
    "curl $BASE_URL/devices"

# 2. Select first device from the list
DEVICE_UDID="00008140-001944A42813C01C"  # Using the device ID from previous output
test_endpoint "Select device" \
    "curl -X POST $BASE_URL/device/select -H 'Content-Type: application/json' -d '{\"udid\": \"$DEVICE_UDID\"}'"

# 3. Get current device
test_endpoint "Get current device" \
    "curl $BASE_URL/device/current"

# 4. Get device info
test_endpoint "Get device info" \
    "curl $BASE_URL/device/info"

# 5. Take screenshot
test_endpoint "Take screenshot" \
    "curl $BASE_URL/device/screenshot"

# 6. Get orientation
test_endpoint "Get orientation" \
    "curl $BASE_URL/device/orientation"

# 7. Set orientation to landscape
test_endpoint "Set orientation to landscape" \
    "curl -X POST $BASE_URL/device/orientation -H 'Content-Type: application/json' -d '{\"orientation\": \"LANDSCAPE\"}'"

# 8. Lock device
test_endpoint "Lock device" \
    "curl -X POST $BASE_URL/device/lock"

# 9. Unlock device
test_endpoint "Unlock device" \
    "curl -X POST $BASE_URL/device/unlock"

# 10. Press home button
test_endpoint "Press home button" \
    "curl -X POST $BASE_URL/device/home"

# 11. Check if Settings app is installed
test_endpoint "Check if Settings app is installed" \
    "curl \"$BASE_URL/app/installed?bundle_id=com.apple.Preferences\""

# 12. Launch Settings app
test_endpoint "Launch Settings app" \
    "curl -X POST $BASE_URL/app/launch -H 'Content-Type: application/json' -d '{\"bundle_id\": \"com.apple.Preferences\"}'"

# 13. Close Settings app
test_endpoint "Close Settings app" \
    "curl -X POST $BASE_URL/app/close -H 'Content-Type: application/json' -d '{\"bundle_id\": \"com.apple.Preferences\"}'"

# 14. Set orientation back to portrait
test_endpoint "Set orientation back to portrait" \
    "curl -X POST $BASE_URL/device/orientation -H 'Content-Type: application/json' -d '{\"orientation\": \"PORTRAIT\"}'"

echo -e "\n${GREEN}Testing completed!${NC}" 