import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.security_scanner import SecurityScanner

def test_security_scanner_safe():
    code = """
import os
api_key = os.getenv("MY_API_KEY")
password = os.environ.get("DB_PASSWORD")
"""
    res = SecurityScanner.scan_code(code)
    assert res["safe"]
    assert len(res["findings"]) == 0

def test_security_scanner_unsafe_key():
    code = "openai_key = 'sk-proj-abcdefghijklmnopqrstuvwxyz1234567890abcdef'"
    res = SecurityScanner.scan_code(code)
    assert not res["safe"]
    assert any("OpenAI" in f for f in res["findings"])

def test_security_scanner_unsafe_password():
    code = "secret_key = \"super-secret-hardcoded-value-123456\""
    res = SecurityScanner.scan_code(code)
    assert not res["safe"]
    assert any("Assignment" in f for f in res["findings"])
