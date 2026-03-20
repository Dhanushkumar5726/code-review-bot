"""
Code Analyzer Node.

Performs a comprehensive LLM-powered analysis of the Python code,
identifying potential bugs, style violations, security issues,
performance concerns, and readability problems.
"""

from src.state import ReviewState  # pyre-ignore
from src.prompts import ANALYZER_PROMPT  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry  # pyre-ignore


def analyzer_node(state: ReviewState) -> dict:
    """
    Analyze the current code for issues.

    Reads the current code and iteration context from state,
    sends it to the LLM for analysis, and returns the raw
    analysis text.
    """
    llm = create_llm(temperature=0.1)

    # Build history context for iterative reviews
    history_context = ""
    if state.get("review_history"):
        history_lines = ["**Previous iteration results:**"]
        for record in state["review_history"]:
            history_lines.append(
                f"  - Iteration {record['iteration']}: "
                f"{record['issues_found']} issues found, "
                f"{record['issues_fixed']} fixed, "
                f"checklist pass rate: {record['checklist_pass_rate']}"
            )
        history_context = "\n".join(history_lines)

    prompt = ANALYZER_PROMPT.format(
        code=state["current_code"],
        iteration=state.get("iteration", 0) + 1,
        max_iterations=state.get("max_iterations", 3),
        history_context=history_context,
        static_results=state.get("static_analysis_results", "No static analysis run yet."),
    )

    response = invoke_with_retry(llm, prompt)

    return {"analysis": response.content}
