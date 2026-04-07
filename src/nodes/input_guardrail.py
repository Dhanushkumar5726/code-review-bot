"""
Input Guardrail Node.

Intercepts the user input at the very beginning of the workflow.
If the user asks an off-topic question (e.g. asking for a recipe),
it flags the state as off-topic and populates the final report with a refusal.
Otherwise, it allows the flow to continue to the code review process.
"""

from src.state import ReviewState  # pyre-ignore
from src.prompts import INPUT_GUARDRAIL_PROMPT  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry  # pyre-ignore
import json
import re

def parse_dict_safely(text: str) -> dict:
    cleaned = text.strip()
    
    # Try markdown extraction first
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0]
        
    cleaned = cleaned.strip()
    
    # Attempt standard parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
        
    # If parsing failed, try extracting anything that looks like a JSON object
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
            
    return {}

def input_guardrail_node(state: ReviewState) -> dict:
    """
    Evaluates original_code to see if it's off-topic.
    """
    user_input = state.get("original_code", "").strip()
    
    if not user_input:
        return {"is_off_topic": False}
        
    llm = create_llm(temperature=0.0)
    prompt = INPUT_GUARDRAIL_PROMPT.format(input_text=user_input)
    
    response = invoke_with_retry(llm, prompt)
    
    # Safely parse the JSON response from the LLM
    parsed = parse_dict_safely(response.content)
    
    # If the LLM failed to return a proper dict, we fail open (allow it)
    if not isinstance(parsed, dict):
        return {"is_off_topic": False}
        
    classification = parsed.get("classification", "CODE")
    
    if classification == "OFF_TOPIC":
        refusal_msg = (
            "I am an AI Code Review Bot. I can only assist with code reviews, "
            "software engineering topics, and debugging. Please provide code "
            "for review or a relevant programming question."
        )
        return {
            "is_off_topic": True,
            "final_report": refusal_msg
        }
        
    return {"is_off_topic": False}
