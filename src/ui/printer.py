from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from datetime import datetime
import logging
import traceback
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class Printer:
    def __init__(self, console: Console):
        self.console = console
        self.items: Dict[str, dict] = {}
        self.table = Table(show_header=False, padding=(0, 1), box=None)
        self.table.add_column(width=80)
        self.live = None
        
        try:
            self.live = Live(self.table, console=console, refresh_per_second=4, auto_refresh=False)
            self.live.start()
            logger.info("Printer initialized successfully with live display")
        except Exception as e:
            logger.error(f"Failed to initialize live display: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            # Fallback to simple console output
            print("Live display initialization failed. Using simple console output.")

    def _format_timestamp(self) -> str:
        return f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim]"

    def update_item(self, key: str, content: str, is_done: bool = False, hide_checkmark: bool = False):
        """Update or add an item to the display."""
        if not key or not content:
            logger.warning(f"Empty key or content in update_item: key='{key}', content='{content}'")
            return
            
        try:
            timestamp = self._format_timestamp()
            
            # Format based on type
            if "error" in key.lower():
                content = f"[bold red]{content}[/bold red]"
            elif "warning" in key.lower():
                content = f"[bold yellow]{content}[/bold yellow]"
            elif "success" in key.lower() or is_done:
                content = f"[bold green]{content}[/bold green]"
                
            # Add checkmark for completed items if not hidden
            status = ">" if not is_done else "+"
            if hide_checkmark:
                status = " "
            
            # Create formatted content
            formatted_content = f"{timestamp} {status} {content}"
            
            # Store the item
            self.items[key] = {
                "content": formatted_content,
                "is_done": is_done,
                "timestamp": datetime.now()  # Store timestamp for sorting
            }
            
            # Always print the current item immediately using direct console
            try:
                self.console.print(formatted_content)
            except Exception as e:
                logger.error(f"Failed to print content with rich console: {str(e)}")
                print(formatted_content)  # Fallback to standard print
            
            # Then try to refresh the full display
            try:
                self._refresh_display()
            except Exception as e:
                logger.error(f"Failed to refresh display: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
        except Exception as e:
            logger.error(f"Error in update_item: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            # Fallback to standard print
            print(f"{datetime.now().strftime('%H:%M:%S')} > {content}")

    def mark_item_done(self, key: str):
        """Mark an item as done."""
        if not key:
            logger.warning("Empty key in mark_item_done")
            return
            
        try:
            if key in self.items:
                item = self.items[key]
                if not item["is_done"]:
                    content = item["content"].replace("> ", "+ ", 1)
                    self.items[key] = {
                        "content": content,
                        "is_done": True,
                        "timestamp": item["timestamp"]
                    }
                    try:
                        self.console.print(content)
                    except Exception as e:
                        logger.error(f"Failed to print content with rich console: {str(e)}")
                        print(content)  # Fallback to standard print
                        
                    try:
                        self._refresh_display()
                    except Exception as e:
                        logger.error(f"Failed to refresh display: {str(e)}")
            else:
                logger.warning(f"Attempted to mark non-existent item as done: {key}")
        except Exception as e:
            logger.error(f"Error in mark_item_done: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")

    def _refresh_display(self):
        """Refresh the display with current items."""
        if not self.items:
            logger.debug("No items to display in _refresh_display")
            return
            
        if not self.live or not self.live.is_started:
            logger.debug("Live display not available for refresh")
            return
            
        try:
            self.table.rows = []
            
            # Sort items by timestamp and status
            all_items = sorted(
                self.items.items(),
                key=lambda x: (x[1]["is_done"], x[1]["timestamp"])
            )
            
            # Split into active and done
            active_items = [(k, v) for k, v in all_items if not v["is_done"]]
            done_items = [(k, v) for k, v in all_items if v["is_done"]]
            
            # Add active items
            for _, item in active_items:
                self.table.add_row(item["content"])
                
            # Add a separator if we have both active and done items
            if active_items and done_items:
                self.table.add_row("[dim]" + "─" * 80 + "[/dim]")
                
            # Add completed items (safely get last 5)
            if done_items:
                start_idx = max(0, len(done_items) - 5)
                for _, item in done_items[start_idx:]:
                    self.table.add_row(item["content"])
            
            # Only try to refresh if we have a live display
            if self.live and self.live.is_started:
                try:
                    self.live.refresh()
                except Exception as e:
                    logger.error(f"Error refreshing live display: {str(e)}")
        except Exception as e:
            logger.error(f"Error in _refresh_display: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")

    def end(self):
        """Clean up and close the live display."""
        try:
            if self.live and self.live.is_started:
                logger.info("Stopping live display")
                try:
                    self.console.print()
                except Exception:
                    pass
                self.live.stop()
                logger.info("Live display stopped")
        except Exception as e:
            logger.error(f"Error ending printer: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            try:
                print("\nTerminating display...")
            except Exception:
                pass 