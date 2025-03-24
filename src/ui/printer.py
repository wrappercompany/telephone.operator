from rich.console import Console
from rich.live import Live
from rich.table import Table

class Printer:
    def __init__(self, console: Console):
        self.console = console
        self.items = {}
        self.live = Live(
            self._generate_table(),
            console=console,
            refresh_per_second=4,
        )
        self.live.start()

    def update_item(self, key: str, text: str, is_done: bool = False, hide_checkmark: bool = False):
        """Update a progress item."""
        self.items[key] = {
            "text": text,
            "is_done": is_done,
            "hide_checkmark": hide_checkmark,
        }
        self.live.update(self._generate_table())

    def mark_item_done(self, key: str):
        """Mark an item as done."""
        if key in self.items:
            self.items[key]["is_done"] = True
            self.live.update(self._generate_table())

    def end(self):
        """End the live display."""
        self.live.stop()

    def _generate_table(self) -> Table:
        """Generate the progress table."""
        table = Table(show_header=False, show_footer=False, box=None)
        table.add_column("Status", style="green")
        table.add_column("Message")

        for item in self.items.values():
            status = "✓ " if item["is_done"] and not item["hide_checkmark"] else ""
            table.add_row(status, item["text"])

        return table 