import os
from dotenv import load_dotenv
load_dotenv()

from src.graph import build_review_graph
from src.state import ReviewState

if __name__ == "__main__":
    graph = build_review_graph()
    
    test_cases = [
        "Give me a chicken biryani recipe",
        "def hello_world():\n    print('hello world')",
        "Can you review my HTML code? <div>Hello</div>"
    ]
    
    for case in test_cases:
        print(f"Testing input: {case}")
        state = ReviewState(
            original_code=case,
            current_code=case,
            static_analysis_results="",
            analysis="",
            issues=[],
            suggestions=[],
            checklist_results=[],
            all_checks_passed=False,
            iteration=0,
            max_iterations=1,
            is_complete=False,
            review_history=[],
            final_report="",
            is_off_topic=False
        )
        
        result = graph.invoke(state)
        print(f"IS OFF TOPIC: {result.get('is_off_topic')}")
        if result.get("is_off_topic"):
            print(f"REPORT: {result.get('final_report')}")
        print("-" * 40)
