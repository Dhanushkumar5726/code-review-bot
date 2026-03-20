"""
State definition for the Iterative Code Review Bot.

This module defines the shared state (TypedDict) that flows through
every node in the LangGraph workflow. Each node reads from and writes
to this state, enabling stateful, iterative code review.
"""

from __future__ import annotations
from typing import TypedDict, Annotated
from operator import add


class Issue(TypedDict):
    """A single issue found during code review."""
    issue_id: str
    type: str          # "bug", "style", "security", "performance", "readability"
    severity: str      # "critical", "warning", "info"
    line: int | None
    description: str
    code_snippet: str


class Suggestion(TypedDict):
    """A suggested fix for an identified issue."""
    issue_id: str
    explanation: str
    original_code: str
    fixed_code: str


class ChecklistItem(TypedDict):
    """Result of a single checklist validation."""
    name: str
    passed: bool
    details: str


class IterationRecord(TypedDict):
    """Record of a single review iteration."""
    iteration: int
    issues_found: int
    issues_fixed: int
    checklist_pass_rate: str


class ReviewState(TypedDict):
    """
    The central state that flows through the LangGraph workflow.

    This state is passed to every node and accumulates information
    across the iterative review cycle.
    """
    # --- Input ---
    original_code: str              # The submitted Python code (never modified)

    # --- Working State ---
    current_code: str               # The latest version of the code (updated after fixes)
    static_analysis_results: str    # Output from AST/Flake8 (Syntax/Runtime bugs)
    analysis: str                   # Raw LLM analysis output
    issues: list[Issue]             # List of identified issues
    suggestions: list[Suggestion]   # Suggested fixes for the issues

    # --- Checklist ---
    checklist_results: list[ChecklistItem]  # Pass/fail for each checklist item
    all_checks_passed: bool                  # True if every checklist item passed

    # --- Iteration Control ---
    iteration: int                  # Current iteration number (starts at 0)
    max_iterations: int             # Safety limit to prevent infinite loops
    is_complete: bool               # Whether the review cycle is done

    # --- History & Output ---
    review_history: list[IterationRecord]   # Log of each review iteration
    final_report: str                        # The generated final Markdown report
