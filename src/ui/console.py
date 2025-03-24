from dataclasses import dataclass
from typing import List, ClassVar, Optional
import logging
import traceback
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install

# Install rich traceback handler
install()

# Configure console logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create a global console instance
try:
    console = Console()
    logger.debug("Console initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Rich console: {str(e)}")
    # Create a fallback console that will just use print()
    class FallbackConsole:
        def print(self, *args, **kwargs):
            try:
                print(*args)
            except Exception as e:
                logger.error(f"Fallback print failed: {str(e)}")
    console = FallbackConsole()

@dataclass
class CoverageEvaluation:
    """Evaluation of screenshot coverage."""
    name: ClassVar[str] = "CoverageEvaluation"
    
    score: str  # "complete" or "incomplete"
    feedback: str
    missing_areas: List[str]
    
    def __post_init__(self):
        """Validate the evaluation data."""
        try:
            # Ensure score is valid
            if self.score not in ["complete", "incomplete"]:
                logger.warning(f"Invalid score value: {self.score}. Defaulting to 'incomplete'")
                self.score = "incomplete"
            
            # Ensure feedback is not empty
            if not self.feedback:
                logger.warning("Empty feedback provided. Using default.")
                self.feedback = "Continue capturing screenshots of different app areas."
            
            # Ensure missing_areas is a list and not empty when incomplete
            if not isinstance(self.missing_areas, list):
                logger.warning(f"missing_areas is not a list: {type(self.missing_areas)}. Converting to list.")
                self.missing_areas = [str(self.missing_areas)] if self.missing_areas else []
            
            if self.score == "incomplete" and not self.missing_areas:
                logger.warning("Score is incomplete but missing_areas is empty. Adding default.")
                self.missing_areas = ["different app screens", "various UI states"]
        except Exception as e:
            logger.error(f"Error in CoverageEvaluation.__post_init__: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            # Set safe defaults
            if not hasattr(self, 'score') or not self.score:
                self.score = "incomplete"
            if not hasattr(self, 'feedback') or not self.feedback:
                self.feedback = "Continue capturing screenshots."
            if not hasattr(self, 'missing_areas') or not self.missing_areas:
                self.missing_areas = ["app screens"]

def print_iteration_progress(current: int, total: int):
    """Print the current iteration progress."""
    try:
        console.print(f"\n[bold blue]Iteration {current}/{total}[/bold blue]")
        logger.info(f"Iteration progress: {current}/{total}")
    except Exception as e:
        logger.error(f"Error printing iteration progress: {str(e)}")
        try:
            print(f"\nIteration {current}/{total}")
        except:
            pass

def print_screenshot_results(action: str):
    """Print the results of screenshot capture."""
    try:
        if not action:
            action = "Screenshot captured"
        console.print(Panel(action, title="Screenshot Results", border_style="green"))
        logger.info(f"Screenshot results: {action}")
    except Exception as e:
        logger.error(f"Error printing screenshot results: {str(e)}")
        try:
            print(f"Screenshot Results: {action}")
        except:
            pass

def print_coverage_analysis(result: Optional[CoverageEvaluation]):
    """Print the coverage analysis results."""
    try:
        if not result:
            logger.warning("No coverage evaluation provided")
            result = CoverageEvaluation(
                score="incomplete",
                feedback="No coverage data available",
                missing_areas=["all app areas"]
            )
            
        if result.score == "complete":
            style = "green"
            title = "Coverage Complete"
        else:
            style = "yellow"
            title = "Coverage Analysis"
        
        # Format missing areas with proper handling for empty list
        missing_areas_text = ", ".join(result.missing_areas) if result.missing_areas else "None specified"
        
        content = f"Status: {result.score}\nFeedback: {result.feedback}\nMissing Areas: {missing_areas_text}"
        
        try:
            console.print(Panel(content, title=title, border_style=style))
        except Exception as e:
            logger.error(f"Failed to print panel: {str(e)}")
            print(f"\n{title}:\n{content}")
            
        logger.info(f"Coverage analysis: score={result.score}, missing_areas={missing_areas_text}")
    except Exception as e:
        logger.error(f"Error printing coverage analysis: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        try:
            print_error(f"Failed to display coverage analysis: {str(e)}")
        except:
            print(f"Error displaying coverage analysis: {str(e)}")

def print_error(message: str):
    """Print an error message."""
    try:
        console.print(f"[bold red]Error:[/bold red] {message}")
        logger.error(message)
    except Exception as e:
        # Last resort fallback if rich console fails
        logger.error(f"Rich console error display failed: {str(e)}")
        try:
            print(f"ERROR: {message}")
        except Exception as e2:
            logger.error(f"Standard print also failed: {str(e2)}")

def print_warning(message: str):
    """Print a warning message."""
    try:
        console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
        logger.warning(message)
    except Exception as e:
        logger.error(f"Rich console warning display failed: {str(e)}")
        try:
            print(f"WARNING: {message}")
        except Exception as e2:
            logger.error(f"Standard print also failed: {str(e2)}")

def print_success(message: str):
    """Print a success message."""
    try:
        console.print(f"[bold green]Success:[/bold green] {message}")
        logger.info(f"Success: {message}")
    except Exception as e:
        logger.error(f"Rich console success display failed: {str(e)}")
        try:
            print(f"SUCCESS: {message}")
        except Exception as e2:
            logger.error(f"Standard print also failed: {str(e2)}")

def print_appium_status(message: str, is_error: bool = False):
    """Print Appium server status."""
    try:
        style = "red" if is_error else "green"
        console.print(f"[bold {style}]Appium Status:[/bold {style}] {message}")
        if is_error:
            logger.error(f"Appium status: {message}")
        else:
            logger.info(f"Appium status: {message}")
    except Exception as e:
        logger.error(f"Rich console appium status display failed: {str(e)}")
        try:
            status_type = "ERROR" if is_error else "INFO"
            print(f"APPIUM STATUS ({status_type}): {message}")
        except Exception as e2:
            logger.error(f"Standard print also failed: {str(e2)}")

def print_missing_api_key_instructions():
    """Print instructions for setting up the OpenAI API key."""
    instructions = """
Error: OpenAI API key not found!

To set up your OpenAI API key:

1. Get your API key from https://platform.openai.com/api-keys
2. Create a .env file in the project root (copy from .env.example)
3. Add your API key to the .env file:
   OPENAI_API_KEY=your_api_key_here

Make sure to keep your API key secret and never commit it to version control.
"""
    
    try:
        console.print(Panel(
            f"[red]{instructions}[/red]",
            title="API Key Setup Instructions",
            border_style="red"
        ))
        logger.error("Missing OpenAI API key")
    except Exception as e:
        logger.error(f"Rich console API key instructions display failed: {str(e)}")
        try:
            print(f"ERROR: OpenAI API key not found.\n{instructions}")
        except Exception as e2:
            logger.error(f"Standard print also failed: {str(e2)}")
            # Last resort
            print("ERROR: OpenAI API key not found. See docs for setup instructions.") 