from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from datetime import datetime
import logging
import traceback
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class Printer:
    def __init__(self, console: Console, use_live_display: bool = False):
        self.console = console
        self.items: Dict[str, dict] = {}
        self.use_live_display = use_live_display
        self.live = None
        
        # Only setup live display if requested
        if self.use_live_display:
            try:
                self.table = Table(show_header=False, padding=(0, 1), box=None)
                self.table.add_column(width=80)
                # Add a dummy row to prevent "list index out of range" error
                self.table.add_row("")
                self.live = Live(self.table, console=console, refresh_per_second=4, auto_refresh=False)
                self.live.start()
                logger.info("Printer initialized with live display")
            except Exception as e:
                logger.error(f"Failed to initialize live display: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                self.use_live_display = False
                
        logger.info("Printer initialized successfully")

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
                formatted_content = f"[bold red]{content}[/bold red]"
            elif "warning" in key.lower():
                formatted_content = f"[bold yellow]{content}[/bold yellow]"
            elif "success" in key.lower() or is_done:
                formatted_content = f"[bold green]{content}[/bold green]"
            else:
                formatted_content = content
                
            # Add checkmark for completed items if not hidden
            status = ">" if not is_done else "+"
            if hide_checkmark:
                status = " "
            
            # Create formatted content
            display_text = f"{timestamp} {status} {formatted_content}"
            
            # Store the item
            self.items[key] = {
                "content": display_text,
                "raw_content": content,
                "is_done": is_done,
                "timestamp": datetime.now()  # Store timestamp for sorting
            }
            
            # Always use direct console print - more reliable
            self._safe_print(display_text)
            
            # Only try to refresh live display if explicitly enabled
            if self.use_live_display:
                try:
                    self._refresh_live_display()
                except Exception as e:
                    logger.error(f"Failed to refresh live display: {str(e)}")
                    logger.debug(f"Stack trace: {traceback.format_exc()}")
        except Exception as e:
            logger.error(f"Error in update_item: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            # Last resort fallback
            try:
                print(f"{datetime.now().strftime('%H:%M:%S')} {content}")
            except:
                pass

    def _safe_print(self, text: str):
        """Safely print to console with fallbacks."""
        try:
            self.console.print(text)
        except Exception as e:
            # If rich console fails, try standard print
            logger.error(f"Rich console print failed: {str(e)}")
            try:
                # Strip any Rich markup before printing
                clean_text = text.replace("[bold red]", "").replace("[/bold red]", "")
                clean_text = clean_text.replace("[bold yellow]", "").replace("[/bold yellow]", "")
                clean_text = clean_text.replace("[bold green]", "").replace("[/bold green]", "")
                clean_text = clean_text.replace("[dim]", "").replace("[/dim]", "")
                print(clean_text)
            except Exception as e2:
                logger.error(f"Standard print also failed: {str(e2)}")

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
                        "raw_content": item.get("raw_content", ""),
                        "is_done": True,
                        "timestamp": item["timestamp"]
                    }
                    # Safe print
                    self._safe_print(content)
                    
                    if self.use_live_display:
                        try:
                            self._refresh_live_display()
                        except Exception as e:
                            logger.error(f"Failed to refresh live display: {str(e)}")
            else:
                logger.warning(f"Attempted to mark non-existent item as done: {key}")
        except Exception as e:
            logger.error(f"Error in mark_item_done: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")

    def _refresh_live_display(self):
        """Refresh the live display with current items."""
        if not self.use_live_display or not self.live or not hasattr(self, 'table'):
            return
            
        try:
            # Reset table but always keep at least one row
            self.table.rows.clear()
            self.table.add_row("")
            
            # Get and sort items
            all_items = list(self.items.values())
            all_items.sort(key=lambda x: (x["is_done"], x["timestamp"]))
            
            # Split into active and done items
            active_items = [item for item in all_items if not item["is_done"]]
            done_items = [item for item in all_items if item["is_done"]]
            
            # Add active items
            for item in active_items:
                self.table.add_row(item["content"])
                
            # Add separator if we have both types
            if active_items and done_items:
                self.table.add_row("[dim]" + "─" * 80 + "[/dim]")
                
            # Add most recent completed items
            recent_done = done_items[-5:] if len(done_items) > 5 else done_items
            for item in recent_done:
                self.table.add_row(item["content"])
            
            # Try to refresh
            if self.live and self.live.is_started:
                self.live.refresh()
        except Exception as e:
            logger.error(f"Error in _refresh_live_display: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")

    def end(self):
        """Clean up and close the live display."""
        try:
            if self.use_live_display and self.live and self.live.is_started:
                logger.info("Stopping live display")
                try:
                    # Display one final message
                    self._safe_print("\nDisplay terminated.")
                    # Stop the live display
                    self.live.stop()
                    logger.info("Live display stopped")
                except Exception as e:
                    logger.error(f"Error stopping live display: {str(e)}")
        except Exception as e:
            logger.error(f"Error ending printer: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            try:
                print("\nTerminating display...")
            except:
                pass 