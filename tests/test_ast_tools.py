import sys
import os

# Add parent directory to sys.path so we can import packages correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.ast_tools import ASTTools

def test_minify_code():
    code = """
def hello_world():
    \"\"\"This is a docstring\"\"\"
    # This is a comment
    print("Hello, World!")
"""
    minified = ASTTools.minify_code(code)
    assert "docstring" not in minified
    assert "comment" not in minified
    assert "Hello, World!" in minified

def test_detect_mocks_and_stubs():
    # Pass check
    code_pass = """
def empty_func():
    pass
"""
    res = ASTTools.detect_mocks_and_stubs(code_pass)
    assert res["has_violations"]
    assert any("pass" in v for v in res["violations"])

    # Ellipsis check
    code_ellipsis = """
def stub_func():
    ...
"""
    res = ASTTools.detect_mocks_and_stubs(code_ellipsis)
    assert res["has_violations"]
    assert any("ellipsis" in v for v in res["violations"])

    # TODO check
    code_todo = """
def do_something():
    # TODO: implement this
    return 42
"""
    res = ASTTools.detect_mocks_and_stubs(code_todo)
    assert res["has_violations"]
    assert any("TODO" in v for v in res["violations"])

    # Safe check
    code_safe = """
def add(a, b):
    return a + b
"""
    res = ASTTools.detect_mocks_and_stubs(code_safe)
    assert not res["has_violations"]
