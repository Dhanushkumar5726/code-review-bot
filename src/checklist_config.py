"""
Checklist Configuration for the Code Review Bot.

Defines the quality checklist items that the bot validates
code against during each iteration. These items can be
customized for different coding standards.
"""

# Each item is a string description that the LLM evaluates against
REVIEW_CHECKLIST = [
    "PEP 8 naming conventions: variables and functions use snake_case, classes use PascalCase",
    "No use of dangerous functions: eval(), exec(), or compile() with user input",
    "If error handling is present, exceptions are caught specifically and not as bare except clauses",
    "No mutable default arguments in function definitions (e.g., def func(arg=[]))",
    "No unused imports at the top of the file",
    "No hardcoded secrets, passwords, or API keys in the source code",
    "Functions follow single responsibility principle (not overly long or complex)",
]


def get_checklist_text() -> str:
    """Format the checklist items as a numbered list for the LLM prompt."""
    lines = []
    for i, item in enumerate(REVIEW_CHECKLIST, 1):
        lines.append(f"{i}. {item}")
    return "\n".join(lines)
