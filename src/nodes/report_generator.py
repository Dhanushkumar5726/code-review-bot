"""
Report Generator Node.

Compiles a comprehensive Markdown review report summarizing
all iterations, issues found, fixes applied, and final status.
"""

import json

from src.state import ReviewState  # pyre-ignore
from src.prompts import REPORT_PROMPT  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry  # pyre-ignore


def report_generator_node(state: ReviewState) -> dict:
    """
    Generate the final comprehensive review report.

    Compiles all review data into a structured Markdown report
    with summaries, issue lists, checklist results, and code
    comparison.
    """
    llm = create_llm(temperature=0.2)

    # Format checklist results for the prompt
    checklist_text = "No checklist results available."
    if state.get("checklist_results"):
        checklist_text = json.dumps(state["checklist_results"], indent=2)

    # Format issues
    issues_json_formatted = json.dumps(state.get("issues", []), indent=2)

    # Format suggestions
    suggestions_json_formatted = json.dumps(state.get("suggestions", []), indent=2)

    prompt = REPORT_PROMPT.format(
        lines_analyzed=len(state["original_code"].splitlines()),
        total_issues=len(state.get("issues", [])),
        original_code=state["original_code"],
        issues_json=issues_json_formatted,
        suggestions_json=suggestions_json_formatted,
        iterations=state.get("iteration", 0),
    )

    response = invoke_with_retry(llm, prompt)

    return {
        "final_report": response.content,
        "is_complete": True,
    }
