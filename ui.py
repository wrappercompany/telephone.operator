#!/usr/bin/env python3

# /// script
# dependencies = [
#   "rich>=13.0.0,<14.0.0",
# ]
# ///

from rich.console import Console
from rich.panel import Panel
from rich.traceback import install
from rich.table import Table
from rich.live import Live
from typing import Dict, Any
from dataclasses import dataclass
from typing import Literal

# Install rich traceback handler
install(show_locals=True)

# Create rich console instance
console = Console()

@dataclass
class CoverageEvaluation:
    feedback: str
    score: Literal["complete", "needs_more", "insufficient"]
    missing_areas: list[str]

class ToolCallLogger:
    def __init__(self):
        self.console = Console()
        
    def log_tool_call(self, tool_name: str, args: Dict[str, Any]):
        # Filter out None values from args
        args_str = ", ".join(f"{k}={v}" for k, v in args.items() if v is not None)
        self.console.print(f"[cyan]Using tool:[/cyan] [green]{tool_name}[/green] [yellow]{args_str}[/yellow]")
    
    def start_live_display(self):
        pass  # No-op, not needed anymore
    
    def stop_live_display(self):
        pass  # No-op, not needed anymore
    
    def clear_history(self):
        pass  # No-op, not needed anymore

def print_iteration_progress(iteration: int, max_iterations: int):
    """Print the current iteration progress."""
    console.clear()
    console.print(f"\n[bold cyan]Iteration {iteration}/{max_iterations}[/bold cyan]")

def print_screenshot_results(latest_action: str):
    """Print the results of screenshot capture."""
    console.print("\n[bold green]Screenshot Results:[/bold green]")
    console.print(Panel(latest_action, border_style="blue"))

def print_coverage_analysis(result: CoverageEvaluation):
    """Print the coverage analysis results."""
    console.print("\n[bold green]Coverage Analysis:[/bold green]")
    console.print(Panel(
        f"Score: {result.score}\n\nFeedback:\n{result.feedback}\n\nMissing Areas:\n" + "\n".join([f"- {area}" for area in result.missing_areas]),
        border_style="yellow",
        title="Coverage Analysis"
    ))

def print_error(error_msg: str):
    """Print an error message."""
    console.print(f"[red]{error_msg}[/red]")

def print_warning(warning_msg: str):
    """Print a warning message."""
    console.print(f"[yellow]{warning_msg}[/yellow]")

def print_success(success_msg: str):
    """Print a success message."""
    console.print(f"[green]{success_msg}[/green]")

def print_appium_status(status_msg: str, is_error: bool = False):
    """Print Appium server status message."""
    if is_error:
        print_error(f"Error: {status_msg}")
    else:
        print_success(status_msg)

def print_missing_api_key_instructions():
    """Print instructions for missing OpenAI API key."""
    print_error("Error: OPENAI_API_KEY not found in environment variables or .env file")
    print_warning("Please create a .env file in the project root with your OpenAI API key:")
    console.print("OPENAI_API_KEY=your_api_key_here")

# Create global tool logger instance
tool_logger = ToolCallLogger() 