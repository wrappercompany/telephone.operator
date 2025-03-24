from dataclasses import dataclass
from typing import List
from rich.console import Console
from rich.panel import Panel

console = Console()

@dataclass
class CoverageEvaluation:
    score: str  # "complete" or "incomplete"
    feedback: str
    missing_areas: List[str]

def print_iteration_progress(current: int, total: int):
    """Print the current iteration progress."""
    console.print(f"\n[bold blue]Iteration {current}/{total}[/bold blue]")

def print_screenshot_results(action: str):
    """Print the results of screenshot capture."""
    console.print(Panel(action, title="Screenshot Results", border_style="green"))

def print_coverage_analysis(result: CoverageEvaluation):
    """Print the coverage analysis results."""
    if result.score == "complete":
        style = "green"
        title = "Coverage Complete"
    else:
        style = "yellow"
        title = "Coverage Analysis"
    
    content = f"Status: {result.score}\nFeedback: {result.feedback}\nMissing Areas: {', '.join(result.missing_areas)}"
    console.print(Panel(content, title=title, border_style=style))

def print_error(message: str):
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")

def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

def print_success(message: str):
    """Print a success message."""
    console.print(f"[bold green]Success:[/bold green] {message}")

def print_appium_status(message: str, is_error: bool = False):
    """Print Appium server status."""
    style = "red" if is_error else "green"
    console.print(f"[bold {style}]Appium Status:[/bold {style}] {message}")

def print_missing_api_key_instructions():
    """Print instructions for setting up OpenAI API key."""
    console.print(Panel(
        "OpenAI API key not found. Please set your OPENAI_API_KEY environment variable:\n\n"
        "1. Copy .env.example to .env\n"
        "2. Add your API key to the .env file\n"
        "3. Run the script again",
        title="API Key Required",
        border_style="red"
    )) 