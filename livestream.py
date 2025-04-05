#!/usr/bin/env python3

# /// script
# dependencies = [
#   "Appium-Python-Client>=3.1.0",
#   "fastmcp>=0.1.0",
#   "urllib3<2.0.0",
#   "pydantic>=2.0.0",
#   "rich>=13.0.0",
#   "libimobiledevice",
#   "lxml>=4.9.0",
#   "dictdiffer>=0.9.0",
#   "tiktoken>=0.5.0",
# ]
# ///

import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Union, AsyncGenerator
from appium.webdriver.webdriver import WebDriver
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.tree import Tree
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from lxml import etree
from dictdiffer import diff
import tiktoken
from server import device_manager, Config, SwipeDirection
import pytest_asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PageSourceMonitor:
    def __init__(self, interval: float = 1.0, output_dir: Optional[Path] = None, max_depth: int = 5):
        self.interval: float = interval
        self.output_dir: Path = output_dir or Path("page_source_logs")
        self.console: Console = Console()
        self.layout: Layout = Layout()
        self.last_source: Optional[str] = None
        self.last_tree_dict: Optional[Dict[str, Any]] = None
        self.changes_count: int = 0
        self.max_depth: int = max_depth
        self.last_error: Optional[str] = None
        
        # Initialize tokenizer for GPT-4o (latest model)
        self.tokenizers: Dict[str, Optional[Any]] = {
            'gpt-4o': None  # Will be initialized on first use with correct encoding
        }
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
    
    def _setup_layout(self) -> None:
        """Setup the rich layout for display."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
    
    def _element_to_dict(self, element: etree.Element) -> Optional[Dict[str, Any]]:
        """Convert XML element to dictionary focusing on interactive elements and text content."""
        # Get important attributes
        attrs = dict(element.attrib)
        element_type = attrs.get('type', '')
        
        # Only process elements we care about
        if not self._is_meaningful_element({'type': element_type, **attrs}):
            return None
        
        # Create a more meaningful representation
        result: Dict[str, Any] = {
            'type': element_type,
            'name': attrs.get('name', ''),  # This is the accessibility identifier
            'label': attrs.get('label', ''),  # Human readable label
            'value': attrs.get('value', ''),  # Current value/text
            'enabled': attrs.get('enabled', '') == 'true',
            'visible': attrs.get('visible', '') == 'true',
            'accessible': attrs.get('accessible', '') == 'true',
        }
        
        # For buttons and interactive elements, include coordinates for Appium
        if self._is_interactive_element(result):
            result['appium_id'] = result['name'] or result['label']  # Identifier for Appium
            if all(k in attrs for k in ['x', 'y', 'width', 'height']):
                result['geometry'] = {
                    'x': int(attrs['x']),
                    'y': int(attrs['y']),
                    'width': int(attrs['width']),
                    'height': int(attrs['height'])
                }
        
        # Process children
        children = []
        for child in element:
            child_dict = self._element_to_dict(child)
            if child_dict:  # Only include meaningful children
                children.append(child_dict)
        
        if children:
            result['children'] = children
        
        return result
    
    def _is_meaningful_element(self, element_dict: Dict[str, str]) -> bool:
        """Determine if an element is meaningful for interaction or contains important text."""
        element_type = element_dict.get('type', '')
        
        # Interactive elements we care about
        INTERACTIVE_TYPES = {
            'XCUIElementTypeButton',
            'XCUIElementTypeTextField',
            'XCUIElementTypeSecureTextField',
            'XCUIElementTypeCell',  # For table/collection view cells
            'XCUIElementTypeLink',
            'XCUIElementTypeSearchField',
            'XCUIElementTypeSwitch',
            'XCUIElementTypeSlider',
            'XCUIElementTypePickerWheel',
        }
        
        # Text content elements we care about
        TEXT_TYPES = {
            'XCUIElementTypeStaticText',
            'XCUIElementTypeTextView',
            'XCUIElementTypeTextField',
        }
        
        # Always include interactive elements that are enabled and accessible
        if (element_type in INTERACTIVE_TYPES and 
            element_dict.get('enabled') == 'true' and 
            element_dict.get('accessible') == 'true'):
            return True
        
        # Include text elements that have actual content
        if element_type in TEXT_TYPES and any([
            element_dict.get('value'),
            element_dict.get('label'),
            element_dict.get('name')
        ]):
            return True
        
        return False
    
    def _is_interactive_element(self, element_dict: Dict[str, Any]) -> bool:
        """Determine if an element is interactive and can be manipulated by Appium."""
        return (
            element_dict['type'] in {
                'XCUIElementTypeButton',
                'XCUIElementTypeTextField',
                'XCUIElementTypeSecureTextField',
                'XCUIElementTypeCell',
                'XCUIElementTypeLink',
                'XCUIElementTypeSearchField',
                'XCUIElementTypeSwitch',
            } and
            element_dict['enabled'] and
            element_dict['accessible']
        )
    
    def _create_diff_table(self, old_dict: Optional[Dict[str, Any]], new_dict: Optional[Dict[str, Any]]) -> Table:
        """Create a table showing differences between two XML states."""
        table = Table(
            title="Interactive Element Changes",
            show_header=True,
            header_style="bold magenta",
            title_style="bold blue"
        )
        table.add_column("Element", style="cyan", width=30)
        table.add_column("Change Type", style="yellow", width=15)
        table.add_column("Details", style="green")
        
        def _extract_changes(path, old, new, parent_type=""):
            if isinstance(old, dict) and isinstance(new, dict):
                # Only process interactive elements or text content
                if not (self._is_interactive_element(old) or self._is_interactive_element(new)):
                    return
                
                element_type = new.get('type', old.get('type', parent_type))
                appium_id = new.get('appium_id', old.get('appium_id', ''))
                
                # Compare important attributes
                for key in ['value', 'label', 'enabled', 'visible']:
                    if key in old and key in new and old[key] != new[key]:
                        table.add_row(
                            f"{element_type}\n[dim]({appium_id})[/]",
                            key.title(),
                            f"[red]{old[key]}[/] → [green]{new[key]}[/]"
                        )
                
                # Compare children
                if 'children' in old and 'children' in new:
                    _compare_children(path + '.children', old['children'], new['children'], element_type)
            
        def _compare_children(path, old_children, new_children, parent_type):
            old_map = {self._get_element_id(c): c for c in old_children if c}
            new_map = {self._get_element_id(c): c for c in new_children if c}
            
            # Find added and removed elements
            added = set(new_map.keys()) - set(old_map.keys())
            removed = set(old_map.keys()) - set(new_map.keys())
            common = set(old_map.keys()) & set(new_map.keys())
            
            for key in added:
                element = new_map[key]
                if self._is_interactive_element(element):
                    table.add_row(
                        f"{element['type']}\n[dim]({element.get('appium_id', '')})[/]",
                        "Added",
                        f"label: {element.get('label', '')}, value: {element.get('value', '')}"
                    )
            
            for key in removed:
                element = old_map[key]
                if self._is_interactive_element(element):
                    table.add_row(
                        f"{element['type']}\n[dim]({element.get('appium_id', '')})[/]",
                        "Removed",
                        f"label: {element.get('label', '')}, value: {element.get('value', '')}"
                    )
            
            # Compare common elements
            for key in common:
                _extract_changes(
                    f"{path}.{key}",
                    old_map[key],
                    new_map[key],
                    old_map[key].get('type', parent_type)
                )
        
        if old_dict and new_dict:
            _extract_changes("root", old_dict, new_dict)
        
        return table
    
    def _get_element_id(self, element: Optional[Dict[str, Any]]) -> str:
        """Generate a unique identifier for an element."""
        if not element:
            return ""
        
        parts: list[str] = []
        if element.get('type'):
            parts.append(element['type'])
        if element.get('appium_id'):
            parts.append(f"id={element['appium_id']}")
        elif element.get('name'):
            parts.append(f"name={element['name']}")
        if element.get('geometry'):
            geo = element['geometry']
            parts.append(f"pos={geo['x']},{geo['y']}")
        return '|'.join(parts)
    
    def _clean_xml(self, source: str) -> str:
        """Clean XML source before parsing."""
        # Add XML declaration if missing
        if not source.strip().startswith('<?xml'):
            source = '<?xml version="1.0" encoding="UTF-8"?>\n' + source
        
        # Remove any null bytes
        source = source.replace('\x00', '')
        
        # Remove any invalid XML characters
        source = ''.join(char for char in source if ord(char) < 0xD800 or ord(char) > 0xDFFF)
        
        return source
    
    def _parse_xml(self, source: str) -> tuple[Union[Tree, None], Optional[Dict[str, Any]]]:
        """Parse XML and create a rich Tree representation and dictionary."""
        try:
            # Clean the XML first
            cleaned_source = self._clean_xml(source)
            
            # Convert to bytes with explicit encoding
            source_bytes = cleaned_source.encode('utf-8')
            
            # Try to parse
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(source_bytes, parser=parser)
            
            # Convert to dictionary for diffing
            tree_dict = self._element_to_dict(root)
            
            # Check for parser errors
            if len(parser.error_log) > 0:
                errors = [str(error) for error in parser.error_log]
                logger.warning(f"XML parsing warnings: {errors}")
            
            tree = Tree(
                Text(f"[bold blue]{root.tag}[/]", style="bold blue"),
                guide_style="bold bright_black",
            )
            self._build_tree(root, tree, depth=0)
            self.last_error = None
            return tree, tree_dict
        except Exception as e:
            error_msg = f"Error parsing XML: {str(e)}"
            logger.error(error_msg)
            
            try:
                # Save problematic XML for debugging
                if source != self.last_error:
                    # Ensure output directory exists
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    error_file = self.output_dir / f"error_{timestamp}.xml"
                    error_file.write_text(source, encoding='utf-8')
                    self.last_error = source
                    logger.error(f"Saved problematic XML to {error_file}")
            except Exception as save_error:
                logger.error(f"Error saving problematic XML: {save_error}")
            
            # Create error tree with details
            error_tree = Tree("[red]Error parsing XML[/]")
            error_tree.add(f"[yellow]Error: {str(e)}[/]")
            error_tree.add("[yellow]First 500 characters of source:[/]")
            error_tree.add(Syntax(source[:500] + "...", "xml", theme="monokai"))
            return error_tree, None
    
    def _build_tree(self, element: etree.Element, tree: Tree, depth: int = 0) -> None:
        """Recursively build the tree representation."""
        if depth >= self.max_depth:
            if len(element) > 0:
                tree.add("[dim]...[/]")
            return
        
        for child in element:
            try:
                # Get important attributes
                name = child.get('name', '')
                type_ = child.get('type', '')
                label = child.get('label', '')
                value = child.get('value', '')
                
                # Create node label
                node_parts = []
                if type_:
                    node_parts.append(f"[bold cyan]{type_}[/]")
                if name:
                    node_parts.append(f"[yellow]name=[green]\"{name}\"[/]")
                if label and label != name:
                    node_parts.append(f"[yellow]label=[green]\"{label}\"[/]")
                if value and value != name and value != label:
                    node_parts.append(f"[yellow]value=[green]\"{value}\"[/]")
                
                node_label = " ".join(node_parts) if node_parts else "[dim]<empty>[/]"
                
                # Add node to tree
                child_tree = tree.add(node_label)
                self._build_tree(child, child_tree, depth + 1)
            except Exception as e:
                logger.error(f"Error processing element: {e}")
                tree.add(f"[red]Error processing element: {str(e)}[/]")
    
    def _save_page_source(self, source: str) -> bool:
        """Save page source to a file if it has changed."""
        try:
            if source != self.last_source:
                # Ensure output directory exists
                self.output_dir.mkdir(parents=True, exist_ok=True)
                
                # Create timestamp and filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = self.output_dir / f"page_source_{timestamp}.xml"
                
                # Write file with proper encoding
                filename.write_text(source, encoding='utf-8')
                
                self.changes_count += 1
                self.last_source = source
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving page source: {e}")
            return False
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens for GPT-4o (latest model)."""
        try:
            # Initialize tokenizer if not already done
            if not self.tokenizers['gpt-4o']:
                self.tokenizers['gpt-4o'] = tiktoken.get_encoding("cl100k_base")
            
            # Count tokens
            return len(self.tokenizers['gpt-4o'].encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return 0
    
    def _create_token_info(self, token_count: int) -> Text:
        """Create token count and cost info for GPT-4o ($15 per 1M tokens)."""
        cost = (token_count / 1_000_000) * 15.0
        return Text.assemble(
            ("GPT-4o Tokens: ", "bold cyan"),
            (f"{token_count:,}", "green"),
            (" ($", "yellow"),
            (f"{cost:.4f}", "yellow"),
            (")", "yellow")
        )
    
    async def monitor(self) -> None:
        """Start monitoring page source."""
        self._setup_layout()
        
        try:
            # Initialize device session if not already initialized
            if not device_manager.driver:
                await device_manager.initialize_session()
            
            with Live(self.layout, refresh_per_second=4) as live:
                while True:
                    try:
                        # Get current time
                        current_time = datetime.now().strftime("%H:%M:%S")
                        
                        # Get page source
                        source = device_manager.driver.page_source
                        changed = self._save_page_source(source)
                        
                        # Count tokens
                        token_count = self._count_tokens(source)
                        token_info = self._create_token_info(token_count)
                        
                        # Parse and create tree view
                        tree, tree_dict = self._parse_xml(source)
                        
                        # Create diff table if we have previous state
                        diff_table = None
                        if changed and self.last_tree_dict and tree_dict:
                            diff_table = self._create_diff_table(self.last_tree_dict, tree_dict)
                        self.last_tree_dict = tree_dict
                        
                        # Update display
                        self.layout["header"].update(
                            Panel(f"iOS Page Source Monitor - {current_time}")
                        )
                        
                        status = "CHANGED" if changed else "NO CHANGE"
                        color = "green" if changed else "yellow"
                        
                        stats_panel = Panel(
                            f"Status: [{color}]{status}[/]\n"
                            f"Total changes detected: {self.changes_count}\n"
                            f"Output directory: {self.output_dir}\n"
                            f"Tree depth limit: {self.max_depth} levels",
                            title="Statistics"
                        )
                        
                        main_layout = Layout()
                        if diff_table and changed:
                            diff_panel = Panel(diff_table, title="Changes")
                            tree_panel = Panel(tree, title="UI Element Tree")
                            main_layout.split_column(
                                Layout(stats_panel, size=6),
                                Layout(diff_panel, size=10),
                                Layout(tree_panel)
                            )
                        else:
                            tree_panel = Panel(tree, title="UI Element Tree")
                            main_layout.split_column(
                                Layout(stats_panel, size=6),
                                Layout(tree_panel)
                            )
                        
                        self.layout["main"].update(main_layout)
                        
                        # Update footer with token info aligned right
                        footer_text = Text.assemble(
                            (f"Polling interval: {self.interval}s - Press Ctrl+C to stop", "white"),
                            Text("   "), # Spacer
                            token_info
                        )
                        self.layout["footer"].update(Panel(footer_text))
                        
                        await asyncio.sleep(self.interval)
                        
                    except Exception as e:
                        logger.error(f"Error during monitoring: {e}")
                        self.layout["main"].update(
                            Panel(f"[red]Error: {str(e)}[/]")
                        )
                        await asyncio.sleep(self.interval)
                        
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        finally:
            await device_manager.cleanup()

async def main() -> None:
    parser = argparse.ArgumentParser(description='Monitor iOS device page source')
    parser.add_argument('--interval', type=float, default=1.0,
                      help='Polling interval in seconds (default: 1.0)')
    parser.add_argument('--output-dir', type=Path, default=None,
                      help='Directory to save page source logs')
    parser.add_argument('--device-name', type=str, default=Config.DEVICE_NAME,
                      help=f'iOS device name (default: {Config.DEVICE_NAME})')
    parser.add_argument('--ios-version', type=str, default=Config.IOS_VERSION,
                      help=f'iOS version (default: {Config.IOS_VERSION})')
    parser.add_argument('--max-depth', type=int, default=5,
                      help='Maximum depth of the UI tree to display (default: 5)')
    
    args = parser.parse_args()
    
    # Update Config if needed
    if args.device_name:
        Config.DEVICE_NAME = args.device_name
    if args.ios_version:
        Config.IOS_VERSION = args.ios_version
    
    monitor = PageSourceMonitor(
        interval=args.interval,
        output_dir=args.output_dir,
        max_depth=args.max_depth
    )
    await monitor.monitor()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_teardown() -> AsyncGenerator[None, None]:
    """Setup and teardown for each test."""
    try:
        await device_manager.initialize_session()
        # Wait for session to be ready with timeout
        if not await wait_for_appium_ready():
            raise Exception("Appium session failed to initialize")
        yield
    finally:
        await device_manager.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user") 