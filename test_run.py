import sys
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from src.graph import build_review_graph

with open("tests/sample_code/medium_code.py", "r", encoding="utf-8") as f:
    code = f.read()

graph = build_review_graph()
final_state = {
    "original_code": code,
    "current_code": code,
    "static_analysis_results": "",
    "analysis": "",
    "issues": [],
    "suggestions": [],
    "checklist_results": [],
    "all_checks_passed": False,
    "iteration": 0,
    "max_iterations": 1,
    "is_complete": False,
    "review_history": [],
    "final_report": "",
}

try:
    for event in graph.stream(final_state):
        for k, v in event.items():
            if isinstance(v, dict):
                final_state.update(v)
    
    print("\n--- FINAL REPORT ---\n")
    print(final_state.get("final_report", "No report generated."))
except Exception as e:
    print("Error:", e)
