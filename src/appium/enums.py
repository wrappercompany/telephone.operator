from enum import Enum, auto

class ElementState(str, Enum):
    """Element states in the UI."""
    VISIBLE = "visible"
    INVISIBLE = "invisible"
    PRESENT = "present"
    ABSENT = "absent"
    ENABLED = "enabled"
    DISABLED = "disabled"

class AppAction(str, Enum):
    """Actions performed on the app."""
    LAUNCH = "launch"
    CLOSE = "close"
    SCREENSHOT = "screenshot"
    TAP = "tap"
    SWIPE = "swipe"
    INPUT = "input"
    NAVIGATE = "navigate"

class AppiumStatus(str, Enum):
    """Status of Appium operations."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    INVALID_PARAMS = "invalid_params"
    DRIVER_ERROR = "driver_error" 