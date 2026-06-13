from tools.code_executor import CodeExecutor


class TesterAgent:
    def __init__(self):
        self.name = "Tester"
        self.role = "Quality Assurance Agent running code and tests in isolated sandboxes."

    def run_suite(self, test_file_path: str, timeout: int | None = None) -> dict:
        """
        Executes pytest on the test suite and captures the test execution results.
        If tests crash or fail, returns a traceback summary.
        """
        print(f"[Tester] Running test suite: {test_file_path}...")

        result = CodeExecutor.run_tests(test_file_path, timeout=timeout)

        success = result.get("success", False)
        exit_code = result.get("exit_code", -1)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        failures_summary = ""

        if not success:
            print("[Tester] Tests failed. Extracting error logs...")
            # Parse stderr and stdout to find traceback info
            combined = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            # Extract key traceback lines to reduce token consumption
            lines = combined.splitlines()
            traceback_lines = []
            capture = False

            for line in lines:
                if "FAILURES" in line or "ERRORS" in line or "traceback" in line.lower() or "exception" in line.lower():
                    capture = True
                if capture:
                    traceback_lines.append(line)
                    if len(traceback_lines) > 40:  # Limit length of traceback to save tokens
                        traceback_lines.append(
                            "... [Traceback truncated to save tokens] ...")
                        break

            failures_summary = "\n".join(
                traceback_lines) if traceback_lines else combined[:2000]

        return {
            "passed": success,
            "exit_code": exit_code,
            "raw_output": f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}",
            "failures_summary": failures_summary
        }


if __name__ == "__main__":
    import os
    from config import Config

    # Quick mock run
    tester = TesterAgent()
    res = tester.run_suite(os.path.join(
        Config.WORKSPACE_DIR, "non_existent_test.py"))
    print("Passed:", res["passed"])
    print("Summary:\n", res["failures_summary"])
