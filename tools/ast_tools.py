import ast
import re


class ASTTools:
    @staticmethod
    def parse_code_blocks(response: str, impl_filename: str, test_filename: str) -> tuple[str, str]:
        """
        Parses markdown code blocks in raw LLM response and semantically classifies them
        into core implementation code and test code using file names, imports, and definitions.
        Returns:
            A tuple of (implementation_code, test_code).
        """
        import re
        
        # 1. Extract all python code blocks along with their preceding text
        blocks_with_preceding = []
        for m in re.finditer(r"```python\s*(.*?)\s*```", response, re.DOTALL):
            code_content = m.group(1)
            start_pos = m.start()
            preceding_text = response[max(0, start_pos - 300):start_pos].lower()
            blocks_with_preceding.append((preceding_text, code_content))
            
        if not blocks_with_preceding:
            return "", ""
            
        impl_code_candidates = []
        test_code_candidates = []
        
        impl_base = impl_filename.rsplit(".", 1)[0] if impl_filename else ""
        test_base = test_filename.rsplit(".", 1)[0] if test_filename else ""
        
        for preceding, code in blocks_with_preceding:
            score_impl = 0
            score_test = 0
            
            # Feature A: Preceding context text
            if any(kw in preceding for kw in ["implementation", "corrected implementation", "source code", "production code", "source"]):
                score_impl += 5
            if any(kw in preceding for kw in ["test", "pytest", "suite", "assertion", "unit test"]):
                score_test += 5
                
            # Feature B: First-line filename comment check
            first_line = code.splitlines()[0].strip() if code.strip() else ""
            if first_line.startswith("#"):
                comment_content = first_line[1:].strip().lower()
                if impl_filename.lower() in comment_content or (impl_base and impl_base.lower() in comment_content):
                    score_impl += 10
                if test_filename.lower() in comment_content or (test_base and test_base.lower() in comment_content):
                    score_test += 10
                    
            # Feature C: Pytest or test function markers inside code
            if "def test_" in code or "import pytest" in code or "@pytest." in code:
                score_test += 15
                
            # Feature D: Importing the implementation module
            if impl_base:
                import_pattern = rf"\b(import\s+{re.escape(impl_base)}|from\s+{re.escape(impl_base)}\s+import)\b"
                if re.search(import_pattern, code):
                    score_test += 15
                    
            # Feature E: Contains class or function definitions matching the target request
            defs = re.findall(r"^\s*(def|class)\s+(\w+)", code, re.MULTILINE)
            non_test_defs = [d for d in defs if not d[1].startswith("test_")]
            if non_test_defs:
                score_impl += 3
                
            # Classify based on score
            if score_impl > score_test:
                impl_code_candidates.append(code)
            elif score_test > score_impl:
                test_code_candidates.append(code)
            else:
                if "def test_" in code or "import pytest" in code:
                    test_code_candidates.append(code)
                else:
                    impl_code_candidates.append(code)
                    
        # Apply extracted code candidates with fallback to index-based matching
        implementation_code = ""
        test_code = ""
        
        all_blocks = [block[1] for block in blocks_with_preceding]
        
        if impl_code_candidates:
            implementation_code = impl_code_candidates[0]
        else:
            implementation_code = all_blocks[0]
            
        if test_code_candidates:
            test_code = test_code_candidates[0]
        elif len(all_blocks) >= 2:
            if all_blocks[0] == implementation_code:
                test_code = all_blocks[1]
            else:
                test_code = all_blocks[0]
        else:
            test_code = "def test_placeholder():\n    assert True\n"
            
        return implementation_code.strip(), test_code.strip()

    @staticmethod
    def minify_code(code_content: str) -> str:
        """
        Parses python code and strips out all docstrings, comments, and empty lines,
        reducing token footprint by 30-50% while preserving exact execution logic.
        """
        try:
            tree = ast.parse(code_content)

            # Walk the tree and remove docstrings from classes, functions, and module level
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                    if (node.body
                            and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)):
                        # Remove the docstring expr
                        node.body.pop(0)
                        if not node.body:
                            # Re-add a pass statement if body is empty after removing docstring
                            node.body.append(ast.Pass())

            # unparse is standard in Python 3.9+
            minified = ast.unparse(tree)
            return minified
        except Exception as e:
            print(
                f"[Warning] AST Minifier failed: {e}. Falling back to basic regex cleaning.")
            # Fallback basic regex cleaning (removes full line comments and blank lines)
            lines = code_content.splitlines()
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                cleaned_lines.append(line)
            return "\n".join(cleaned_lines)

    @staticmethod
    def detect_mocks_and_stubs(code_content: str) -> dict:
        """
        Scans code using AST and regex to find signs of lazy implementation:
        - 'pass' statements inside functional code.
        - Comments containing 'TODO', 'FIXME', or 'mock'.
        - Empty functions or dummy return values (e.g. return 'TODO', return 'mock').
        - Lazy ellipsis (...) anywhere in the code.
        """
        violations = []

        try:
            tree = ast.parse(code_content)

            for node in ast.walk(tree):
                # Check for Ellipsis anywhere in the AST
                if isinstance(node, ast.Constant) and node.value is Ellipsis:
                    violations.append("Found lazy ellipsis (...) stub in the code structure.")

                # Check for bare 'pass' statements or Ellipsis (...) inside functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check if body is just a pass or ellipsis
                    if len(node.body) == 1:
                        first_stmt = node.body[0]
                        if isinstance(first_stmt, ast.Pass):
                            violations.append(
                                f"Function '{node.name}' has empty implementation (pass).")
                        elif (
                            isinstance(first_stmt, ast.Expr)
                            and isinstance(first_stmt.value, ast.Constant)
                            and first_stmt.value.value is Ellipsis
                        ):
                            violations.append(
                                f"Function '{node.name}' has empty implementation (ellipsis ...).")

                    # Check for dummy return values
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and isinstance(child.value, ast.Constant):
                            val = str(child.value.value).lower()
                            if val in ["todo", "mock", "dummy", "placeholder", "test_data"]:
                                violations.append(
                                    f"Function '{node.name}' returns placeholder/mock value: {child.value.value!r}.")
        except Exception as e:
            violations.append(f"AST Parsing error during mock check: {e}")

        # Regex check for raw text comments (like # TODO or # FIXME) and lazy instructions
        comment_pattern = re.compile(
            r"#\s*(todo|fixme|mock|placeholder|dummy|write here|rest of|remains unchanged|same as|stays here|original code|etc|insert here)", re.IGNORECASE)
        lines = code_content.splitlines()
        for idx, line in enumerate(lines, 1):
            match = comment_pattern.search(line)
            if match:
                violations.append(
                    f"Line {idx}: Found placeholder comment '{line.strip()}'")

        return {
            "has_violations": len(violations) > 0,
            "violations": violations
        }


if __name__ == "__main__":
    test_code = """
'''
This is a module docstring
'''
def fetch_user_data(user_id):
    \"\"\"
    Fetch user data from database
    \"\"\"
    # TODO: implement database connection
    data = {"id": user_id, "name": "mock"}
    return "TODO" # return mock data

class DatabaseConnector:
    '''Class docstring'''
    def connect(self):
        pass
"""
    print("--- Original Code ---")
    print(test_code)

    print("--- Minified Code ---")
    minified = ASTTools.minify_code(test_code)
    print(minified)

    print("--- Mock Detection ---")
    chk = ASTTools.detect_mocks_and_stubs(test_code)
    print(chk)
