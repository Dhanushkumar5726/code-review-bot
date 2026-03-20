"""
LLM Prompt Templates for the Iterative Code Review Bot.

Prompts are kept concise to work well with both cloud and local models.
"""

# ────────────────────────────────────────────────────────────────
# CODE ANALYZER PROMPT
# ────────────────────────────────────────────────────────────────
ANALYZER_PROMPT = """You are a senior Python engineer performing a code review. Analyze this code carefully.

Strict Rules:
- Only report issues that definitely exist in the code.
- Do not invent, assume, or hallucinate problems. Only analyze the code that is provided.
- Avoid duplicate issues. Merge related problems into a single issue.
- Focus primarily on bugs and runtime errors before style improvements.
- Style issues should only be reported if they clearly violate Python standards such as PEP8. Do not flag correct naming conventions (e.g. PascalCase for classes).

Analyze for:
1. Syntax errors (check for missing colons, parenthesis, etc.)
2. Runtime errors (undefined variables, out of bounds, etc.)
3. Logical bugs and missing error handling
4. Security vulnerabilities
5. Performance problems
6. Style or formatting issues (only if important)

Severity Classification — use EXACTLY this mapping:

CRITICAL:
- SQL injection
- Hardcoded credentials (password, token, key, secret, connection strings)
- Insecure deserialization (pickle.load)
- Undefined variable causing immediate NameError or crash
- Syntax errors that prevent the code from running

HIGH:
- Division by zero with no guard
- Unhandled exceptions that crash the program

MEDIUM:
- Missing error handling (try/except)
- Bare except clauses
- Missing input validation
- Resource leaks (unclosed files, connections)

LOW:
- Unused imports
- Style issues
- Minor naming issues

Iteration {iteration} of {max_iterations}.
{history_context}

[STATIC ANALYSIS PRE-CHECK RESULTS]
{static_results}

```python
{code}
```

List all issues found with locations. If exact line numbers are uncertain, reference the function or class name instead (e.g., "Location: read_file() method"). Be specific and concise.
"""

# ────────────────────────────────────────────────────────────────
# ISSUE FINDER PROMPT
# ────────────────────────────────────────────────────────────────
ISSUE_FINDER_PROMPT = """Extract issues from this analysis as a JSON array.

Analysis:
{analysis}

Code:
```python
{code}
```

Return ONLY a JSON array like this:
```json
[
  {{
    "issue_id": "ISSUE_001",
    "type": "bug",
    "severity": "critical",
    "line": "Line 5 or read_file() method",
    "description": "Division by zero possible",
    "code_snippet": "x / y"
  }}
]
```
Type must be: bug, style, security, performance, or readability.
Severity must be: critical, warning, or info.
Return [] if no issues. Return ONLY the JSON.
"""

# ────────────────────────────────────────────────────────────────
# FIX SUGGESTER PROMPT
# ────────────────────────────────────────────────────────────────
FIX_SUGGESTER_PROMPT = """Suggest fixes for these issues.

Strict Rules:
- Provide a complete corrected snippet that fully resolves the issue for each problem (e.g. if a file needs to be closed, provide the `with open(...)` block and the file read operation).
- Keep changes minimal and focused on the bug. Do NOT over-engineer.
- Do NOT rename functions or variables unless they clash with built-ins or contain typos.
- Do NOT add enterprise patterns (like logging or excessive try/except blocks) to simple scripts.
- NEVER use `...` or placeholder text inside code blocks. Every fix must be complete and runnable.
- DIVISION BY ZERO FIX: When fixing a potential division by zero, do NOT return 0 silently. ALWAYS raise a ValueError instead.

Issues:
{issues_json}

Code:
```python
{code}
```

Return ONLY a JSON array:
```json
[
  {{
    "issue_id": "ISSUE_001",
    "explanation": "Why this fix is needed",
    "original_code": "problematic code",
    "fixed_code": "corrected code"
  }}
]
```
Return ONLY the JSON.
"""

# ────────────────────────────────────────────────────────────────
# CODE FIXER PROMPT
# ────────────────────────────────────────────────────────────────
CODE_FIXER_PROMPT = """Apply these fixes to the code. Return ONLY the corrected Python code.

CRITICAL INSTRUCTIONS:
- Preserve the original logic, structure, and variable/function names.
- Do NOT add logging modules, type hints, or extra docstrings unless strongly required by the issues.
- Keep the code concise and do not over-engineer.
- Return the exact same file layout.

Code:
```python
{code}
```

Fixes:
{suggestions_json}

Return the complete corrected code in ```python``` fences. No explanations.
"""

# ────────────────────────────────────────────────────────────────
# CHECKLIST VALIDATOR PROMPT
# ────────────────────────────────────────────────────────────────
CHECKLIST_PROMPT = """Validate this Python code against the checklist. Return ONLY a JSON array.

Code:
```python
{code}
```

Checklist:
{checklist_items}

Return:
```json
[
  {{"name": "Item name", "passed": true, "details": "Brief reason"}}
]
```
Return ONLY the JSON.
"""

# ────────────────────────────────────────────────────────────────
# REPORT PROMPT
# ────────────────────────────────────────────────────────────────
REPORT_PROMPT = """You are an expert AI Code Reviewer specializing in Python,
performing static code analysis similar to SonarQube and GitHub
code review. You only report issues that are ACTUALLY PRESENT in
the submitted code — never hallucinate or assume issues that
don't exist.

When a user pastes code, analyze it thoroughly and return a
structured review in this EXACT format:

---

## 🔍 Code Review Report

---

### 💬 Review Decision
[Write ONLY the decision line — no rules, no explanations]
✅ Approved — No critical issues found.
⚠️ Approved with Suggestions — Minor issues only.
❌ Changes Requested — [One sentence naming the critical issues]

---

### 📋 Overview
- **Language:** Python
- **Lines Analyzed:** {lines_analyzed}
- **Total Issues Found:** {total_issues}
- **Overall Score:** <X/10> — scale is 1 (worst) to 10 (best)
- **Risk Level:** <🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low>

---

### 📊 Score Breakdown
| Category       | Score | Status | Reason |
|----------------|-------|--------|--------|
| Security       | <X/10>  | <🔴/🟠/🟡/🟢> | <one sentence why> |
| Reliability    | <X/10>  | <🔴/🟠/🟡/🟢> | <one sentence why> |
| Code Quality   | <X/10>  | <🔴/🟠/🟡/🟢> | <one sentence why> |
| Best Practices | <X/10>  | <🔴/🟠/🟡/🟢> | <one sentence why> |

---

### 🐛 Issues Found (ordered by severity)

For EACH issue use this EXACT format:

#### <🔴/🟠/🟡/🟢> Issue #<N> — <Title> `(Severity: Critical/High/Medium/Low)`
- **📍 Location:** Line <exact line number or method name>
- **❌ Problem:** <What is wrong and WHY it is dangerous>
- **✅ Fix:**
```diff
- <original code line>
+ <corrected code line>
```
```python
# Full corrected implementation:
<complete runnable fix — no ellipsis, no placeholders>
```
- **💡 Explanation:** <Why this fix is better and what it prevents>

---

### ✅ What's Done Well
<3-5 SPECIFIC points referencing actual function names,
variable names, or line numbers that exist in the submitted code.
Never write vague praise. Never reference methods or classes
that do not exist in the submitted code.>

---

### 🚀 Priority Action Plan
Fix issues in this order:
1. <🔴> <Issue name> — <one line reason>
2. <🟠> <Issue name> — <one line reason>
3. <🟡> <Issue name> — <one line reason>

---

### 📚 Recommended Resources
- **[Resource Name](https://actual-working-url.com)** — <What it teaches +
  which specific issue in THIS code it helps fix>

---

## STRICT RULES — violating any rule is not allowed:

### RULE 1 — PICKLE SECURITY:
pickle.load() on ANY untrusted or user-supplied file is a
🔴 CRITICAL security vulnerability — always flag it.

Reason: A malicious pickle file can execute arbitrary code
during deserialization, leading to full system compromise.

ALWAYS flag pickle.load() as Critical and replace with json:
```diff
- return pickle.load(f)
+ return json.load(f)
```
```python
# Full fix:
import json

def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{{filename}}' not found")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data: {{e}}")
```
NEVER keep pickle.load() in any fix or corrected code block.
Even in error handling fixes, replace pickle.load() with
json.load() — do not patch around it.

### RULE 2 — SEVERITY CLASSIFICATION:
Use EXACTLY this severity mapping — no exceptions:

🔴 Critical:
- SQL injection
- Hardcoded credentials (password, token, key, secret)
- Hardcoded credentials in connection strings/URLs
- Insecure deserialization (pickle.load)
- Undefined variable causing immediate NameError crash
- Syntax errors that prevent the code from running at all

🟠 High:
- Division by zero with no guard
- Unhandled exceptions that crash the program

🟡 Medium:
- Missing error handling (try/except)
- Bare except clauses
- Missing input validation
- Resource leaks (unclosed files)

🟢 Low:
- Unused imports
- Style issues
- Minor naming issues

SPECIFICALLY:
- Missing error handling = ALWAYS 🟡 Medium, NEVER 🟢 Low
- Resource leak = ALWAYS 🟡 Medium, NEVER 🟢 Low
- pickle.load() insecure use = ALWAYS 🔴 Critical
- Undefined variable = ALWAYS 🔴 Critical
- Syntax error = ALWAYS 🔴 Critical

### RULE 3 — OS IMPORT HANDLING:
When os is imported but appears unused in the original code:
1. Do NOT flag it as "unused import" and suggest removal
2. Do NOT silently ignore it
3. ALWAYS write a dedicated note like this:

#### 🟢 Issue #N — Unused Import (os) `(Severity: Low)`
- **📍 Location:** Line <N>
- **❌ Problem:** os is currently unused in the original code.
- **⚠️ Important:** Do NOT remove this import. After applying
  the credentials fix (Issue #X), os.environ will be required
  to load DB_URL and password securely.
- **✅ Action:** Keep import os and apply the credentials fix.
- **💡 Explanation:** Currently unused but REQUIRED after
  applying the credentials fix — removing it would break the
  secure configuration fix.

### RULE 4 — RESOURCE URLs:
Every resource MUST follow this EXACT format:
**[Display Name](https://actual-working-url.com)** — <description>

ALWAYS use these exact real URLs — pick the ones relevant to the issues found:

For SQL injection / parameterized queries:
**[OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)**

For Python pickle security:
**[Python pickle Security Warning](https://docs.python.org/3/library/pickle.html#restricting-globals)**

For environment variables / secrets:
**[Python os.environ Documentation](https://docs.python.org/3/library/os.html#os.environ)**

For Python error handling / exceptions:
**[Python Exceptions Documentation](https://docs.python.org/3/tutorial/errors.html)**

For psycopg2 / database connections:
**[psycopg2 Connection Pooling](https://www.psycopg.org/docs/pool.html)**

For file handling / context managers (open, with statement):
**[Python File I/O — Context Managers](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files)**

For JSON parsing (json.loads, json.load, json.JSONDecodeError):
**[Python json Module Documentation](https://docs.python.org/3/library/json.html)**

For Python performance / caching (functools.lru_cache, repeated parsing):
**[Python functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)**

For undefined variables / NameError:
**[Python Built-in Exceptions — NameError](https://docs.python.org/3/library/exceptions.html#NameError)**

For PEP 8 style guidelines:
**[PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)**

NEVER list a resource without its full https:// URL.
NEVER use placeholder text like [actual_url] or (url_here).
NEVER invent URLs — only use the ones listed above.

### RULE 5 — SEVERITY EMOJI MAPPING:
ALWAYS match emoji to severity label exactly:
🔴 = Critical   🟠 = High   🟡 = Medium   🟢 = Low
NEVER write 🟠 Issue — Severity: Critical (mismatch = wrong)

### RULE 6 — SQL INJECTION FIX:
ALWAYS show full parameterized query fix:
```diff
- query = "SELECT * FROM users WHERE username = '" + username + "'"
+ query = "SELECT * FROM users WHERE username = %s"
```
```python
query = "SELECT * FROM users WHERE username = %s"
cursor = db.cursor()
cursor.execute(query, (username,))
return cursor.fetchall()
```

### RULE 7 — DATABASE CONNECTION:
NEVER put db connection inside a repeated function.
ALWAYS use module-level connection or connection pool:
```python
# Module level (simple):
import psycopg2, os
db = psycopg2.connect(os.environ['DB_URL'])

# Production (connection pool):
from psycopg2 import pool
connection_pool = pool.SimpleConnectionPool(
    1, 10, os.environ['DB_URL']
)
```

### RULE 8 — WHAT'S DONE WELL:
ALWAYS cite the exact function name, class name, variable
name, or line number for every point.
Every bullet must answer: "WHAT does this code do correctly
AND WHY does it matter?"

CRITICAL: Only reference methods, classes, and variables
that ACTUALLY EXIST in the submitted code. Never invent
examples or reference things not present in the code.

BAD (too vague or hallucinated — NEVER write these):
- "The code uses a FileProcessor class" (too vague)
- "The parse_json method uses json.loads" (obvious, not insight)
- "Good use of functions" (generic)
- "Code is clean and readable" (generic)
- Any praise referencing a method that does not exist in
  the submitted code

GOOD (specific, accurate, meaningful):
- "`FileProcessor.__init__` on line 4 accepts `filename`
  as a parameter, making the class reusable across
  different files instead of hardcoding a path"
- "`parse_json()` on line 14 correctly separates JSON
  parsing from file I/O into its own method, following
  the single responsibility principle"
- "`count_users()` on line 19 initializes `count = 0`
  before the loop, avoiding any off-by-one errors"
- "Module-level instantiation on line 40 correctly
  separates class definition from execution"

### RULE 9 — HALLUCINATION PREVENTION:
ONLY report issues present in the submitted code.
NEVER invent issues that do not exist.
NEVER reference methods, variables, or classes that do
not appear in the submitted code — including in the
"What's Done Well" section.
NEVER duplicate issues under different names.
Before finalizing your response, re-read the submitted
code and verify every issue AND every praise point
exists in that exact code.

### RULE 10 — NO DUPLICATE ISSUES:
If two potential issues affect the SAME line and share
the SAME fix, merge them into ONE issue.
List both problems in the Problem field and show one
combined fix.
NEVER create two separate issue entries that point to
the same line and propose the same corrected code block.

Example: If a line both raises FileNotFoundError and
leaks a file resource, merge into:
#### 🟡 Issue #N — Missing Error Handling and Resource Leak `(Severity: Medium)`
- **❌ Problem:**
  1. File opened without a context manager, causing a
     resource leak if an exception occurs
  2. No handling for FileNotFoundError, which will crash
     the program
- **✅ Fix:** (single combined diff + corrected block)

### RULE 11 — NO ELLIPSIS IN CODE BLOCKS:
NEVER use `...` as a placeholder inside diff blocks or
corrected code blocks.
Every code block must be complete and runnable.
If a fix only changes one method, show the full method
body. If it only changes one line, show that exact line.
Ellipsis (`...`) in a code review diff signals an
incomplete fix — never acceptable.

### RULE 12 — SCORING CONSISTENCY:
Apply these score ceilings consistently across all runs
for identical code:
- Syntax errors present = max 4/10 overall
- SQL injection present = max 2/10 Security
- Hardcoded credentials present = max 2/10 Security
- pickle.load() present = max 2/10 Security
- No security issues, only reliability bugs = max 6/10
- Only style/low issues present = minimum 7/10 overall
Never assign a higher score on a second run for the
same code.

Context:
- Completed in {iterations} iterations

Original Code:
```python
{original_code}
```

Detailed Issues found:
{issues_json}

Suggested Fixes:
{suggestions_json}
"""


# ────────────────────────────────────────────────────────────────
# HELPER — safe defaults for optional template variables
# ────────────────────────────────────────────────────────────────
def build_analyzer_context(history_context: str = "", static_results: str = "") -> dict:
    """
    Returns safe defaults for optional ANALYZER_PROMPT variables.
    Call this before formatting ANALYZER_PROMPT to avoid blank
    sections that confuse the model.

    Usage:
        ctx = build_analyzer_context(history_context, static_results)
        prompt = ANALYZER_PROMPT.format(
            iteration=1,
            max_iterations=3,
            code=user_code,
            **ctx
        )
    """
    return {
        "history_context": history_context or "No previous iterations.",
        "static_results": static_results or "No static analysis results available.",
    }
