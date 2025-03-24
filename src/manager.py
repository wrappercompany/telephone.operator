from __future__ import annotations

import asyncio
import time
from typing import Optional
from pathlib import Path

from agents import Runner, custom_span, gen_trace_id, trace, RunConfig
from rich.console import Console

from .agents.screenshot_agent import screenshot_taker
from .agents.coverage_agent import coverage_evaluator
from .ui.printer import Printer
from .appium.driver import ios_driver

class ScreenshotManager:
    def __init__(self):
        self.console = Console()
        self.printer = Printer(self.console)

    async def run(self, app_config: dict) -> None:
        trace_id = gen_trace_id()
        with trace("Screenshot capture trace", trace_id=trace_id):
            self.printer.update_item(
                "trace_id",
                f"View trace: https://platform.openai.com/traces/{trace_id}",
                is_done=True,
                hide_checkmark=True,
            )

            self.printer.update_item(
                "starting",
                "Starting screenshot capture...",
                is_done=True,
                hide_checkmark=True,
            )

            iteration_count = 0
            max_iterations = 20
            input_items = [{
                "content": f"Please launch {app_config['name']} and start capturing screenshots systematically.",
                "role": "user"
            }]

            # Create run config
            run_config = RunConfig(
                tracing_disabled=False,
            )

            while iteration_count < max_iterations:
                iteration_count += 1
                self.printer.update_item(
                    "progress",
                    f"Iteration {iteration_count}/{max_iterations}",
                    hide_checkmark=True,
                )

                try:
                    # Run screenshot capture
                    screenshot_result = await self._capture_screenshots(input_items, run_config)
                    input_items = screenshot_result.to_input_list()

                    # Run coverage evaluation
                    coverage_result = await self._evaluate_coverage(input_items, run_config)

                    if coverage_result.score == "complete":
                        self.printer.update_item(
                            "complete",
                            "Screenshot coverage is complete!",
                            is_done=True,
                        )
                        break

                    if iteration_count == max_iterations:
                        self.printer.update_item(
                            "max_iterations",
                            "Maximum iterations reached",
                            is_done=True,
                        )
                        break

                    # Add feedback for next iteration
                    input_items.append({
                        "content": f"Coverage Feedback: {coverage_result.feedback}\nPlease capture screenshots of: {', '.join(coverage_result.missing_areas)}",
                        "role": "user"
                    })

                except Exception as e:
                    self.printer.update_item(
                        "error",
                        f"Error: {str(e)}",
                        is_done=True,
                    )
                    break

            self.printer.end()

    async def _capture_screenshots(self, input_items: list, run_config: RunConfig):
        with custom_span("Capture Screenshots"):
            self.printer.update_item("capturing", "Capturing screenshots...")
            result = await Runner.run(
                screenshot_taker,
                input_items,
                run_config=run_config,
                max_turns=30
            )
            self.printer.mark_item_done("capturing")
            return result

    async def _evaluate_coverage(self, input_items: list, run_config: RunConfig):
        with custom_span("Evaluate Coverage"):
            self.printer.update_item("evaluating", "Evaluating coverage...")
            result = await Runner.run(
                coverage_evaluator,
                input_items,
                run_config=run_config,
                max_turns=20
            )
            self.printer.mark_item_done("evaluating")
            return result.final_output 