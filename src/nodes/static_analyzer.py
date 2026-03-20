"""
Static Analyzer Node.

Pre-processes the user's code using Python's built-in AST parser
and flake8 to detect definitive Syntax Errors and Runtime Errors
(like undefined variables) before handing it off to the LLM.
This drastically reduces hallucinations.
"""

import ast
import subprocess
import tempfile
import os

from src.state import ReviewState  # pyre-ignore


def static_analyzer_node(state: ReviewState) -> dict:
    """
    Run AST parsing and Flake8 on the code.
    Returns definitive, factual issues to inject into the LLM context.
    """
    code = state["current_code"]
    results = []

    # 1. AST Parsing for critical SyntaxErrors
    try:
        ast.parse(code)
    except SyntaxError as e:
        err_text = getattr(e, "text", "")
        clean_text = err_text.strip() if err_text else ""
        results.append(f"[CRITICAL] SyntaxError at line {e.lineno}: {e.msg}\n    {clean_text}")
        return {"static_analysis_results": "\n".join(results)}  # Stop immediately, code is totally broken

    # 2. Flake8 for static analysis (Undefined variables, etc)
    try:
        # Write code to a temp file to pass to flake8
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name

        # Run flake8. 
        # F821 = undefined name
        # F401 = imported but unused
        # E999 = SyntaxError
        cmd = ["flake8", temp_path, "--select=F821,F401,E999"]
        
        # We expect a non-zero exit code if issues are found
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.stdout:
            for line in process.stdout.strip().split("\n"):
                if not line:
                    continue
                # Line format: /temp/path.py:line:col: ERROR_CODE Message
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    line_no = parts[1]
                    err_msg = parts[3].strip()
                    results.append(f"[ERROR] Line {line_no}: {err_msg}")
                    
    except Exception as e:
        results.append(f"[SYSTEM] Static Analyzer Warning: {str(e)}")
    finally:
        # Cleanup temp file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    final_output = "\n".join(results)
    if not final_output:
        final_output = "No static analysis errors found."

    return {"static_analysis_results": final_output}
