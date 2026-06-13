import os
from agents.base import BaseAgent
from tools.ast_tools import ASTTools
from tools.security_scanner import SecurityScanner
from tools.memory_db import MemoryDB
from config import Config


class VerifierAgent(BaseAgent):
    def __init__(self):
        super().__init__("Verifier",
                         "Code auditor who enforces code standards, security, and updates scores.")

    def verify(self, task_desc: str, code_file: str, code_content: str) -> dict:
        """
        Performs static analysis (AST, security patterns) and calls LLM to audit
        code quality, complexity, and safety. Updates and persists agent scores.
        """
        print(
            f"[Verifier] Auditing code quality and security for {code_file}...")

        violations = []
        score_change = 0

        # 1. AST Mock Check
        ast_result = ASTTools.detect_mocks_and_stubs(code_content)
        if ast_result["has_violations"]:
            violations.extend(ast_result["violations"])
            score_change -= 100  # Severe penalty for mock data / placeholder

        # 2. Secret Leak Scan
        sec_result = SecurityScanner.scan_code(code_content)
        if not sec_result["safe"]:
            violations.extend(sec_result["findings"])
            score_change -= 100  # Severe penalty for security leaks

        # 3. LLM Audit (Clean code, complexity, security check)
        system_prompt = """
You are a Senior Code Reviewer. Audit the provided code against strict enterprise standards.
Your output must be a strict JSON object with the following schema:
{
  "complexity_optimal": true/false,
  "complexity_explanation": "explanation of complexity check",
  "security_safe": true/false,
  "security_explanation": "explanation of security vulnerabilities (e.g. SQL Injection, unsafe shell execution)",
  "pep8_clean": true/false,
  "pep8_explanation": "explanation of PEP8 compliance and design pattern review"
}
Do not output any introductory or concluding text, only the raw JSON.
"""

        user_prompt = f"""
Task Description: {task_desc}

Code File: {code_file}
Code Content:
```python
{code_content}
```

Respond with only the strict JSON block.
"""

        audit_response = self.generate(
            system_prompt, user_prompt, temperature=0.1)

        # Parse audit response for penalties/rewards
        import re
        import json

        complexity_ok = True
        security_ok = True
        pep8_ok = True

        json_content = audit_response
        code_block_match = re.search(
            r"```(?:json)?\s*(.*?)\s*```", audit_response, re.DOTALL)
        if code_block_match:
            json_content = code_block_match.group(1)

        # Clean JSON from response
        clean_json = json_content.strip()
        clean_json = re.sub(r"^```(?:json)?", "", clean_json)
        clean_json = re.sub(r"```$", "", clean_json)
        clean_json = clean_json.strip()
        # Remove trailing commas in JSON object before parsing (common LLM syntax mistake)
        clean_json = re.sub(r",\s*([\]}])", r"\1", clean_json)

        try:
            audit_data = json.loads(clean_json)
            complexity_ok = bool(audit_data.get("complexity_optimal", True))
            security_ok = bool(audit_data.get("security_safe", True))
            pep8_ok = bool(audit_data.get("pep8_clean", True))
        except Exception:
            print(
                "[Verifier] Warning: Failed to parse LLM JSON audit. Falling back to robust regex value extraction.")
            # Fallback using specific key-value regexes
            comp_match = re.search(
                r"[\"']complexity_optimal[\"']\s*:\s*(true|false)", clean_json, re.IGNORECASE)
            sec_match = re.search(
                r"[\"']security_safe[\"']\s*:\s*(true|false)", clean_json, re.IGNORECASE)
            pep8_match = re.search(
                r"[\"']pep8_clean[\"']\s*:\s*(true|false)", clean_json, re.IGNORECASE)

            complexity_ok = comp_match.group(
                1).lower() == "true" if comp_match else True
            security_ok = sec_match.group(
                1).lower() == "true" if sec_match else True
            pep8_ok = pep8_match.group(
                1).lower() == "true" if pep8_match else True

        # Deduct or reward based on audit
        if not complexity_ok:
            violations.append("Algorithm/complexity is not optimal.")
            score_change -= 50
        else:
            score_change += 20

        if not security_ok:
            violations.append("Security risk detected by code auditor.")
            score_change -= 100
        else:
            score_change += 20

        if pep8_ok:
            score_change += 10

        # 4. Type Checking using Mypy (Static type analysis)
        try:
            from tools.code_executor import CodeExecutor
            pip_path = CodeExecutor.get_venv_pip()
            import subprocess
            # Ensure mypy is installed (run with 40s timeout)
            subprocess.run([pip_path, "install", "mypy"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40)

            bin_dir = CodeExecutor.get_venv_bin_dir()
            import platform
            mypy_executable = os.path.join(
                bin_dir, "mypy.exe" if platform.system() == "Windows" else "mypy")

            impl_path = os.path.join(Config.WORKSPACE_DIR, code_file)
            res = subprocess.run([mypy_executable, "--ignore-missing-imports",
                                 impl_path], capture_output=True, text=True, timeout=30)

            if res.returncode != 0:
                violations.append(f"Mypy type check warning:\n{res.stdout}")
                score_change -= 20
            else:
                score_change += 10
        except Exception as e:
            # If mypy fails to run or install, don't fail the verification
            print(f"[Verifier] Mypy check skipped or failed to run: {e}")

        # Limit total positive reward per verification run
        score_change = max(-300, min(100, score_change))

        # Update persistent DB score
        new_score = MemoryDB.update_agent_score(score_change)

        # Determine if the verification passed.
        # We only fail (and rollback) if there is a deterministic security leak (regex) or AST mock/stub violations.
        # LLM audit is subjective, so its violations only deduct score but do not fail the verification.
        ast_result = ASTTools.detect_mocks_and_stubs(code_content)
        sec_result = SecurityScanner.scan_code(code_content)
        passed = (not ast_result["has_violations"]) and sec_result["safe"]

        # Log results
        print(
            f"[Verifier] Verification finished. Passed: {passed}. Score change: {score_change}. New Score: {new_score}")
        if violations:
            print("[Verifier] Violations/Warnings found:")
            for v in violations:
                print(f" - {v}")

        return {
            "passed": passed,
            "violations": violations,
            "score_change": score_change,
            "new_score": new_score,
            "audit_details": audit_response
        }


if __name__ == "__main__":
    # Test verifier
    verifier = VerifierAgent()
    code = """
def calculate_factorial(n):
    # TODO: fix overflow
    if n == 0:
        return 1
    return n * calculate_factorial(n - 1)
"""
    res = verifier.verify("factorial", "math.py", code)
    print(res)
