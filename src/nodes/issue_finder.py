"""
Issue Finder Node.

Parses the raw LLM analysis into a structured list of issues,
categorized by type and severity.
"""

from src.state import ReviewState  # pyre-ignore
from src.prompts import ISSUE_FINDER_PROMPT  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry, parse_json_from_response  # pyre-ignore


def issue_finder_node(state: ReviewState) -> dict:
    """
    Extract structured issues from the analysis.

    Parses the raw analysis into categorized issues with
    type, severity, line numbers, and descriptions.
    """
    llm = create_llm(temperature=0.0)

    prompt = ISSUE_FINDER_PROMPT.format(
        analysis=state["analysis"],
        code=state["current_code"],
    )

    response = invoke_with_retry(llm, prompt)
    issues = parse_json_from_response(response.content)

    return {"issues": issues}
