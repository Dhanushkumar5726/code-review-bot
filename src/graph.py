"""
LangGraph Workflow Definition.

This module wires up all the nodes into a directed graph with
conditional routing that enables the iterative review loop.

Flow:
  START → static_analyzer → analyzer → issue_finder → (has issues?)
    → YES: fix_suggester → code_fixer → checklist → (all pass or max iter?)
        → NO: loop back to analyzer
        → YES: report_generator → report_validator → END
    → NO: report_generator → report_validator → END

report_validator is the NEW second-pass LLM node that fixes
Review Decision, severity labels, URLs, scores, and duplicates
before the report reaches the user.
"""

from langgraph.graph import StateGraph, END, START  # pyre-ignore
from src.state import ReviewState  # pyre-ignore
from src.nodes.static_analyzer import static_analyzer_node  # pyre-ignore
from src.nodes.analyzer import analyzer_node  # pyre-ignore
from src.nodes.issue_finder import issue_finder_node  # pyre-ignore
from src.nodes.fix_suggester import fix_suggester_node  # pyre-ignore
from src.nodes.code_fixer import code_fixer_node  # pyre-ignore
from src.nodes.checklist import checklist_node  # pyre-ignore
from src.nodes.report_generator import report_generator_node  # pyre-ignore
from src.nodes.report_validator import report_validator_node  # pyre-ignore  ← NEW


# ──────────────────────────────────────────────────────────
# Conditional Edge Functions
# ──────────────────────────────────────────────────────────

def route_after_issue_finder(state: ReviewState) -> str:
    """
    After the LLM finds issues, dynamically route the flow:
    - Issues found → fix_suggester
    - No issues → report_generator (skip fix loop)
    """
    if state.get("issues") and len(state["issues"]) > 0:
        return "fix_suggester"
    return "report_generator"


def route_after_checklist(state: ReviewState) -> str:
    """
    Regulate the auto-correction loop.
    - All checks passed OR max iterations reached → report_generator
    - Otherwise → loop back to analyzer with history context
    """
    if state.get("all_checks_passed", False):
        return "report_generator"
    if state.get("is_complete", False):
        return "report_generator"
    return "analyzer"


# ──────────────────────────────────────────────────────────
# Graph Builder
# ──────────────────────────────────────────────────────────

def build_review_graph() -> StateGraph:
    """
    Build and compile the iterative code review graph.

    Returns a compiled LangGraph that can be invoked with
    an initial ReviewState.
    """
    graph = StateGraph(ReviewState)

    # ── Add all nodes ──────────────────────────────────────
    graph.add_node("static_analyzer", static_analyzer_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("issue_finder", issue_finder_node)
    graph.add_node("fix_suggester", fix_suggester_node)
    graph.add_node("code_fixer", code_fixer_node)
    graph.add_node("checklist", checklist_node)
    graph.add_node("report_generator", report_generator_node)
    graph.add_node("report_validator", report_validator_node)  # ← NEW

    # ── Define edges ───────────────────────────────────────

    # START → static_analyzer → analyzer
    graph.add_edge(START, "static_analyzer")
    graph.add_edge("static_analyzer", "analyzer")

    # analyzer → issue_finder
    graph.add_edge("analyzer", "issue_finder")

    # issue_finder → fix_suggester OR report_generator (conditional)
    graph.add_conditional_edges(
        "issue_finder",
        route_after_issue_finder,
        {
            "fix_suggester": "fix_suggester",
            "report_generator": "report_generator",
        },
    )

    # fix_suggester → code_fixer → checklist
    graph.add_edge("fix_suggester", "code_fixer")
    graph.add_edge("code_fixer", "checklist")

    # checklist → analyzer (loop) OR report_generator (conditional)
    graph.add_conditional_edges(
        "checklist",
        route_after_checklist,
        {
            "analyzer": "analyzer",
            "report_generator": "report_generator",
        },
    )

    # report_generator → report_validator → END  ← NEW
    graph.add_edge("report_generator", "report_validator")
    graph.add_edge("report_validator", END)

    compiled = graph.compile()
    return compiled
