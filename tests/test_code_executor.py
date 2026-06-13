import sys
import os
import platform

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.code_executor import CodeExecutor

def test_venv_paths():
    bin_dir = CodeExecutor.get_venv_bin_dir()
    python_path = CodeExecutor.get_venv_python()
    pip_path = CodeExecutor.get_venv_pip()
    
    assert "agent_env" in bin_dir
    assert "agent_env" in python_path
    assert "agent_env" in pip_path
    
    if platform.system() == "Windows":
        assert bin_dir.endswith("Scripts")
        assert python_path.endswith("python.exe")
        assert pip_path.endswith("pip.exe")
    else:
        assert bin_dir.endswith("bin")
        assert python_path.endswith("python")
        assert pip_path.endswith("pip")
