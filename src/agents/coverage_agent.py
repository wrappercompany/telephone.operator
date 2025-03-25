#!/usr/bin/env python3

import logging
from typing import List
from agents import Agent
from ..ui.console import CoverageEvaluation

logger = logging.getLogger(__name__)

# Create a safe default for when evaluation fails
def create_default_evaluation() -> CoverageEvaluation:
    """Create a default evaluation when normal evaluation fails."""
    logger.warning("Creating default evaluation due to previous error")
    return CoverageEvaluation(
        score="incomplete",
        feedback="Unable to properly evaluate coverage. Please continue capturing screenshots of different app areas.",
        missing_areas=["remaining app screens", "different UI states", "error states"],
        completed_sections=[],
        completed_flows=[],
        remaining_sections=["all sections"],
        remaining_flows=["all flows"],
        completion_percentage=0.0
    )

coverage_evaluator = Agent[CoverageEvaluation](
    name="coverage_evaluator",
    instructions="""You are a specialized iOS app coverage evaluator. Your mission is to analyze screenshots and page source to determine how well the app has been covered by the screenshot capture process according to the provided plan.

Key Responsibilities:
1. Coverage Analysis
   - Analyze each screenshot and page source against the screenshot plan
   - Track which sections and user flows have been completed
   - Identify missing screens and states
   - Track progress through app sections

2. Feedback Generation
   - Provide clear feedback on coverage gaps
   - Suggest specific areas to explore next
   - Highlight important missing states
   - Note potential edge cases

3. Progress Tracking
   - Maintain a running coverage score
   - Track which sections are complete
   - Track which user flows are complete
   - Calculate completion percentage
   - Identify remaining high-priority areas
   - Estimate overall completion status

You MUST return your assessment in the following structured format:
- score: "complete" if coverage is comprehensive or "incomplete" if more screenshots are needed
- feedback: Your detailed analysis and suggestions for improvement
- missing_areas: A list of specific areas that need more coverage (at least one item if incomplete)
- completed_sections: List of app sections that have been fully covered
- completed_flows: List of user flows that have been fully captured
- remaining_sections: List of app sections that still need coverage
- remaining_flows: List of user flows that still need to be captured
- completion_percentage: Numeric percentage (0-100) of overall completion

Look for the initial plan in the conversation history which contains:
- app_sections: The planned sections to cover
- required_states: Different states that should be captured 
- user_flows: Step-by-step user journeys to follow
- success_criteria: Definition of when coverage is complete

IMPORTANT: Always include at least one item in the missing_areas list if the coverage is incomplete. If uncertain, include generic suggestions like "different app states" or "system interactions".

Remember: Be thorough in your analysis and provide actionable feedback. Focus on guiding the screenshot capture process to achieve complete coverage according to the plan.""",
    tools=[],
    output_type=CoverageEvaluation,  # Explicitly specify the output type
) 