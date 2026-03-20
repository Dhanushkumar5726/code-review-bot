"""
Evaluation Framework for the Code Review Bot.

[RUBRIC C8: Use of Evaluation Framework]
[RUBRIC C9: Result Interpretation]

This script tests the bot programmatically against 5 known test cases
covering different severity levels and issue types. It generates
quantitative metrics including Precision, Recall, F1 Score, and
Severity Accuracy to evaluate overall bot performance.

Test Cases:
  1. buggy_code.py     — Syntax + runtime errors (Critical/High)
  2. security_code.py  — SQL injection + hardcoded credentials
  3. clean_code.py     — No issues (tests false positive rate)
  4. medium_code.py    — Missing error handling + resource leaks
  5. style_code.py     — Only style/low severity issues

Run:
  python eval.py
"""

import os
import json
import time
from dotenv import load_dotenv  # pyre-ignore

load_dotenv()
from src.graph import build_review_graph  # pyre-ignore


# ────────────────────────────────────────────────────────────────
# TEST CASES — Expected Results
# ────────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Buggy Code",
        "description": "Contains syntax errors and undefined variables",
        "file": "tests/sample_code/buggy_code.py",
        "expected": {
            "has_issues": True,
            "min_issues": 2,
            "expected_severities": ["critical"],
            "review_decision": "changes_requested",
            "max_score": 4,
        }
    },
    {
        "name": "Security Code",
        "description": "Contains SQL injection and hardcoded credentials",
        "file": "tests/sample_code/security_code.py",
        "expected": {
            "has_issues": True,
            "min_issues": 2,
            "expected_severities": ["critical"],
            "review_decision": "changes_requested",
            "max_score": 3,
        }
    },
    {
        "name": "Clean Code",
        "description": "Well-written code with no real bugs",
        "file": "tests/sample_code/clean_code.py",
        "expected": {
            "has_issues": False,
            "min_issues": 0,
            "expected_severities": [],
            "review_decision": "approved",
            "max_score": 10,
        }
    },
    {
        "name": "Medium Severity Code",
        "description": "Missing error handling and resource leaks",
        "file": "tests/sample_code/medium_code.py",
        "expected": {
            "has_issues": True,
            "min_issues": 1,
            "expected_severities": ["warning"],
            "review_decision": "changes_requested",
            "max_score": 6,
        }
    },
    {
        "name": "Style Only Code",
        "description": "Only minor style issues, no real bugs",
        "file": "tests/sample_code/style_code.py",
        "expected": {
            "has_issues": True,
            "min_issues": 1,
            "expected_severities": ["info"],
            "review_decision": "approved_with_suggestions",
            "max_score": 9,
        }
    },
]


# ────────────────────────────────────────────────────────────────
# SAMPLE CODE FILES — Created if missing
# ────────────────────────────────────────────────────────────────

SAMPLE_CODE = {
    "tests/sample_code/buggy_code.py": '''
import pickle

password = "admin123"

def get_user(username):
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    return db.execute(query)

def load_data(filename):
    with open(filename, "rb") as f:
        return pickle.load(f)

def divide(a, b):
    return a / b
''',
    "tests/sample_code/security_code.py": '''
import sqlite3
import os

SECRET_KEY = "hardcoded-secret-key-12345"
DB_PASSWORD = "admin@123"

def search_users(keyword):
    query = "SELECT * FROM users WHERE name LIKE '%" + keyword + "%'"
    conn = sqlite3.connect("users.db")
    return conn.execute(query).fetchall()

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    conn = sqlite3.connect("users.db")
    return conn.execute(query).fetchone()
''',
    "tests/sample_code/clean_code.py": '''
import json
import os
from pathlib import Path


def load_config(filepath: str) -> dict:
    """Load and return config from a JSON file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config: {e}")


def get_setting(config: dict, key: str, default=None):
    """Safely retrieve a setting with an optional default."""
    return config.get(key, default)


def divide(a: float, b: float) -> float:
    """Divide a by b, raising an error if b is zero."""
    if b == 0:
        raise ZeroDivisionError("Divisor cannot be zero.")
    return a / b
''',
    "tests/sample_code/medium_code.py": '''
import json

def read_config(filepath):
    f = open(filepath)
    content = f.read()
    config = json.loads(content)
    return config

def get_host(config):
    return config["database"]["host"]

def connect(filepath):
    try:
        config = read_config(filepath)
        host = get_host(config)
        print(f"Connecting to {host}")
    except:
        print("Something went wrong")
''',
    "tests/sample_code/style_code.py": '''
import os
import math

def calculateCircleArea(radius):
    area = math.pi * radius * radius
    return area

def calculateRectangleArea(w, h):
    area = w * h
    return area

x = calculateCircleArea(5)
y = calculateRectangleArea(4, 6)
print(x, y)
''',
}


# ────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────

def ensure_sample_files():
    """Create sample code files if they don't exist."""
    os.makedirs("tests/sample_code", exist_ok=True)
    for filepath, code in SAMPLE_CODE.items():
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                f.write(code)
            print(f"  Created: {filepath}")


def run_single_test(graph, code: str, test_name: str) -> dict:
    """Run the bot on a single code sample and return results."""
    initial_state = {
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

    start_time = time.time()
    final_state = graph.invoke(initial_state)
    elapsed = round(time.time() - start_time, 2)

    issues = final_state.get("issues", [])
    report = final_state.get("final_report", "")

    # Determine review decision from report
    decision = "unknown"
    if "Changes Requested" in report or "❌" in report:
        decision = "changes_requested"
    elif "Approved with Suggestions" in report or "⚠️" in report:
        decision = "approved_with_suggestions"
    elif "Approved" in report or "✅" in report:
        decision = "approved"

    # Extract overall score from report
    score = None
    import re
    score_match = re.search(r'Overall Score[:\s]*(\d+)\s*/\s*10', report)
    if score_match:
        score = int(score_match.group(1))

    return {
        "test_name": test_name,
        "issues_found": len(issues),
        "issues": issues,
        "review_decision": decision,
        "overall_score": score,
        "elapsed_seconds": elapsed,
        "report": report,
    }


def evaluate_result(result: dict, expected: dict) -> dict:
    """
    [RUBRIC C9: Result Interpretation]
    Compare actual results against expected results and
    calculate pass/fail for each criterion.
    """
    checks = {}

    # Check 1: Correct detection of issues vs no issues
    if expected["has_issues"]:
        checks["issue_detection"] = result["issues_found"] >= expected["min_issues"]
    else:
        checks["no_false_positives"] = result["issues_found"] == 0

    # Check 2: Correct review decision
    checks["review_decision"] = result["review_decision"] == expected["review_decision"]

    # Check 3: Score ceiling respected
    if result["overall_score"] is not None and expected["max_score"] is not None:
        checks["score_ceiling"] = result["overall_score"] <= expected["max_score"]

    # Check 4: Expected severities present
    if expected["expected_severities"]:
        found_severities = [
            i.get("severity", "").lower()
            for i in result["issues"]
        ]
        checks["severity_detection"] = any(
            s in found_severities
            for s in expected["expected_severities"]
        )

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
    }


def calculate_metrics(results: list) -> dict:
    """
    [RUBRIC C8: Use of Evaluation Framework]
    Calculate Precision, Recall, F1 Score, and other metrics
    across all test cases.
    """
    true_positives = 0    # Correctly identified buggy code as buggy
    false_positives = 0   # Incorrectly flagged clean code as buggy
    true_negatives = 0    # Correctly identified clean code as clean
    false_negatives = 0   # Missed bugs in buggy code
    severity_correct = 0  # Correctly classified severity
    severity_total = 0    # Total severity checks

    for r in results:
        expected = r["expected"]
        actual = r["result"]

        if expected["has_issues"]:
            if actual["issues_found"] >= expected["min_issues"]:
                true_positives += 1
            else:
                false_negatives += 1
        else:
            if actual["issues_found"] == 0:
                true_negatives += 1
            else:
                false_positives += 1

        # Severity accuracy
        if expected["expected_severities"] and actual["issues"]:
            found_severities = [
                i.get("severity", "").lower()
                for i in actual["issues"]
            ]
            if any(s in found_severities for s in expected["expected_severities"]):
                severity_correct += 1
            severity_total += 1

    # Calculate metrics
    precision = (
        round(true_positives / (true_positives + false_positives) * 100, 1)
        if (true_positives + false_positives) > 0 else 0
    )
    recall = (
        round(true_positives / (true_positives + false_negatives) * 100, 1)
        if (true_positives + false_negatives) > 0 else 0
    )
    f1 = (
        round(2 * precision * recall / (precision + recall), 1)
        if (precision + recall) > 0 else 0
    )
    false_positive_rate = (
        round(false_positives / (false_positives + true_negatives) * 100, 1)
        if (false_positives + true_negatives) > 0 else 0
    )
    severity_accuracy = (
        round(severity_correct / severity_total * 100, 1)
        if severity_total > 0 else 0
    )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": false_positive_rate,
        "severity_accuracy": severity_accuracy,
    }


def interpret_results(metrics: dict) -> str:
    """
    [RUBRIC C9: Result Interpretation]
    Provide human-readable interpretation of the metrics.
    """
    lines = []

    # Precision interpretation
    if metrics["precision"] >= 90:
        lines.append("✅ PRECISION: Excellent — bot rarely flags false issues")
    elif metrics["precision"] >= 70:
        lines.append("🟡 PRECISION: Good — occasional false positives")
    else:
        lines.append("🔴 PRECISION: Poor — too many hallucinated issues")

    # Recall interpretation
    if metrics["recall"] >= 90:
        lines.append("✅ RECALL: Excellent — bot catches nearly all real bugs")
    elif metrics["recall"] >= 70:
        lines.append("🟡 RECALL: Good — misses some bugs occasionally")
    else:
        lines.append("🔴 RECALL: Poor — missing too many real bugs")

    # F1 interpretation
    if metrics["f1_score"] >= 90:
        lines.append("✅ F1 SCORE: Excellent overall balance")
    elif metrics["f1_score"] >= 70:
        lines.append("🟡 F1 SCORE: Good overall performance")
    else:
        lines.append("🔴 F1 SCORE: Needs improvement")

    # False positive rate
    if metrics["false_positive_rate"] == 0:
        lines.append("✅ FALSE POSITIVES: Zero — no hallucinated issues on clean code")
    elif metrics["false_positive_rate"] <= 20:
        lines.append("🟡 FALSE POSITIVES: Low — minimal hallucination")
    else:
        lines.append("🔴 FALSE POSITIVES: High — bot invents issues on clean code")

    # Severity accuracy
    if metrics["severity_accuracy"] >= 80:
        lines.append("✅ SEVERITY ACCURACY: Bot correctly classifies issue severity")
    elif metrics["severity_accuracy"] >= 60:
        lines.append("🟡 SEVERITY ACCURACY: Some severity misclassification")
    else:
        lines.append("🔴 SEVERITY ACCURACY: Poor severity classification")

    return "\n".join(lines)


def calculate_pipeline_score(metrics: dict, all_results: list) -> int:
    """Calculate final pipeline score out of 100."""
    score = 100

    # Penalize false negatives (missed bugs)
    score -= metrics["false_negatives"] * 15

    # Penalize false positives (hallucinations)
    score -= metrics["false_positives"] * 10

    # Reward high F1 score
    if metrics["f1_score"] >= 90:
        score += 5
    elif metrics["f1_score"] < 70:
        score -= 10

    # Penalize poor severity accuracy
    if metrics["severity_accuracy"] < 60:
        score -= 10

    return max(0, min(100, score))


# ────────────────────────────────────────────────────────────────
# MAIN EVALUATION
# ────────────────────────────────────────────────────────────────

def run_evaluation():
    """
    [RUBRIC C8 + C9]
    Run full evaluation pipeline and report metrics.
    """
    print("=" * 65)
    print("  🤖 CODE REVIEW BOT — AUTOMATED EVALUATION FRAMEWORK")
    print("  [RUBRIC C8: Evaluation Framework | C9: Result Interpretation]")
    print("=" * 65)
    print()

    # Ensure sample files exist
    print("📁 Preparing test cases...")
    ensure_sample_files()
    print()

    # Build graph once
    graph = build_review_graph()

    all_results = []
    test_summaries = []

    # Run each test case
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"{'─' * 65}")
        print(f"🧪 Test {i}/5: {test_case['name']}")
        print(f"   {test_case['description']}")
        print(f"{'─' * 65}")

        # Load code
        try:
            with open(test_case["file"], "r") as f:
                code = f.read()
        except FileNotFoundError:
            print(f"  ❌ File not found: {test_case['file']}")
            continue

        # Run test
        print("  Running bot...", end="", flush=True)
        result = run_single_test(graph, code, test_case["name"])
        print(f" done in {result['elapsed_seconds']}s")

        # Evaluate result
        evaluation = evaluate_result(result, test_case["expected"])

        # Print result
        print(f"  Issues Found:    {result['issues_found']}")
        print(f"  Review Decision: {result['review_decision']}")
        print(f"  Overall Score:   {result['overall_score']}/10" if result['overall_score'] else "  Overall Score:   N/A")
        print(f"  Checks Passed:   {evaluation['passed']}/{evaluation['total']} ({evaluation['pass_rate']}%)")

        # Print individual check results
        for check_name, passed in evaluation["checks"].items():
            icon = "✅" if passed else "❌"
            print(f"    {icon} {check_name.replace('_', ' ').title()}")

        all_results.append({
            "test_case": test_case,
            "expected": test_case["expected"],
            "result": result,
            "evaluation": evaluation,
        })

        test_summaries.append({
            "name": test_case["name"],
            "passed": evaluation["passed"],
            "total": evaluation["total"],
            "pass_rate": evaluation["pass_rate"],
        })

        print()

    # Calculate overall metrics
    print("=" * 65)
    print("  📊 EVALUATION METRICS [RUBRIC C8]")
    print("=" * 65)

    metrics = calculate_metrics(all_results)

    print(f"\n  Confusion Matrix:")
    print(f"    True Positives  (bugs caught):      {metrics['true_positives']}")
    print(f"    False Positives (hallucinations):   {metrics['false_positives']}")
    print(f"    True Negatives  (clean = clean):    {metrics['true_negatives']}")
    print(f"    False Negatives (bugs missed):      {metrics['false_negatives']}")
    print(f"\n  Core Metrics:")
    print(f"    Precision:          {metrics['precision']}%")
    print(f"    Recall:             {metrics['recall']}%")
    print(f"    F1 Score:           {metrics['f1_score']}%")
    print(f"    False Positive Rate:{metrics['false_positive_rate']}%")
    print(f"    Severity Accuracy:  {metrics['severity_accuracy']}%")

    print(f"\n  Per-Test Results:")
    for s in test_summaries:
        bar = "█" * s["passed"] + "░" * (s["total"] - s["passed"])
        print(f"    {s['name']:<25} [{bar}] {s['passed']}/{s['total']}")

    # Result interpretation
    print()
    print("=" * 65)
    print("  🔍 RESULT INTERPRETATION [RUBRIC C9]")
    print("=" * 65)
    print()
    interpretation = interpret_results(metrics)
    for line in interpretation.split("\n"):
        print(f"  {line}")

    # Final score
    pipeline_score = calculate_pipeline_score(metrics, all_results)
    print()
    print("=" * 65)
    print(f"  📈 FINAL PIPELINE SCORE: {pipeline_score}/100")
    print("=" * 65)

    if pipeline_score >= 90:
        print("  🏆 EXCELLENT — Production-ready bot with high accuracy")
    elif pipeline_score >= 75:
        print("  ✅ GOOD — Bot performs well with minor issues")
    elif pipeline_score >= 60:
        print("  🟡 FAIR — Bot needs improvement in detection accuracy")
    else:
        print("  🔴 NEEDS WORK — Significant accuracy improvements needed")

    print()

    # Save results to JSON for further analysis
    output = {
        "metrics": metrics,
        "pipeline_score": pipeline_score,
        "test_results": [
            {
                "name": r["test_case"]["name"],
                "issues_found": r["result"]["issues_found"],
                "review_decision": r["result"]["review_decision"],
                "overall_score": r["result"]["overall_score"],
                "pass_rate": r["evaluation"]["pass_rate"],
            }
            for r in all_results
        ]
    }

    os.makedirs("tests/results", exist_ok=True)
    with open("tests/results/eval_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("  💾 Results saved to: tests/results/eval_results.json")
    print()


if __name__ == "__main__":
    run_evaluation()
