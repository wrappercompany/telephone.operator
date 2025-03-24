from dataclasses import dataclass
from typing import List, ClassVar
from rich.console import Console
from rich.panel import Panel

console = Console()

@dataclass
class CoverageEvaluation:
    """Evaluation of screenshot coverage."""
    name: ClassVar[str] = "CoverageEvaluation"
    
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
    """Print instructions for setting up the OpenAI API key."""
    console.print(Panel(
        """[red]Error: OpenAI API key not found![/red]

To set up your OpenAI API key:

1. Get your API key from [link]https://platform.openai.com/api-keys[/link]
2. Create a .env file in the project root (copy from .env.example)
3. Add your API key to the .env file:
   [cyan]OPENAI_API_KEY=your_api_key_here[/cyan]

Make sure to keep your API key secret and never commit it to version control.""",
        title="API Key Setup Instructions",
        border_style="red"
    )) 