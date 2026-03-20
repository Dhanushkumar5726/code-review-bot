"""
Checklist Validator Node.

Validates the current code against the configurable quality
checklist and determines if the review cycle should continue.
"""

from src.state import ReviewState  # pyre-ignore
from src.prompts import CHECKLIST_PROMPT  # pyre-ignore
from src.checklist_config import get_checklist_text  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry, parse_json_from_response  # pyre-ignore


def checklist_node(state: ReviewState) -> dict:
    """
    Validate code against the quality checklist.

    Checks each item in the checklist and determines if the
    code passes. Updates iteration count and review history.
    """
    llm = create_llm(temperature=0.0)

    prompt = CHECKLIST_PROMPT.format(
        code=state["current_code"],
        checklist_items=get_checklist_text(),
    )

    response = invoke_with_retry(llm, prompt)
    checklist_results = parse_json_from_response(response.content)

    # Determine if all checks passed
    all_passed = all(
        item.get("passed", False) for item in checklist_results
    ) if checklist_results else False

    # Calculate pass rate
    total = len(checklist_results) if checklist_results else 0
    passed = sum(1 for item in checklist_results if item.get("passed", False))
    pass_rate = f"{passed}/{total}" if total > 0 else "0/0"

    # Update iteration
    current_iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", 3)

    # Decide if we are done
    is_complete = all_passed or current_iteration >= max_iterations

    # Build iteration record
    iteration_record = {
        "iteration": current_iteration,
        "issues_found": len(state.get("issues", [])),
        "issues_fixed": len(state.get("suggestions", [])),
        "checklist_pass_rate": pass_rate,
    }

    # Append to history
    review_history = list(state.get("review_history", []))
    review_history.append(iteration_record)

    return {
        "checklist_results": checklist_results,
        "all_checks_passed": all_passed,
        "iteration": current_iteration,
        "is_complete": is_complete,
        "review_history": review_history,
    }
