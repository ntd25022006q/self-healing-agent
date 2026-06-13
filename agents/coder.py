from agents.base import BaseAgent


class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__("Coder", "Software engineer who writes code and complete test suites.")

    def write_code(self, task_desc: str, plan_text: str, current_code: str = "", default_filename: str | None = None) -> dict:
        """
        Generates the implementation file and its corresponding unit tests.
        """
        print("[Coder] Writing code and unit tests...")

        system_prompt = """
You are an expert Python Software Engineer. Write complete, high-quality, and optimized code.
Rules:
1. Do NOT write any placeholders, dummy values, stub return values (like return "mock"), ellipsis stubs (...), or comments like '# TODO' / '# FIXME'.
2. Write complete execution logic. Every single function/class must be fully implemented. Doing otherwise will trigger AST validation failures and you will be penalized. Do not truncate code or leave functions incomplete.
3. You must write both the core implementation file AND a corresponding pytest test file.
4. The test file must have comprehensive test cases covering normal flows and edge cases. Do not truncate the test suite.
5. Code must be OS-independent (use os.path or pathlib for path management).
6. Return code blocks separated by markdown headers.
7. CORRECT MODULE IMPORTS: When writing the test file, you MUST import the code from the implementation file correctly. For example, if the implementation file is named `matrix.py`, you must use `import matrix` or `from matrix import ...`. Do not guess incorrect module names.
8. STRICT ANTI-TRUNCATION: NEVER use ellipsis (...), placeholder comments like "# (rest of code remains the same)", or truncate any data strings/lists in the implementation or test files. You must output 100% of the code in full. Failure to do so will corrupt the project files.
"""

        name_instruction = f"If creating a new file, the implementation file name MUST be: {default_filename}\n" if default_filename else ""

        user_prompt = f"""
Task: {task_desc}

Architectural Plan:
{plan_text}

{name_instruction}
Current Code (if modifying):
{current_code if current_code else "None"}

Please output your response exactly in this format (use code blocks):

IMPLEMENTATION:
```python
# [file_name]
# Write complete python code here
```

TEST:
```python
# [test_file_name]
# Write complete pytest suite here (importing the implementation file)
```
"""

        response = self.generate(system_prompt, user_prompt, temperature=0.1)

        # Parse the files out of the markdown output using semantic parser
        implementation_file = default_filename if default_filename else "app.py"
        if default_filename:
            base_name = default_filename.rsplit(".", 1)[0]
            test_file = f"test_{base_name}.py"
        else:
            test_file = "test_app.py"

        from tools.ast_tools import ASTTools
        implementation_code, test_code = ASTTools.parse_code_blocks(response, implementation_file, test_file)

        # Try to guess filenames from first line comments
        import re
        if implementation_code:
            first_line = implementation_code.splitlines()[0] if implementation_code else ""
            match = re.search(r"#\s*([\w\-\.]+)", first_line)
            if match:
                implementation_file = match.group(1)

        if test_code:
            first_line = test_code.splitlines()[0] if test_code else ""
            match = re.search(r"#\s*([\w\-\.]+)", first_line)
            if match and match.group(1) != implementation_file:
                test_file = match.group(1)
            else:
                base_name = implementation_file.rsplit(".", 1)[0]
                test_file = f"test_{base_name}.py"

        return {
            "raw_response": response,
            "implementation_file": implementation_file,
            "implementation_code": implementation_code,
            "test_file": test_file,
            "test_code": test_code
        }


if __name__ == "__main__":
    coder = CoderAgent()
    res = coder.write_code(
        "Calculate factorial",
        "PLAN:\n- File: math_ops.py (CREATE)\n  - Purpose: Factorial function\n- File: test_math_ops.py (CREATE)"
    )
    print("Impl File:", res["implementation_file"])
    print("Impl Code:\n", res["implementation_code"])
    print("Test File:", res["test_file"])
    print("Test Code:\n", res["test_code"])
