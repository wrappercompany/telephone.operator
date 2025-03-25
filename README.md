# Telephone Operator

An iOS screenshot automation tool that systematically captures all screens of an app using OpenAI's Agents API.

## Overview

Telephone Operator uses a goal-based approach to screenshot capture. Given an app, it:

1. Creates a comprehensive screenshot plan
2. Systematically captures all screens
3. Evaluates progress against the plan
4. Continues until all screens are captured

## How It Works

The system uses a three-agent architecture:

1. **Planner Agent**: Analyzes the app and creates a structured plan breaking down:
   - App sections to cover
   - Required states to capture
   - User flows to follow
   - Success criteria

2. **Screenshot Agent**: Interacts with the iOS app to:
   - Navigate through screens
   - Trigger different states
   - Follow user flows
   - Capture screenshots

3. **Coverage Evaluator**: Tracks progress against the plan:
   - Identifies completed sections and flows
   - Determines what remains to be captured
   - Calculates completion percentage
   - Provides focused feedback

The Manager orchestrates these agents through an iterative process until complete coverage is achieved.

## Getting Started

### Prerequisites

- Python 3.9+
- Appium server
- iOS device or simulator
- OpenAI API key

### Installation

1. Clone the repository
```
git clone https://github.com/yourusername/telephone.operator.git
cd telephone.operator
```

2. Create and activate a virtual environment
```
uv venv
source .venv/bin/activate
```

3. Install dependencies
```
uv pip install -e .
```

4. Set up your environment variables
```
cp .env.example .env
# Edit .env to add your OpenAI API key
```

### Usage

1. Start the Appium server

2. Configure your target app in `main.py`
```python
target_app = {
    "name": "YourAppName",
    "bundle_id": "com.example.appbundleid",
    "description": "A detailed description of your app's functionality"
}
```

3. Run the app
```
uv run main.py
```

## License

[Your license information] 