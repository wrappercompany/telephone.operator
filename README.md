# Telephone Operator

An automated iOS app testing and screenshot capture tool powered by OpenAI's GPT models.

## Features

- Automated screenshot capture of iOS apps
- Intelligent coverage analysis
- Progress tracking and reporting
- OpenAI GPT-powered automation

## Prerequisites

- Python 3.9+
- Node.js and npm (for Appium)
- Appium (`npm install -g appium`)
- XCode and iOS Simulator
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/telephone-operator.git
cd telephone-operator
```

2. Install dependencies using uv:
```bash
uv pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

1. Start the iOS Simulator with your desired device

2. Run the screenshot capture:
```bash
python main.py
```

The tool will:
- Launch the specified iOS app
- Systematically capture screenshots of all screens and states
- Analyze coverage and provide feedback
- Continue until complete coverage is achieved

## Project Structure

```
telephone-operator/
├── src/
│   ├── agents/
│   │   ├── screenshot_agent.py
│   │   └── coverage_agent.py
│   ├── appium/
│   │   ├── driver.py
│   │   └── tools.py
│   └── ui/
│       ├── console.py
│       └── printer.py
├── tests/
├── main.py
├── pyproject.toml
└── requirements.txt
```

## License

MIT 