# Appium Tools Tests

This directory contains tests for the Appium tools used in the iOS screenshot capture framework.

## Test Structure

- `test_appium_tools.py`: Contains all test cases for the Appium tools
- `conftest.py`: Contains pytest configuration and fixtures
- `../pytest.ini`: Global pytest configuration
- `../run_tests.py`: Script to run the tests with various options

## Test Categories

The tests are marked with the following categories:

- `asyncio`: Tests that use asyncio
- `appium`: Tests that require an Appium server
- `integration`: Tests that perform integration testing

## Requirements

- Python 3.12+
- Appium server (for running appium tests)
- iOS Simulator or real device connected
- WebDriverAgent installed and configured

## Testing with function_tool Decorators

The Appium tools are decorated with `@function_tool` from the OpenAI Agents SDK. These decorated functions are not directly callable. To test them, we need to:

1. Create a `RunContextWrapper` instance to provide context to the function
2. Serialize parameters to JSON
3. Call `on_invoke_tool` method on the function tool

Example:

```python
from agents import RunContextWrapper

# Create a test context
class TestContext:
    def __init__(self):
        self.data = {}

# Call a function tool
async def call_launch_app(bundle_id: str) -> str:
    ctx = RunContextWrapper(TestContext())
    args = json.dumps({"bundle_id": bundle_id})
    return await launch_app.on_invoke_tool(ctx, args)
```

## Running Tests

### Using run_tests.py

The simplest way to run the tests is using the `run_tests.py` script:

```bash
# Run all tests
./run_tests.py

# Skip tests that require Appium
./run_tests.py --skip-appium

# Specify a different app to test
./run_tests.py --bundle-id "com.example.app"

# Run only specific test categories
./run_tests.py --markers "integration and not appium"

# Run tests in parallel
./run_tests.py --parallel

# Increase verbosity
./run_tests.py --verbose
```

### Using pytest directly

You can also run the tests using pytest directly:

```bash
# Run all tests
pytest

# Run with specific markers
pytest -m "appium"
pytest -m "not appium"
pytest -m "integration"

# Run specific test file
pytest tests/test_appium_tools.py

# Run specific test function
pytest tests/test_appium_tools.py::test_launch_app

# Run with xdist for parallel execution
pytest -n auto
```

## Environment Variables

The tests can be configured with the following environment variables:

- `TEST_APP_BUNDLE_ID`: Bundle ID of the app to test (default: "com.apple.Preferences")
- `SKIP_APPIUM_TESTS`: Set to "true" to skip tests that require Appium
- `APPIUM_HOST`: Appium server host (default: "127.0.0.1")
- `APPIUM_PORT`: Appium server port (default: 4723)
- `IOS_PLATFORM_NAME`: Platform name (default: "iOS")
- `IOS_DEVICE_NAME`: Device name (default: "iPhone 16 Pro")
- `IOS_PLATFORM_VERSION`: Platform version (default: "18.2")
- `IOS_AUTOMATION_NAME`: Automation name (default: "XCUITest")

## Test Cases

The test suite includes the following test cases:

1. **Basic Operations**
   - Launching apps
   - Getting page source
   - Taking screenshots

2. **UI Interactions**
   - Tapping elements by different locator strategies
   - Swiping in different directions
   - Pressing physical buttons
   - Sending input to text fields

3. **Complex Workflows**
   - Multi-step interactions within a single app
   - Cross-app interactions
   - Navigation and state verification

## Troubleshooting

If you encounter issues running the tests:

1. **Appium Server Not Running**
   - Start the Appium server: `appium`
   - Verify the server is running: `curl http://localhost:4723/status`

2. **Device Not Connected**
   - For simulators, ensure the simulator is running
   - For real devices, ensure the device is connected and WebDriverAgent is installed

3. **Permission Issues**
   - Some tests may require specific permissions on the device
   - Tests are designed to handle permission errors gracefully

4. **Test Failures**
   - Check the test logs for specific error messages
   - Verify Appium server logs for connection issues
   - Test against a known working app (e.g., Settings app)

5. **Function Tool Errors**
   - If you see errors about FunctionTool objects not being callable, make sure to use the wrapper pattern shown in the "Testing with function_tool Decorators" section 