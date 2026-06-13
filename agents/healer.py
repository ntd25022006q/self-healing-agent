from agents.base import BaseAgent
from tools.code_executor import CodeExecutor
import re


class HealerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Healer", "Specialist who diagnoses traceback logs and plans code repairs.")

    def heal_code(self, task_desc: str, code_file: str, current_code: str, test_file: str, current_test: str, traceback_log: str, temperature_override: float | None = None) -> dict:
        """
        Diagnoses compiler/runtime/logic errors, installs missing libraries if needed,
        and generates the corrected code.
        """
        print(f"[Healer] Diagnosing test failures for {code_file}...")

        # Step 1: Detect if the error is a ModuleNotFoundError (missing package)
        # We can handle this automatically without calling the LLM, saving 100% tokens for this error!
        missing_pkg_match = re.search(
            r"ModuleNotFoundError:\s*No\s*module\s*named\s*['\"]([\w\-]+)['\"]", traceback_log)
        if missing_pkg_match:
            pkg_name = missing_pkg_match.group(1)
            print(
                f"[Healer] Detected missing package: {pkg_name}. Initiating auto-installation...")
            install_result = CodeExecutor.install_package(pkg_name)

            if install_result.get("success", False):
                print(
                    f"[Healer] Successfully installed {pkg_name}. Conflict check: {install_result.get('conflict_check', '')}")
                # Tell the orchestrator to re-run the tests directly since we solved the dependency issue!
                return {
                    "auto_installed": True,
                    "package_installed": pkg_name,
                    "implementation_code": current_code,
                    "test_code": current_test,
                    "explanation": f"Auto-installed missing dependency '{pkg_name}' and verified compatibility."
                }
            else:
                print(
                    f"[Healer] Auto-installation of {pkg_name} failed: {install_result.get('error', '')}")

        # Add special warning for infinite loop / timeout errors
        if "timeout" in traceback_log.lower():
            traceback_log += "\n\nCRITICAL WARNING: The execution timed out. This means your code has an infinite loop or infinite recursion! Please inspect your loop exit conditions (e.g. while loops, recursion base cases) and ensure they are guaranteed to terminate under all inputs."

        # Step 2: Otherwise, call the LLM to fix the logic/syntax/import issue
        system_prompt = """
You are a Senior Debugging Engineer. Analyze the provided Python code, its corresponding tests, and the execution traceback.
Identify the root cause of the error (syntax error, missing import, logic bug, or incorrect API call).
Write the fully corrected version of the code.
Rules:
1. Do NOT write placeholders, dummy values, ellipsis stubs (...), or mock data. Write the complete, fixed implementation.
2. Write complete execution logic. Every single function/class must be fully implemented. Do not truncate functions or use comments as a shortcut.
3. Return both the corrected implementation file and the corrected test file.
4. Be platform-agnostic (ensure it runs correctly on Windows and Linux).
5. INCREMENTAL HEALING: Do not delete, refactor, or omit any existing functions or classes that are not related to the error. Retain all original helper methods, signatures, comments, and structure. Only edit the lines directly causing the bug.
6. CORRECT MODULE IMPORTS: When writing the test file, you MUST import the code from the implementation file correctly. For example, if the implementation file is named `matrix.py`, you must use `import matrix` or `from matrix import ...`. Do not guess incorrect module names.
7. STRICT ANTI-TRUNCATION: NEVER use ellipsis (...), placeholder comments like "# (rest of code remains the same)", or truncate any data strings/lists in the implementation or test files. You must output 100% of the code in full. Failure to do so will corrupt the project files.
"""

        user_prompt = f"""
Task: {task_desc}

Implementation File ({code_file}):
```python
{current_code}
```

Test File ({test_file}):
```python
{current_test}
```

Execution Error Log / Traceback:
{traceback_log}

Identify the bug and return the corrected files in this exact format (use code blocks):

IMPLEMENTATION:
```python
# [file_name]
# Write complete corrected python code here
```

TEST:
```python
# [test_file_name]
# Write complete corrected pytest suite here
```
"""

        temp = temperature_override if temperature_override is not None else 0.1
        response = self.generate(system_prompt, user_prompt, temperature=temp)
        # Log LLM response for developer diagnosis
        print(f"[Healer DEBUG] Raw LLM Response (first 1000 chars):\n{response[:1000]}\n" + "="*80)

        # Parse output files using semantic parser
        from tools.ast_tools import ASTTools
        implementation_code, test_code = ASTTools.parse_code_blocks(response, code_file, test_file)

        # Safety Defense: Reject updates to implementation file if the new code defines 0 functions/classes while the original did
        if implementation_code != current_code:
            orig_defs = len(re.findall(
                r"^\s*(def|class)\s+\w+", current_code, re.MULTILINE))
            new_defs = len(re.findall(r"^\s*(def|class)\s+\w+",
                           implementation_code, re.MULTILINE))
            if orig_defs > 0 and new_defs == 0:
                print(
                    f"[Healer] Rejected new implementation code because it contains 0 function/class definitions (Original had {orig_defs}). Avoiding file corruption.")
                implementation_code = current_code

        return {
            "auto_installed": False,
            "implementation_code": implementation_code,
            "test_code": test_code,
            "explanation": "Resolved coding/logical error from stack trace analysis."
        }


if __name__ == "__main__":
    healer = HealerAgent()
    # Mock test of auto-installer
    err = "ModuleNotFoundError: No module named 'requests'"
    res = healer.heal_code("Fetch rates", "api.py",
                           "pass", "test_api.py", "pass", err)
    print("Auto-installed:", res["auto_installed"])
    print("Explanation:", res["explanation"])
