"""
Fix Suggester Node.

For each identified issue, generates a specific fix suggestion
with explanation and corrected code.
"""

import json

from src.state import ReviewState  # pyre-ignore
from src.prompts import FIX_SUGGESTER_PROMPT  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry, parse_json_from_response  # pyre-ignore


def fix_suggester_node(state: ReviewState) -> dict:
    """
    Generate fix suggestions for each identified issue.

    Uses the LLM to produce specific code fix recommendations
    with explanations.
    """
    llm = create_llm(temperature=0.1)

    # If no issues, skip
    if not state.get("issues"):
        return {"suggestions": []}

    prompt = FIX_SUGGESTER_PROMPT.format(
        issues_json=json.dumps(state["issues"], indent=2),
        code=state["current_code"],
    )

    response = invoke_with_retry(llm, prompt)
    suggestions = parse_json_from_response(response.content)

    return {"suggestions": suggestions}
