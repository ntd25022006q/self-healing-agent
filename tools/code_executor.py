import os
import sys
import subprocess
import platform
from config import Config


class CodeExecutor:
    ENV_DIR = os.path.join(Config.WORKSPACE_DIR, "agent_env")

    @classmethod
    def get_venv_bin_dir(cls) -> str:
        """
        Get the bin directory of the virtual environment depending on OS.
        """
        if platform.system() == "Windows":
            return os.path.join(cls.ENV_DIR, "Scripts")
        return os.path.join(cls.ENV_DIR, "bin")

    @classmethod
    def get_venv_python(cls) -> str:
        """
        Get path to python executable inside the virtualenv.
        """
        bin_dir = cls.get_venv_bin_dir()
        if platform.system() == "Windows":
            return os.path.join(bin_dir, "python.exe")
        return os.path.join(bin_dir, "python")

    @classmethod
    def get_venv_pip(cls) -> str:
        """
        Get path to pip executable inside the virtualenv.
        """
        bin_dir = cls.get_venv_bin_dir()
        if platform.system() == "Windows":
            return os.path.join(bin_dir, "pip.exe")
        return os.path.join(bin_dir, "pip")

    @classmethod
    def initialize_env(cls) -> bool:
        """
        Create the virtual environment if it doesn't already exist.
        """
        if not os.path.exists(cls.ENV_DIR):
            print(f"[CodeExecutor] Creating virtualenv at {cls.ENV_DIR}...")
            try:
                # Use current system python to create virtualenv
                subprocess.run([sys.executable, "-m", "venv",
                               cls.ENV_DIR], check=True, timeout=60)
                print("[CodeExecutor] Virtualenv created successfully.")

                # Upgrade pip inside environment
                pip_path = cls.get_venv_pip()
                subprocess.run([pip_path, "install", "--upgrade",
                               "pip"], check=True, timeout=60)

                # Pre-install parent workspace dependencies if requirements.txt exists
                req_path = os.path.join(
                    Config.WORKSPACE_DIR, "requirements.txt")
                if os.path.exists(req_path):
                    print(
                        f"[CodeExecutor] Pre-installing parent workspace dependencies from {req_path}...")
                    subprocess.run([pip_path, "install", "-r",
                                   req_path], check=True, timeout=120)
                return True
            except Exception as e:
                print(f"[CodeExecutor] Error initializing virtualenv: {e}")
                return False
        return True

    @classmethod
    def install_package(cls, package_name: str) -> dict:
        """
        Install a package inside the virtualenv, running 'pip check' afterward to verify dependency safety.
        """
        cls.initialize_env()
        pip_path = cls.get_venv_pip()

        # Prevent injection attacks
        # Only take the first token (package name)
        safe_pkg = package_name.strip().split()[0]

        print(f"[CodeExecutor] Installing package: {safe_pkg}...")
        try:
            result = subprocess.run(
                [pip_path, "install", safe_pkg],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return {"success": False, "error": result.stderr}

            # Run dependency conflict check
            check_result = subprocess.run(
                [pip_path, "check"],
                capture_output=True,
                text=True,
                timeout=30
            )

            is_conflicted = check_result.returncode != 0
            return {
                "success": True,
                "output": result.stdout,
                "conflict_check": check_result.stdout if is_conflicted else "No dependency conflicts found."
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Installation timed out."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def execute_script(cls, script_path: str, args: list | None = None, timeout: int | None = None) -> dict:
        """
        Execute a python script in the virtualenv sandbox with a strict timeout.
        """
        cls.initialize_env()
        python_path = cls.get_venv_python()

        if not os.path.exists(script_path):
            return {"success": False, "error": f"Script not found: {script_path}"}

        cmd = [python_path, script_path]
        if args:
            cmd.extend(args)

        exec_timeout = timeout if timeout is not None else Config.TIMEOUT_SECONDS
        try:
            print(
                f"[CodeExecutor] Running script: {' '.join(cmd)} (timeout={exec_timeout}s)")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                cwd=Config.WORKSPACE_DIR
            )

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out. Process exceeded {exec_timeout} seconds limit (potential infinite loop)."
            }
        except Exception as e:
            return {"success": False, "exit_code": -1, "stdout": "", "stderr": str(e)}

    @classmethod
    def run_tests(cls, test_file_path: str, timeout: int | None = None) -> dict:
        """
        Run pytest on a test file inside the virtualenv and capture the results.
        """
        cls.initialize_env()

        # Ensure pytest is installed inside virtualenv
        pip_path = cls.get_venv_pip()
        try:
            subprocess.run([pip_path, "install", "pytest"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        except Exception:
            pass

        bin_dir = cls.get_venv_bin_dir()
        pytest_path = os.path.join(
            bin_dir, "pytest.exe" if platform.system() == "Windows" else "pytest")

        if not os.path.exists(test_file_path):
            return {"success": False, "error": f"Test file not found: {test_file_path}"}

        cmd = [pytest_path, "-v", test_file_path]
        exec_timeout = timeout if timeout is not None else Config.TIMEOUT_SECONDS
        try:
            print(
                f"[CodeExecutor] Running pytest: {' '.join(cmd)} (timeout={exec_timeout}s)")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                cwd=Config.WORKSPACE_DIR
            )
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Pytest execution timed out. Process exceeded {exec_timeout} seconds limit."
            }
        except Exception as e:
            return {"success": False, "exit_code": -1, "stdout": "", "stderr": str(e)}


if __name__ == "__main__":
    # Test env creation
    print("Initializing environment...")
    CodeExecutor.initialize_env()
    print("Python interpreter:", CodeExecutor.get_venv_python())

    # Try running a test code
    test_code_path = os.path.join(Config.WORKSPACE_DIR, "test_run.py")
    with open(test_code_path, "w") as f:
        f.write("import sys\nprint('Hello from sandbox python:', sys.version)\n")

    res = CodeExecutor.execute_script(test_code_path)
    print(res)

    # Clean up test code
    try:
        os.remove(test_code_path)
    except Exception:
        pass
