"""
Report Validator Node.

A second-pass LLM call + programmatic post-processing that
validates the generated report and fixes all violations before
returning the final output to the user.

TWO-PASS ARCHITECTURE:
  Pass 1 — LLM validation (report_generator output → corrected draft)
    Fixes: Review Decision, severity labels, duplicate issues,
           What's Done Well, missing security issues (MD5, all
           hardcoded credentials), os import contradictions,
           ellipsis in code blocks.

  Pass 2 — Programmatic post-processing (corrected draft → final)
    Fixes: Missing URLs (guaranteed — no LLM), excess resources
           (trimmed to max 5).
    This bypasses the LLM entirely for URLs since the LLM has
    consistently failed to add them despite 10+ rounds of prompting.

Plug into graph.py:
  report_generator → report_validator → END
"""

import re
from src.state import ReviewState  # pyre-ignore
from src.llm_utils import create_llm, invoke_with_retry  # pyre-ignore


# ────────────────────────────────────────────────────────────────
# VALIDATOR PROMPT — LLM Pass 1
# ────────────────────────────────────────────────────────────────

VALIDATOR_PROMPT = """You are a strict code review auditor.
You are given a DRAFT code review report.
Your job is to find ALL violations and return the CORRECTED report.
Do NOT explain what you changed. Just return the fixed report.

---

## VIOLATION CHECKS — fix every violation you find:

---

### CHECK 1 — REVIEW DECISION
Scan every issue in the report.
Count how many are 🔴 Critical or 🟠 High severity.

RULE — apply exactly:
- ANY 🔴 or 🟠 issue exists → Decision MUST be:
  ❌ Changes Requested — [one sentence naming the issues]
- ALL issues are 🟡 or 🟢 ONLY → Decision MUST be:
  ⚠️ Approved with Suggestions — Minor issues only.
- ZERO issues found → Decision MUST be:
  ✅ Approved — No critical issues found.

Fix the Review Decision if it does not match the issues.

---

### CHECK 2 — SEVERITY CLASSIFICATION
For every issue, verify the emoji matches the severity label
AND the severity is correctly classified:

CORRECT MAPPING:
  🔴 Critical: SQL injection, hardcoded credentials,
               pickle.load(), undefined variable (NameError),
               syntax error, weak password hashing (MD5/SHA1)
  🟠 High:     Division by zero (no guard),
               bare except clause hiding crashes,
               unhandled exception that crashes the program
  🟡 Medium:   Missing error handling (try/except),
               resource leak (unclosed file/connection),
               missing input validation
  🟢 Low:      Unused imports, style issues, minor naming

SPECIFIC FIXES TO APPLY:
- 🟠 Issue ... Severity: Critical → fix emoji to 🔴
- 🔴 Issue ... Severity: High → fix emoji to 🟠
- Division by zero marked Medium → upgrade to 🟠 High
- Bare except marked Medium → upgrade to 🟠 High
- Resource leak marked High → downgrade to 🟡 Medium
- Missing error handling marked High → downgrade to 🟡 Medium
- SQL injection marked Medium or High → upgrade to 🔴 Critical
- Undefined variable marked Medium or High → upgrade to 🔴 Critical
- MD5/SHA1 password hashing marked any level → upgrade to 🔴 Critical

---

### CHECK 3 — RESOURCE COUNT
Count the items in Recommended Resources.
If there are MORE than 5 → keep only the 3-5 most relevant
to the actual issues found. Remove the rest.
NEVER output more than 5 resources.

---

### CHECK 4 — OVERALL SCORE
Verify the Overall Score matches the code quality:

SCORE CEILINGS — apply exactly:
- ANY syntax error present → max 4/10 overall
- SQL injection present → max 2/10 for Security category
- Hardcoded credentials present → max 2/10 for Security category
- pickle.load() present → max 2/10 for Security category
- No security issues + reliability bugs only → max 6/10 overall
- Only style/low severity issues → minimum 7/10 overall

If the score is too high, lower it to match the ceiling.
If the score is too low for clean code, raise it to the minimum.

---

### CHECK 5 — DUPLICATE ISSUES
Scan for duplicate issues:
- If two issues point to the SAME line/method AND describe
  the SAME problem → they MUST be merged into ONE issue
- Keep the HIGHER severity when merging
- Example: MD5 flagged twice as Issue #4 and Issue #6
  → merge into one issue, keep 🔴 Critical

Remove any duplicate and merge into one combined issue.

---

### CHECK 6 — WHAT'S DONE WELL
Every bullet in What's Done Well must:
1. Name a specific function, class, or line number
2. Explain WHY it is good (not just WHAT it does)
3. Reference something that ACTUALLY EXISTS in the
   ORIGINAL submitted code — not in the fix suggestions

BANNED bullets (rewrite these):
  ❌ "The code is well-structured and easy to understand"
  ❌ "Good use of functions"
  ❌ "The X method is simple and effective"
  ❌ "The code is generally clean and readable"
  ❌ Praising a fix that doesn't exist in the original code
     (e.g., "uses parameterized queries" when original uses
     string concatenation)
  ❌ Any bullet that could apply to ANY Python code

REQUIRED format:
  ✅ "`function_name()` on line N does X, which prevents Y"
  ✅ "`ClassName.__init__` on line N accepts Z as parameter,
      making the class reusable without hardcoding"

Rewrite any vague or inaccurate bullets to be specific
and truthful about the ORIGINAL code.

---

### CHECK 7 — NO ELLIPSIS IN CODE BLOCKS
Scan every code block (diff and python blocks).
If any block contains `...` as a placeholder → rewrite
that block to be complete and runnable.
NEVER leave `...` in any code block.

---

### CHECK 8 — ALL HARDCODED CREDENTIALS FLAGGED
Scan the original code section for ALL credential patterns:
  SECRET_KEY = "..."
  ADMIN_PASSWORD = "..."
  API_KEY = "..."
  DB_PASSWORD = "..."
  TOKEN = "..."
  password = "..."

Each one MUST be a separate 🔴 Critical issue.
If the report only flags one but the code has two or more →
add the missing ones as new 🔴 Critical issues.

---

### CHECK 9 — WEAK HASHING FLAGGED
If the original code uses hashlib.md5() or hashlib.sha1()
for password hashing AND this is not flagged → add:

🔴 Issue #N — Weak Password Hashing (Severity: Critical)
📍 Location: [line where md5/sha1 is used]
❌ Problem: MD5 and SHA1 are cryptographically broken for
   password hashing. Vulnerable to rainbow table attacks.
   Use bcrypt, argon2, or hashlib.pbkdf2_hmac instead.
✅ Fix:
```diff
- hashed = hashlib.md5(password.encode()).hexdigest()
+ import bcrypt
+ hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```
```python
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

If it IS already flagged → verify it is 🔴 Critical.
If it is duplicated (flagged twice) → merge into one issue.

---

### CHECK 10 — OS IMPORT CONTRADICTION
If one issue says "remove import os" AND another issue
says "use os.environ for credentials" → fix the
remove-os issue to say instead:
  "Currently unused but REQUIRED after applying the
   credentials fix — do not remove this import."

NEVER tell the user to remove an import in one issue
and add it back in another.

---

### CHECK 11 — HALLUCINATED ISSUES
For every issue, verify it references something that
ACTUALLY EXISTS in the submitted code.

DELETE any issue where:
  - Location says "None" or "Not specified"
  - The problem describes code that is not in the submission
  - It is a theoretical "what if" rather than an actual bug
  - It describes a bare except clause when no except exists

Only keep issues that can be verified in the code.

---

## INPUT — DRAFT REPORT TO VALIDATE:

{draft_report}

---

## OUTPUT
Return the CORRECTED report in full.
Do NOT add any preamble like "Here is the corrected report".
Do NOT add any postamble like "I fixed X violations".
Start your response directly with:
## 🔍 Code Review Report
"""


# ────────────────────────────────────────────────────────────────
# URL LOOKUP TABLE
# Master map of resource keywords → real URLs
# Used by inject_urls() for programmatic URL injection
# ────────────────────────────────────────────────────────────────

URL_TABLE = {
    # SQL injection
    "owasp sql injection":           "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    "sql injection prevention":      "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    "sql injection":                 "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    # Pickle
    "pickle security":               "https://docs.python.org/3/library/pickle.html#restricting-globals",
    "pickle warning":                "https://docs.python.org/3/library/pickle.html#restricting-globals",
    "pickle":                        "https://docs.python.org/3/library/pickle.html#restricting-globals",
    # Secrets / environment variables
    "os.environ":                    "https://docs.python.org/3/library/os.html#os.environ",
    "environment variable":          "https://docs.python.org/3/library/os.html#os.environ",
    "secrets":                       "https://docs.python.org/3/library/os.html#os.environ",
    "hardcoded credential":          "https://docs.python.org/3/library/os.html#os.environ",
    # Exceptions / error handling — broad matches
    "python exceptions":             "https://docs.python.org/3/tutorial/errors.html",
    "exceptions documentation":      "https://docs.python.org/3/tutorial/errors.html",
    "error handling in python":      "https://docs.python.org/3/tutorial/errors.html",
    "error handling":                "https://docs.python.org/3/tutorial/errors.html",
    "exception handling":            "https://docs.python.org/3/tutorial/errors.html",
    "exception":                     "https://docs.python.org/3/tutorial/errors.html",
    "zerodivisionerror":             "https://docs.python.org/3/tutorial/errors.html",
    "valueerror":                    "https://docs.python.org/3/tutorial/errors.html",
    # File handling
    "file i/o":                      "https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files",
    "context manager":               "https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files",
    "file handling":                 "https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files",
    "reading and writing":           "https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files",
    # JSON
    "json module":                   "https://docs.python.org/3/library/json.html",
    "json parsing":                  "https://docs.python.org/3/library/json.html",
    "json documentation":            "https://docs.python.org/3/library/json.html",
    # PEP 8 — broad matches
    "pep 8":                         "https://peps.python.org/pep-0008/",
    "style guide for python":        "https://peps.python.org/pep-0008/",
    "style guide":                   "https://peps.python.org/pep-0008/",
    "python best practices":         "https://peps.python.org/pep-0008/",
    "best practices":                "https://peps.python.org/pep-0008/",
    "code review guidelines":        "https://peps.python.org/pep-0008/",
    "coding standards":              "https://peps.python.org/pep-0008/",
    # Python official docs — generic fallback for vague resource names
    "python official documentation": "https://docs.python.org/3/",
    "python documentation":          "https://docs.python.org/3/",
    "official documentation":        "https://docs.python.org/3/",
    "python standard library":       "https://docs.python.org/3/library/",
    # Database
    "psycopg2":                      "https://www.psycopg.org/docs/pool.html",
    "connection pool":               "https://www.psycopg.org/docs/pool.html",
    "sqlite3":                       "https://docs.python.org/3/library/sqlite3.html",
    "sqlite":                        "https://docs.python.org/3/library/sqlite3.html",
    # NameError
    "nameerror":                     "https://docs.python.org/3/library/exceptions.html#NameError",
    "undefined variable":            "https://docs.python.org/3/library/exceptions.html#NameError",
    # Caching
    "lru_cache":                     "https://docs.python.org/3/library/functools.html#functools.lru_cache",
    "caching":                       "https://docs.python.org/3/library/functools.html#functools.lru_cache",
    # Password hashing
    "hashlib":                       "https://docs.python.org/3/library/hashlib.html",
    "password hashing":              "https://docs.python.org/3/library/hashlib.html",
    "weak password":                 "https://docs.python.org/3/library/hashlib.html",
    "bcrypt":                        "https://pypi.org/project/bcrypt/",
    "md5":                           "https://docs.python.org/3/library/hashlib.html",
    "sha1":                          "https://docs.python.org/3/library/hashlib.html",
}


# ────────────────────────────────────────────────────────────────
# PROGRAMMATIC POST-PROCESSORS — Pass 2
# These functions bypass the LLM entirely for guaranteed fixes
# ────────────────────────────────────────────────────────────────

def _split_resources_section(report: str) -> "tuple[str, str, str]":
    """
    Split report into three parts around the Resources section.
    Returns (before, resources_content, after) tuple.
    All three parts are guaranteed str to satisfy Pyre2.
    """
    if "Recommended Resources" not in report:
        return str(report), "", ""

    parts: "list[str]" = report.split("Recommended Resources", 1)
    before: str = str(parts[0]) + "Recommended Resources"
    resources_section: str = str(parts[1])

    next_section_match = re.search(r'\n#{1,3} ', resources_section)
    if next_section_match:
        split_idx: int = next_section_match.start()
        resources_content: str = resources_section[:split_idx]
        after_resources: str = resources_section[split_idx:]
    else:
        resources_content = resources_section
        after_resources = ""

    return before, resources_content, after_resources


def inject_urls(report: str) -> str:
    """
    Programmatically inject missing URLs into Recommended Resources.

    For each resource line that has no https:// URL:
    1. Match the line text against URL_TABLE keywords
    2. Inject the matched URL into markdown link format
    3. Return the corrected report

    This guarantees URLs are always present — no LLM needed.
    """
    before, resources_content, after_resources = _split_resources_section(report)
    if not resources_content:
        return report

    fixed_lines: "list[str]" = []
    for line in str(resources_content).split("\n"):
        stripped: str = line.strip()

        # Only process resource list items
        if not (stripped.startswith("-") or stripped.startswith("*")):
            fixed_lines.append(line)
            continue

        # URL already present — leave as-is
        if "https://" in str(line) or "http://" in str(line):
            fixed_lines.append(line)
            continue

        # Find best matching URL from table
        line_lower: str = line.lower()
        matched_url: "str | None" = None
        for keyword, url in URL_TABLE.items():
            if keyword in str(line_lower):
                matched_url = url
                break

        if matched_url is not None:
            matched_url_str: str = str(matched_url)
            # Case 1: Has [Name](url) already — leave as-is (caught above)
            # Case 2: Has [Name] format without URL → insert URL
            md_link_no_url = re.search(r'\[([^\]]+)\](?!\()', line)
            if md_link_no_url:
                name: str = str(md_link_no_url.group(1))
                line = str(line).replace(
                    f"[{name}]",
                    f"[{name}]({matched_url_str})"
                )
            else:
                # Case 3: Has __bold__ format → convert to [Name](url)
                bold_match = re.search(r'__([^_]+)__', line)
                if bold_match:
                    bold_name: str = str(bold_match.group(1)).strip()
                    desc_match = re.search(
                        r'__[^_]+__\s*[—\-]+\s*(.+)', line
                    )
                    bold_desc: str = str(desc_match.group(1)).strip() if desc_match else ""
                    bullet: str = "*" if line.strip().startswith("*") else "-"
                    if bold_desc:
                        line = f"  {bullet} **[{bold_name}]({matched_url_str})** — {bold_desc}"
                    else:
                        line = f"  {bullet} **[{bold_name}]({matched_url_str})**"
                else:
                    # Case 4: Plain text → split on em-dash or dash
                    found_sep: bool = False
                    for sep in [" — ", " - ", "—"]:
                        if sep in str(line):
                            sep_parts: "list[str]" = str(line).split(sep, 1)
                            raw_name: str = str(sep_parts[0])
                            plain_desc: str = str(sep_parts[1]).strip() if len(sep_parts) > 1 else ""
                            clean_name: str = re.sub(
                                r'^[\s\-\*]+\*{0,2}', '', raw_name
                            ).strip().rstrip("*").strip()
                            plain_bullet: str = "*" if line.strip().startswith("*") else "-"
                            if plain_desc:
                                line = f"  {plain_bullet} **[{clean_name}]({matched_url_str})** — {plain_desc}"
                            else:
                                line = f"  {plain_bullet} **[{clean_name}]({matched_url_str})**"
                            found_sep = True
                            break
                    if not found_sep:
                        # No separator — wrap whole name
                        name_match = re.search(
                            r'[-*]\s+\*{0,2}([^—\[(]+)', line
                        )
                        if name_match:
                            plain_name: str = str(name_match.group(1)).strip().rstrip("*").strip()
                            old_text: str = str(name_match.group(1))
                            line = str(line).replace(
                                old_text,
                                f"[{plain_name}]({matched_url_str}) ",
                                1
                            )

        fixed_lines.append(line)

    return str(before) + "\n".join(fixed_lines) + str(after_resources)


def trim_resources(report: str, max_resources: int = 5) -> str:
    """
    Trim Recommended Resources to a maximum of max_resources items.
    Keeps only the first max_resources list items.
    Prevents the LLM from dumping all 14 URLs regardless of relevance.
    """
    before, resources_content, after_resources = _split_resources_section(report)
    if not resources_content:
        return report

    lines: "list[str]" = str(resources_content).split("\n")
    resource_count: int = 0
    trimmed_lines: "list[str]" = []

    for line in lines:
        stripped: str = line.strip()
        if stripped.startswith("-") or stripped.startswith("*"):
            resource_count = resource_count + 1
            if resource_count > max_resources:
                continue
        trimmed_lines.append(line)

    return str(before) + "\n".join(trimmed_lines) + str(after_resources)


# ────────────────────────────────────────────────────────────────
# VALIDATOR NODE
# ────────────────────────────────────────────────────────────────

def report_validator_node(state: ReviewState) -> dict:
    """
    Validate and correct the generated report using two passes.

    Pass 1 — LLM validation:
      Fixes Review Decision, severity labels, duplicate issues,
      What's Done Well accuracy, missing MD5/credential issues,
      os import contradiction, hallucinated issues, and ellipsis
      in code blocks.

    Pass 2 — Programmatic post-processing:
      - trim_resources: enforces max 5 resources
      - inject_urls: guarantees all resources have https:// URLs
      These bypass the LLM since it consistently failed this task.
    """
    draft_report = state.get("final_report", "")

    # If no report was generated, return as-is
    if not draft_report.strip():
        return {"final_report": draft_report}

    # ── Pass 1: LLM validation ────────────────────────────────
    llm = create_llm(temperature=0.0)
    prompt = VALIDATOR_PROMPT.format(draft_report=draft_report)
    response = invoke_with_retry(llm, prompt)
    corrected_report = response.content.strip()

    # Fallback: if LLM returns empty, keep the draft
    if not corrected_report:
        corrected_report = draft_report

    # ── Pass 2: Programmatic post-processing ──────────────────
    corrected_report = trim_resources(corrected_report, max_resources=5)
    corrected_report = inject_urls(corrected_report)

    return {"final_report": corrected_report}
