"""
Code Fixer Node.

Applies the suggested fixes to the current code, producing
a corrected version that is syntactically valid Python.
"""

import json

from src.state import ReviewState  # pyre-ignore
from src.prompts import CODE_FIXER_PROMPT  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry, extract_code_from_response  # pyre-ignore


def code_fixer_node(state: ReviewState) -> dict:
    """
    Apply suggested fixes to produce corrected code.

    Sends the current code and all fix suggestions to the LLM,
    which produces an updated version with all fixes applied.
    """
    llm = create_llm(temperature=0.0)

    # If no suggestions, keep the current code
    if not state.get("suggestions"):
        return {"current_code": state["current_code"]}

    prompt = CODE_FIXER_PROMPT.format(
        code=state["current_code"],
        suggestions_json=json.dumps(state["suggestions"], indent=2),
    )

    response = invoke_with_retry(llm, prompt)
    fixed_code = extract_code_from_response(response.content)

    # Fallback: if extraction fails, keep original code
    if not fixed_code.strip():
        fixed_code = state["current_code"]

    return {"current_code": fixed_code}
