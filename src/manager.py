from __future__ import annotations

import asyncio
import time
import os
import logging
import traceback
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from agents import Runner, custom_span, gen_trace_id, trace, RunConfig
from rich.console import Console
from agents.items import ItemHelpers
import openai

from .agents.screenshot_agent import screenshot_taker
from .agents.coverage_agent import coverage_evaluator, create_default_evaluation
from .agents.planner_agent import planner_agent, ScreenshotPlan
from .ui.printer import Printer
from .ui.chat import ChatInterface, CHAT_MODE_INSTRUCTIONS
from .appium.driver import ios_driver
from .ui.console import print_missing_api_key_instructions, CoverageEvaluation, print_error, print_warning, print_success

logger = logging.getLogger(__name__)

class ScreenshotManager:
    def __init__(self):
        self.console = Console()
        # Initialize printer with live display disabled to avoid Rich Table errors
        self.printer = Printer(self.console, use_live_display=False)
        logger.info("Initializing ScreenshotManager")
        
        # Load environment variables
        load_dotenv()
        
        # Set up OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found")
            print_missing_api_key_instructions()
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
            
        # Set API key for OpenAI
        openai.api_key = api_key
        # Set API key in environment for agents framework
        os.environ["OPENAI_API_KEY"] = api_key
        logger.info("ScreenshotManager initialized successfully")

    async def run(self, app_config: dict) -> None:
        trace_id = gen_trace_id()
        with trace("Screenshot capture trace", trace_id=trace_id):
            logger.info(f"Starting screenshot capture run for {app_config.get('name', 'unknown app')}")
            self.printer.update_item(
                "header",
                "[bold blue]iOS Screenshot Capture[/bold blue]",
                hide_checkmark=True
            )
            
            self.printer.update_item(
                "trace_id",
                f"[dim blue]View trace: https://platform.openai.com/traces/{trace_id}[/dim blue]",
                hide_checkmark=True
            )

            # Validate app_config
            if not app_config or 'name' not in app_config or 'bundle_id' not in app_config:
                error_msg = "Invalid app configuration: Must contain 'name' and 'bundle_id'"
                logger.error(error_msg)
                print_error(error_msg)
                return

            # Check and initialize Appium connection before making any agent calls
            self.printer.update_item(
                "appium",
                "[bold blue]Initializing Appium connection...[/bold blue]",
                hide_checkmark=True
            )
            
            try:
                # Try to initialize the driver with the app's bundle ID
                if not ios_driver.init_driver(app_config['bundle_id']):
                    error_msg = "Failed to initialize Appium driver. Please check Appium server is running."
                    logger.error(error_msg)
                    print_error(error_msg)
                    self.printer.update_item(
                        "appium",
                        "[bold red]Appium connection failed. Aborting.[/bold red]",
                        is_done=True
                    )
                    return
                    
                self.printer.update_item(
                    "appium",
                    "[bold green]Appium connection successful[/bold green]",
                    is_done=True
                )
            except Exception as e:
                error_msg = f"Error initializing Appium driver: {str(e)}"
                logger.error(error_msg)
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                print_error(error_msg)
                self.printer.update_item(
                    "appium",
                    "[bold red]Appium connection failed. Aborting.[/bold red]",
                    is_done=True
                )
                return
                
            # STEP 1: Create a plan using the planner agent
            self.printer.update_item(
                "planning",
                "[bold blue]Creating screenshot plan...[/bold blue]",
                hide_checkmark=True
            )
            
            planning_input = f"Create a screenshot plan for {app_config['name']}, which is {app_config.get('description', 'an iOS app')}."
            
            try:
                plan_result = await Runner.run(
                    planner_agent,
                    planning_input,
                    run_config=RunConfig(tracing_disabled=False)
                )
                
                screenshot_plan = plan_result.final_output
                
                self.printer.update_item(
                    "planning",
                    f"[bold green]Plan created with {len(screenshot_plan.app_sections)} sections and {len(screenshot_plan.user_flows)} flows[/bold green]",
                    is_done=True
                )
                
                # Format the plan for display
                plan_sections = "\n   - " + "\n   - ".join(screenshot_plan.app_sections)
                plan_states = "\n   - " + "\n   - ".join(screenshot_plan.required_states)
                plan_flows = "\n   - " + "\n   - ".join(screenshot_plan.user_flows)
                plan_criteria = "\n   - " + "\n   - ".join(screenshot_plan.success_criteria)
                
                self.printer.update_item(
                    "plan_details",
                    f"[bold cyan]Screenshot Plan:[/bold cyan]\n"
                    f"[bold]App Sections:{plan_sections}[/bold]\n\n"
                    f"[bold]Required States:{plan_states}[/bold]\n\n"
                    f"[bold]User Flows:{plan_flows}[/bold]\n\n"
                    f"[bold]Success Criteria:{plan_criteria}[/bold]",
                    hide_checkmark=True
                )
                
            except Exception as e:
                error_msg = f"Error creating screenshot plan: {str(e)}"
                logger.error(error_msg)
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                self.printer.update_item(
                    "planning",
                    f"[bold red]Failed to create plan: {str(e)}[/bold red]",
                    is_done=True
                )
                # Create a minimal default plan
                screenshot_plan = ScreenshotPlan(
                    app_sections=["App Main Screens", "Settings", "User Input Forms"],
                    required_states=["Default State", "Filled State", "Error State"],
                    user_flows=["App Launch and Navigation", "Basic Functionality"],
                    success_criteria=["All main screens captured", "All primary functions documented"]
                )

            # Create initial input with the plan
            input_items = [{
                "content": f"""Please launch {app_config['name']} and capture screenshots according to this plan:
                
APP SECTIONS: 
{plan_sections}

REQUIRED STATES:
{plan_states}

USER FLOWS:
{plan_flows}

SUCCESS CRITERIA:
{plan_criteria}

Start by launching the app and systematically work through each section. Use the get_page_source tool with context-aware queries to find relevant elements for each step.""",
                "role": "user"
            }]

            # STEP 2: Execute the iterative screenshot process
            iteration_count = 0
            max_iterations = 20
            
            # Create run config
            run_config = RunConfig(
                tracing_disabled=False
            )

            while iteration_count < max_iterations:
                iteration_count += 1
                logger.info(f"Starting iteration {iteration_count}/{max_iterations}")
                self.printer.update_item(
                    "progress",
                    f"[bold blue]Iteration {iteration_count}/{max_iterations}[/bold blue]",
                    hide_checkmark=True
                )

                try:
                    # Run screenshot capture with streaming
                    # For the first iteration, include the initial message to launch the app
                    # For subsequent iterations, don't include app launch instructions to preserve state
                    iteration_input_items = input_items
                    if iteration_count == 1:
                        # First iteration - use the original input with app launch instruction
                        pass
                    else:
                        # For later iterations, modify input to avoid reopening the app
                        # Get latest feedback only, without the initial app launch message
                        feedback_items = [item for item in input_items if "Please launch" not in item.get("content", "")]
                        if feedback_items:
                            iteration_input_items = feedback_items
                    
                    screenshot_result = await self._capture_screenshots_streamed(iteration_input_items, run_config)
                    if not screenshot_result:
                        logger.error("No screenshot result returned, aborting")
                        print_error("Screenshot capture failed, aborting")
                        break
                        
                    # Get the input list
                    try:
                        new_input_items = screenshot_result.to_input_list()
                        if not new_input_items:
                            logger.warning("Empty input items returned from screenshot agent")
                            new_input_items = input_items  # Use previous input items as fallback
                        input_items = new_input_items
                    except Exception as e:
                        logger.error(f"Error converting screenshot result to input list: {str(e)}")
                        logger.debug(f"Stack trace: {traceback.format_exc()}")
                        # If we can't convert, just keep the old input items
                        print_warning("Error processing screenshot results, using previous context")

                    # Run coverage evaluation with streaming
                    coverage_result = await self._evaluate_coverage_streamed(input_items, run_config)
                    
                    # Process the coverage evaluation result
                    coverage_eval = self._extract_coverage_evaluation(coverage_result)
                    
                    if coverage_eval.score == "complete":
                        logger.info("Screenshot coverage is complete")
                        self.printer.update_item(
                            "complete",
                            f"[bold green]Screenshot coverage is complete ({coverage_eval.completion_percentage:.1f}%)[/bold green]",
                            is_done=True
                        )
                        break

                    if iteration_count == max_iterations:
                        logger.info("Maximum iterations reached")
                        self.printer.update_item(
                            "max_iterations",
                            f"[bold yellow]Maximum iterations reached ({coverage_eval.completion_percentage:.1f}% complete)[/bold yellow]",
                            is_done=True
                        )
                        break

                    # Prepare feedback for next iteration based on the plan
                    if coverage_eval.remaining_sections:
                        next_section = coverage_eval.remaining_sections[0]
                        next_flow = coverage_eval.remaining_flows[0] if coverage_eval.remaining_flows else None
                        
                        if next_flow:
                            feedback_msg = f"Coverage Progress: {coverage_eval.completion_percentage:.1f}%\n\nFeedback: {coverage_eval.feedback}\n\nPlease focus on capturing '{next_section}' section, specifically following this flow: {next_flow}\n\nNote: Continue with the current app state, do not relaunch the app."
                        else:
                            feedback_msg = f"Coverage Progress: {coverage_eval.completion_percentage:.1f}%\n\nFeedback: {coverage_eval.feedback}\n\nPlease focus on capturing '{next_section}' section.\n\nNote: Continue with the current app state, do not relaunch the app."
                    else:
                        # Fall back to existing feedback mechanism
                        missing_areas = self._format_missing_areas(coverage_eval)
                        feedback_msg = f"Coverage Progress: {coverage_eval.completion_percentage:.1f}%\n\nFeedback: {coverage_eval.feedback}\n\nPlease capture screenshots of: {missing_areas}\n\nNote: Continue with the current app state, do not relaunch the app."
                    
                    logger.info(f"Coverage feedback: {feedback_msg[:100]}...")
                    input_items.append({
                        "content": feedback_msg,
                        "role": "user"
                    })

                except Exception as e:
                    error_msg = f"Error during iteration {iteration_count}: {str(e)}"
                    logger.error(error_msg)
                    logger.debug(f"Stack trace: {traceback.format_exc()}")
                    self.printer.update_item(
                        "error",
                        f"[bold red]Error: {str(e)}[/bold red]",
                        is_done=True
                    )
                    break

            self.printer.end()
            logger.info("Screenshot capture run completed")

    def _extract_coverage_evaluation(self, coverage_result) -> CoverageEvaluation:
        """Safely extract coverage evaluation from result."""
        try:
            if not coverage_result:
                logger.warning("No coverage result to extract evaluation from")
                return create_default_evaluation()
                
            # First try to get it through the typesafe API
            try:
                coverage_eval = coverage_result.final_output_as(CoverageEvaluation)
                logger.info(f"Extracted coverage evaluation: {coverage_eval}")
                return coverage_eval
            except (AttributeError, TypeError) as e:
                logger.warning(f"Could not extract coverage evaluation using final_output_as: {str(e)}")
                
            # Fallback to accessing it in other ways
            if hasattr(coverage_result, 'output'):
                try:
                    output = coverage_result.output
                    if isinstance(output, CoverageEvaluation):
                        return output
                except Exception as e:
                    logger.warning(f"Error accessing output attribute: {str(e)}")
                    
            # If all else fails, create a default
            logger.warning("Could not extract coverage evaluation, using default")
            return create_default_evaluation()
        except Exception as e:
            logger.error(f"Error extracting coverage evaluation: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return create_default_evaluation()
            
    def _format_missing_areas(self, coverage_eval: CoverageEvaluation) -> str:
        """Safely format missing areas from coverage evaluation."""
        try:
            if hasattr(coverage_eval, 'missing_areas') and isinstance(coverage_eval.missing_areas, list):
                if coverage_eval.missing_areas:
                    return ', '.join(coverage_eval.missing_areas)
                else:
                    return "additional areas of the app"
            else:
                logger.warning("Invalid or missing missing_areas in coverage evaluation")
                return "different areas of the app"
        except Exception as e:
            logger.error(f"Error formatting missing areas: {str(e)}")
            return "additional app functionality"

    async def _capture_screenshots_streamed(self, input_items: list, run_config: RunConfig):
        with custom_span("Capture Screenshots"):
            logger.info("Starting screenshot capture")
            self.printer.update_item(
                "capturing",
                "[bold blue]Capturing screenshots...[/bold blue]",
                hide_checkmark=True
            )
            
            try:
                result = Runner.run_streamed(
                    screenshot_taker,
                    input_items,
                    run_config=run_config,
                    max_turns=30
                )
                
                async for event in result.stream_events():
                    try:
                        if event.type == "run_item_stream_event":
                            if event.item.type == "tool_call_item":
                                tool_info = event.item.raw_item
                                self.printer.update_item(
                                    f"tool_call_{tool_info.name}",
                                    f"[bold cyan]Tool:[/bold cyan] {tool_info.name}",
                                    hide_checkmark=True
                                )
                            elif event.item.type == "tool_call_output_item":
                                output_text = str(event.item.output) if hasattr(event.item, 'output') else "No output"
                                # Format based on success/failure
                                if "error" in output_text.lower() or "failed" in output_text.lower():
                                    formatted_output = f"[bold red]{output_text}[/bold red]"
                                elif "success" in output_text.lower():
                                    formatted_output = f"[bold green]{output_text}[/bold green]"
                                else:
                                    formatted_output = f"[yellow]{output_text}[/yellow]"
                                
                                self.printer.update_item(
                                    "tool_output",
                                    f"[bold cyan]Result:[/bold cyan] {formatted_output}",
                                    hide_checkmark=True
                                )
                            elif event.item.type == "message_output_item":
                                try:
                                    message = ItemHelpers.text_message_output(event.item)
                                    self.printer.update_item(
                                        "agent_message",
                                        f"[bold magenta]Agent:[/bold magenta] {message}",
                                        hide_checkmark=True
                                    )
                                except Exception as e:
                                    logger.error(f"Error extracting message: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing stream event: {str(e)}")
                
                self.printer.mark_item_done("capturing")
                logger.info("Screenshot capture completed")
                
                try:
                    # Get the final output but handle the case where it might not be awaitable
                    if asyncio.iscoroutine(result.final_output):
                        final_output = await result.final_output
                        logger.info("Successfully got final output from screenshot agent")
                        return final_output
                    else:
                        # Handle case where result is already a value, not a coroutine
                        logger.info("Screenshot result is not awaitable, using directly")
                        return result.final_output
                except Exception as e:
                    logger.error(f"Error getting final output from screenshot agent: {str(e)}")
                    logger.debug(f"Stack trace: {traceback.format_exc()}")
                    self.printer.update_item(
                        "error",
                        f"[bold red]Error getting final output from screenshot agent: {str(e)}[/bold red]",
                        is_done=True
                    )
                    # Return a safe default result
                    return type('EmptyResult', (), {'to_input_list': lambda self: input_items})()
            except Exception as e:
                logger.error(f"Error during screenshot capture: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                self.printer.update_item(
                    "error",
                    f"[bold red]Screenshot capture failed: {str(e)}[/bold red]",
                    is_done=True
                )
                return None

    async def _evaluate_coverage_streamed(self, input_items: list, run_config: RunConfig):
        with custom_span("Evaluate Coverage"):
            logger.info("Starting coverage evaluation")
            self.printer.update_item(
                "evaluating",
                "[bold blue]Evaluating coverage...[/bold blue]",
                hide_checkmark=True
            )
            
            try:
                result = Runner.run_streamed(
                    coverage_evaluator,
                    input_items,
                    run_config=run_config,
                    max_turns=20
                )
                
                async for event in result.stream_events():
                    try:
                        if event.type == "run_item_stream_event":
                            if event.item.type == "tool_call_item":
                                tool_info = event.item.raw_item
                                self.printer.update_item(
                                    f"tool_call_{tool_info.name}",
                                    f"[bold cyan]Tool:[/bold cyan] {tool_info.name}",
                                    hide_checkmark=True
                                )
                            elif event.item.type == "tool_call_output_item":
                                output_text = str(event.item.output) if hasattr(event.item, 'output') else "No output"
                                # Format based on success/failure
                                if "error" in output_text.lower() or "failed" in output_text.lower():
                                    formatted_output = f"[bold red]{output_text}[/bold red]"
                                elif "success" in output_text.lower():
                                    formatted_output = f"[bold green]{output_text}[/bold green]"
                                else:
                                    formatted_output = f"[yellow]{output_text}[/yellow]"
                                
                                self.printer.update_item(
                                    "tool_output",
                                    f"[bold cyan]Result:[/bold cyan] {formatted_output}",
                                    hide_checkmark=True
                                )
                            elif event.item.type == "message_output_item":
                                try:
                                    message = ItemHelpers.text_message_output(event.item)
                                    self.printer.update_item(
                                        "agent_message",
                                        f"[bold magenta]Agent:[/bold magenta] {message}",
                                        hide_checkmark=True
                                    )
                                except Exception as e:
                                    logger.error(f"Error extracting message: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing stream event: {str(e)}")
                
                self.printer.mark_item_done("evaluating")
                logger.info("Coverage evaluation completed")
                
                try:
                    # Get the final output but handle the case where it might not be awaitable
                    if asyncio.iscoroutine(result.final_output):
                        final_output = await result.final_output
                        logger.info("Successfully got final output from coverage agent")
                        return final_output
                    else:
                        # Handle case where result is already a value, not a coroutine
                        logger.info("Coverage result is not awaitable, using directly")
                        return result.final_output
                except Exception as e:
                    logger.error(f"Error getting final output from coverage agent: {str(e)}")
                    logger.debug(f"Stack trace: {traceback.format_exc()}")
                    self.printer.update_item(
                        "error",
                        f"[bold red]Error getting final output from coverage agent: {str(e)}[/bold red]",
                        is_done=True
                    )
                    # Return a safe default result with a properly structured CoverageEvaluation
                    return type('EmptyResult', (), {
                        'final_output_as': lambda self, cls: create_default_evaluation(),
                        'to_input_list': lambda self: input_items
                    })()
            except Exception as e:
                logger.error(f"Error during coverage evaluation: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                self.printer.update_item(
                    "error",
                    f"[bold red]Coverage evaluation failed: {str(e)}[/bold red]",
                    is_done=True
                )
                return None 

    async def chat_with_screenshot_agent(self, app_config: dict) -> None:
        """Start a direct chat session with the screenshot agent."""
        trace_id = gen_trace_id()
        with trace("Screenshot agent chat trace", trace_id=trace_id):
            logger.info(f"Starting direct chat with screenshot agent for {app_config.get('name', 'unknown app')}")
            
            # Validate app_config
            if not app_config or 'name' not in app_config or 'bundle_id' not in app_config:
                error_msg = "Invalid app configuration: Must contain 'name' and 'bundle_id'"
                logger.error(error_msg)
                print_error(error_msg)
                return
            
            # Print trace ID for reference
            self.printer.update_item(
                "trace_id",
                f"[dim blue]View trace: https://platform.openai.com/traces/{trace_id}[/dim blue]",
                hide_checkmark=True
            )
            
            # Check and initialize Appium connection before starting chat
            self.printer.update_item(
                "appium",
                "[bold blue]Initializing Appium connection...[/bold blue]",
                hide_checkmark=True
            )
            
            try:
                # Try to initialize the driver with the app's bundle ID
                if not ios_driver.init_driver(app_config['bundle_id']):
                    error_msg = "Failed to initialize Appium driver. Please check Appium server is running."
                    logger.error(error_msg)
                    print_error(error_msg)
                    self.printer.update_item(
                        "appium",
                        "[bold red]Appium connection failed. Aborting.[/bold red]",
                        is_done=True
                    )
                    return
                    
                self.printer.update_item(
                    "appium",
                    "[bold green]Appium connection successful[/bold green]",
                    is_done=True
                )
            except Exception as e:
                error_msg = f"Error initializing Appium driver: {str(e)}"
                logger.error(error_msg)
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                print_error(error_msg)
                self.printer.update_item(
                    "appium",
                    "[bold red]Appium connection failed. Aborting.[/bold red]",
                    is_done=True
                )
                return
            
            try:
                # Initialize the chat interface
                chat = ChatInterface(self.console)
                
                # Prepare the initial message using the specific chat mode instructions
                initial_message = CHAT_MODE_INSTRUCTIONS.format(
                    app_name=app_config['name'],
                    bundle_id=app_config['bundle_id']
                )
                
                # Start the chat session
                print_success(f"Starting chat session for {app_config['name']}")
                await chat.chat_with_agent(
                    agent=screenshot_taker, 
                    initial_message=initial_message
                )
                
            except Exception as e:
                error_msg = f"Error during screenshot agent chat: {str(e)}"
                logger.error(error_msg)
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                print_error(error_msg) 