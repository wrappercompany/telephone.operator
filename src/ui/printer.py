from dataclasses import dataclass
from typing import Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


@dataclass
class PrinterItem:
    text: str
    is_done: bool = False
    hide_checkmark: bool = False


class Printer:
    def __init__(self, console: Console):
        self.console = console
        self.items: Dict[str, PrinterItem] = {}
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        self.live = Live(
            self.progress,
            console=console,
            refresh_per_second=10,
        )
        self.live.start()
        self.task_ids = {}

    def update_item(
        self, key: str, text: str, is_done: bool = False, hide_checkmark: bool = False
    ) -> None:
        """Update or create a progress item."""
        if key not in self.items:
            task_id = self.progress.add_task(text, total=None)
            self.task_ids[key] = task_id
            self.items[key] = PrinterItem(text=text, is_done=is_done, hide_checkmark=hide_checkmark)
        else:
            self.items[key].text = text
            self.items[key].is_done = is_done
            self.items[key].hide_checkmark = hide_checkmark
            self.progress.update(
                self.task_ids[key],
                description=self._format_item(self.items[key]),
            )

    def mark_item_done(self, key: str) -> None:
        """Mark an item as done."""
        if key in self.items:
            self.items[key].is_done = True
            self.progress.update(
                self.task_ids[key],
                description=self._format_item(self.items[key]),
            )

    def end(self) -> None:
        """End the live display."""
        self.live.stop()

    def _format_item(self, item: PrinterItem) -> str:
        """Format an item for display."""
        if item.is_done and not item.hide_checkmark:
            return f"✓ {item.text}"
        return item.text 