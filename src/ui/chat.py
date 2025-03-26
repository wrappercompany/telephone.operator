import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import traceback

from agents import Runner, RunConfig, Agent
from agents.items import ItemHelpers

logger = logging.getLogger(__name__)

# Specific instructions for direct chat mode with screenshot agent
CHAT_MODE_INSTRUCTIONS = """You are now in direct chat mode with the iOS screenshot agent. In this mode, you can:

1. Navigation:
   - "Tap on Settings"
   - "Swipe up/down/left/right"
   - "Go back to previous screen"
   - "Navigate to Profile section"

2. Screenshots:
   - "Take a screenshot of this screen"
   - "Capture the login form"
   - "Screenshot all tabs in sequence"

3. App Exploration:
   - "Explore the user profile section"
   - "Show me all main navigation tabs"
   - "Check what happens when I pull to refresh"

4. Form Interactions:
   - "Fill the email field with test@example.com"
   - "Enter password '12345'"
   - "Submit the form"
   - "Toggle the switch"

5. iOS-Specific Commands:
   - "Pull down Control Center"
   - "Show App Switcher"
   - "Press Home button"
   - "Rotate to landscape"

Each instruction will be executed as a single action, so be specific and clear.
For complex tasks, break them down into separate messages.
Type 'help' to see these instructions again.
Type 'exit' to end the chat session.

Current app: {app_name} ({bundle_id})
"""

class ChatInterface:
    """Simple chat interface for direct communication with agents."""
    
    def __init__(self, console: Console):
        self.console = console
        self.chat_history: List[Dict[str, Any]] = []
        logger.info("ChatInterface initialized")
        
    def _display_message(self, role: str, content: str, style: str = "white"):
        """Display a message in the chat interface."""
        try:
            header_style = {
                "user": "bold blue",
                "assistant": "bold green",
                "system": "bold yellow",
                "error": "bold red"
            }.get(role.lower(), "bold")
            
            self.console.print(f"[{header_style}]{role}:[/{header_style}]", end=" ")
            self.console.print(f"[{style}]{content}[/{style}]")
        except Exception as e:
            logger.error(f"Error displaying message: {str(e)}")
            print(f"{role}: {content}")
    
    def _get_user_input(self, prompt: str = "You") -> str:
        """Get input from the user."""
        try:
            return Prompt.ask(f"[bold blue]{prompt}[/bold blue]")
        except KeyboardInterrupt:
            return "exit"
        except Exception as e:
            logger.error(f"Error getting user input: {str(e)}")
            return input(f"{prompt}: ")
    
    def add_to_history(self, role: str, content: str):
        """Add a message to the chat history."""
        self.chat_history.append({"role": role, "content": content})
    
    async def chat_with_agent(self, 
                      agent: Agent, 
                      initial_message: Optional[str] = None,
                      on_start: Optional[Callable[[], None]] = None,
                      on_exit: Optional[Callable[[], None]] = None) -> None:
        """Start a chat session with an agent."""
        
        # Initialize chat 
        if on_start:
            on_start()
            
        self.console.print(Panel("Chat session started. Type 'exit' to end the session or 'help' to see instructions.", 
                               title="Direct Agent Chat",
                               border_style="green"))
        
        # Display initial message if provided
        if initial_message:
            self.console.print(Panel(initial_message, 
                                   title="Chat Mode Instructions",
                                   border_style="blue"))
            self.add_to_history("system", initial_message)
        
        run_config = RunConfig(tracing_disabled=False)
        
        try:
            while True:
                # Get user input
                user_input = self._get_user_input()
                
                # Handle exit command
                if user_input.lower() in ["exit", "quit", "bye"]:
                    self.console.print("[yellow]Ending chat session...[/yellow]")
                    break
                    
                # Handle help command
                if user_input.lower() in ["help", "?"]:
                    if initial_message:
                        self.console.print(Panel(initial_message, 
                                              title="Chat Mode Instructions",
                                              border_style="blue"))
                    else:
                        self.console.print(Panel("Type 'exit' to end the session.", 
                                              title="Help",
                                              border_style="blue"))
                    continue
                
                # Display user message and add to history
                self._display_message("User", user_input, "white")
                self.add_to_history("user", user_input)
                
                # Stream the agent's response
                self.console.print("[bold green]Assistant:[/bold green]", end=" ")
                
                # Run the agent with the input history
                try:
                    # Convert chat history to input items for the agent
                    input_items = [
                        {"role": item["role"], "content": item["content"]} 
                        for item in self.chat_history
                    ]
                    
                    # Run the agent in streaming mode
                    # Set max_turns=1 to limit the agent to a single turn per user message
                    result = Runner.run_streamed(
                        agent,
                        input_items,
                        run_config=run_config,
                        max_turns=10
                    )
                    
                    full_response = ""
                    
                    # Stream the response
                    async for event in result.stream_events():
                        try:
                            if event.type == "raw_response_event":
                                if hasattr(event.data, 'delta') and event.data.delta:
                                    self.console.print(event.data.delta, end="", highlight=False)
                                    full_response += event.data.delta
                            elif event.type == "run_item_stream_event":
                                if event.item.type == "tool_call_item":
                                    tool_info = event.item.raw_item
                                    self.console.print(f"\n[dim cyan]Using tool: {tool_info.name}...[/dim cyan]")
                                elif event.item.type == "tool_call_output_item":
                                    if hasattr(event.item, 'output'):
                                        output_text = str(event.item.output)
                                        self.console.print(f"[dim cyan]Tool result: {output_text}[/dim cyan]")
                        except Exception as e:
                            logger.error(f"Error processing stream event: {str(e)}")
                    
                    # Add a newline after streaming is complete
                    self.console.print()
                    
                    # Add the response to the chat history
                    if full_response:
                        self.add_to_history("assistant", full_response)
                    
                except Exception as e:
                    error_msg = f"Error getting response: {str(e)}"
                    logger.error(error_msg)
                    logger.debug(f"Stack trace: {traceback.format_exc()}")
                    self._display_message("Error", error_msg, "red")
                
        except KeyboardInterrupt:
            self.console.print("[yellow]Chat session interrupted by user.[/yellow]")
        except Exception as e:
            error_msg = f"Unexpected error in chat session: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            self._display_message("Error", error_msg, "red")
        finally:
            if on_exit:
                on_exit()
            self.console.print(Panel("Chat session ended.", border_style="yellow")) 