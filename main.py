"""
Iterative Code Review Bot — CLI Entry Point.

Usage:
    python main.py <path_to_python_file>
    python main.py --code "print('hello')"
    python main.py                          # interactive mode
"""

import sys
import os

from dotenv import load_dotenv  # pyre-ignore

# Load environment variables from .env
load_dotenv()

from src.graph import build_review_graph  # pyre-ignore


def read_code_from_file(filepath: str) -> str:
    """Read Python code from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def print_banner():
    """Print the application banner."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    models = {
        "groq": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "ollama": os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
        "gemini": "gemini-2.0-flash",
    }
    model_name = models.get(provider, "unknown")
    print("=" * 60)
    print("  🤖 Iterative Code Review Bot")
    print(f"  Powered by LangGraph + {provider.title()} ({model_name})")
    print("=" * 60)
    print()


def print_progress(event: dict, step: int):
    """Print progress information for each graph step."""
    for node_name, node_output in event.items():
        if node_name == "analyzer":
            print(f"  🔍 Step {step}: Analyzing code...")
        elif node_name == "issue_finder":
            issues = node_output.get("issues", [])
            print(f"  🐛 Step {step}: Found {len(issues)} issue(s)")
            for issue in issues:
                severity_icon = {
                    "critical": "🔴",
                    "warning": "🟡",
                    "info": "🔵",
                }.get(issue.get("severity", ""), "⚪")
                print(f"     {severity_icon} [{issue.get('type', 'unknown')}] {issue.get('description', '')[:80]}")
        elif node_name == "fix_suggester":
            suggestions = node_output.get("suggestions", [])
            print(f"  🔧 Step {step}: Generated {len(suggestions)} fix suggestion(s)")
        elif node_name == "code_fixer":
            print(f"  ✏️  Step {step}: Applied fixes to code")
        elif node_name == "checklist":
            results = node_output.get("checklist_results", [])
            passed = sum(1 for r in results if r.get("passed"))
            total = len(results)
            iteration = node_output.get("iteration", "?")
            print(f"  ✅ Step {step}: Checklist validation — {passed}/{total} passed (iteration {iteration})")
            if not node_output.get("all_checks_passed") and not node_output.get("is_complete"):
                print(f"     ↩️  Looping back for another review iteration...")
        elif node_name == "report_generator":
            print(f"  📄 Step {step}: Report draft generated...")

        elif node_name == "report_validator":
            print(f"  🔎 Step {step}: Validating and correcting report...")


def run_review(code: str, max_iterations: int = 3):
    """Run the iterative code review workflow."""
    print(f"📋 Starting review (max {max_iterations} iterations)...\n")

    # Build the graph
    graph = build_review_graph()

    # Prepare initial state
    initial_state = {
        "original_code": code,
        "current_code": code,
        "analysis": "",
        "issues": [],
        "suggestions": [],
        "checklist_results": [],
        "all_checks_passed": False,
        "iteration": 0,
        "max_iterations": max_iterations,
        "is_complete": False,
        "review_history": [],
        "final_report": "",
    }

    # Stream the graph execution to show progress
    step = 1
    final_state = None
    for event in graph.stream(initial_state):
        print_progress(event, step)
        step += 1
        # Keep track of the latest state
        for node_output in event.values():
            if isinstance(node_output, dict):
                initial_state.update(node_output)
        final_state = initial_state

    print("\n" + "=" * 60)
    print("  📊 REVIEW COMPLETE")
    print("=" * 60 + "\n")

    # Print the final report
    if final_state and final_state.get("final_report"):
        print(final_state["final_report"])
    else:
        print("No report was generated.")

    return final_state


def main():
    """Main entry point for the CLI."""
    print_banner()

    # Check provider configuration
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider == "groq":
        if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key_here":
            print("❌ Error: GROQ_API_KEY not found!")
            print("   Get a FREE key from: https://console.groq.com/keys")
            print("   Then set it in the .env file.")
            sys.exit(1)
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        print(f"⚡ Using Groq cloud: {model}\n")
    elif provider == "gemini":
        if not os.getenv("GOOGLE_API_KEY"):
            print("❌ Error: GOOGLE_API_KEY not found!")
            print("   Or switch to Groq: set LLM_PROVIDER=groq in .env")
            sys.exit(1)
    elif provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        print(f"🏠 Using local Ollama model: {model}\n")

    code = None

    # Mode 1: File path argument
    if len(sys.argv) > 1 and sys.argv[1] != "--code":
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"❌ Error: File not found: {filepath}")
            sys.exit(1)
        code = read_code_from_file(filepath)
        print(f"📂 Reviewing file: {filepath}\n")

    # Mode 2: Inline code argument
    elif len(sys.argv) > 2 and sys.argv[1] == "--code":
        code = sys.argv[2]
        print("📝 Reviewing inline code\n")

    # Mode 3: Interactive mode
    else:
        print("📝 Enter Python code to review (type 'END' on a new line when done):\n")
        lines: list[str] = []
        while True:
            try:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            except EOFError:
                break
        code = "\n".join(lines)

    if not code or not code.strip():
        print("❌ Error: No code provided.")
        sys.exit(1)

    # Run the review
    run_review(code, max_iterations=2)


if __name__ == "__main__":
    main()
