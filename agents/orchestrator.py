import os
import hashlib
from config import Config
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.tester import TesterAgent
from agents.healer import HealerAgent
from agents.verifier import VerifierAgent
from tools.memory_db import MemoryDB
from tools.ast_tools import ASTTools


class OrchestratorAgent:
    def __init__(self, log_callback=None):
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.healer = HealerAgent()
        self.verifier = VerifierAgent()
        self.log_callback = log_callback
        MemoryDB.init_db()

    def log(self, message: str):
        print(f"[Orchestrator] {message}")
        if self.log_callback:
            self.log_callback(message)

    def _has_git(self) -> bool:
        import shutil
        import subprocess
        git_path = shutil.which("git")
        if not git_path:
            return False
        try:
            res = subprocess.run([git_path, "--version"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def _create_git_backup(self) -> bool:
        """
        Creates a git commit or branch snapshot before modifying files.
        If git is not initialized, initializes it. Falls back to file-based backup if git fails.
        """
        import subprocess
        if not self._has_git():
            self.log("Git not found on host system. Using file-based backup fallback.")
            return self._create_file_backup()

        try:
            # Check if directory is a git repo
            if not os.path.exists(os.path.join(Config.WORKSPACE_DIR, ".git")):
                self.log("Initializing git repository for safe backup...")
                subprocess.run(["git", "init"], check=True, capture_output=True)

            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            # Create a safety checkpoint commit
            subprocess.run(["git", "commit", "-m", "pre-agent-sandbox-checkpoint", "--allow-empty"], check=True, capture_output=True)
            self.log("Git checkpoint created. Workspace is backed up safely.")
            self.backup_mode = "git"
            return True
        except Exception as e:
            self.log(f"Git backup warning: {e}. Falling back to file-based backup.")
            return self._create_file_backup()

    def _create_file_backup(self) -> bool:
        import shutil
        backup_dir = os.path.join(Config.WORKSPACE_DIR, ".agent_backup")
        try:
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            os.makedirs(backup_dir, exist_ok=True)
            
            # Find and copy all python files in workspace root
            files = [f for f in os.listdir(Config.WORKSPACE_DIR) 
                     if os.path.isfile(os.path.join(Config.WORKSPACE_DIR, f)) 
                     and f.endswith(".py")]
            
            self.backed_up_files = []
            for file_name in files:
                src = os.path.join(Config.WORKSPACE_DIR, file_name)
                dst = os.path.join(backup_dir, file_name)
                shutil.copy2(src, dst)
                self.backed_up_files.append(file_name)
                
            self.log(f"File-based backup created for {len(self.backed_up_files)} files.")
            self.backup_mode = "file"
            return True
        except Exception as e:
            self.log(f"File backup critical error: {e}")
            self.backup_mode = "none"
            return False

    def _restore_backup(self):
        """
        Restores workspace to the last git checkpoint or file-based backup in case of critical crash.
        """
        import shutil
        import subprocess
        
        mode = getattr(self, "backup_mode", "none")
        if mode == "git":
            try:
                self.log("Restoring workspace from safety Git checkpoint...")
                subprocess.run(["git", "reset", "--hard", "HEAD"], check=True, capture_output=True)
            except Exception as e:
                self.log(f"Git restore failed: {e}")
        elif mode == "file":
            try:
                self.log("Restoring workspace from file-based backup...")
                backup_dir = os.path.join(Config.WORKSPACE_DIR, ".agent_backup")
                if not os.path.exists(backup_dir):
                    self.log("Error: Backup directory not found. Cannot restore.")
                    return
                
                # Delete any py files created in workspace root that are not in backup list
                current_files = [f for f in os.listdir(Config.WORKSPACE_DIR) 
                                 if os.path.isfile(os.path.join(Config.WORKSPACE_DIR, f)) 
                                 and f.endswith(".py")]
                for file_name in current_files:
                    if file_name not in self.backed_up_files:
                        path = os.path.join(Config.WORKSPACE_DIR, file_name)
                        os.remove(path)
                        self.log(f"Cleaned up temporary file: {file_name}")
                
                # Restore backed up files
                for file_name in self.backed_up_files:
                    src = os.path.join(backup_dir, file_name)
                    dst = os.path.join(Config.WORKSPACE_DIR, file_name)
                    shutil.copy2(src, dst)
                    
                self.log("Workspace files successfully restored.")
            except Exception as e:
                self.log(f"File-based restore failed: {e}")
        else:
            self.log("No valid backup found. Skipping restore.")

    def _cleanup_backup(self):
        import shutil
        mode = getattr(self, "backup_mode", "none")
        if mode == "file":
            backup_dir = os.path.join(Config.WORKSPACE_DIR, ".agent_backup")
            try:
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
            except Exception as e:
                self.log(f"Backup cleanup warning: {e}")

    def run_task(self, user_prompt: str) -> dict:
        self.log(
            f"Starting Agentic Development loop for query: '{user_prompt}'")

        # Guard check: Ensure agent is not banned (Score <= -300)
        current_score = MemoryDB.get_agent_score()
        if current_score <= -300:
            self.log(
                "ERROR: Agent performance score is below -300. System is LOCKED.")
            return {
                "success": False,
                "error": "Agent is currently SUSPENDED due to poor performance. Please write an appeal to unlock."
            }

        # Backup workspace
        self._create_git_backup()

        # Step 1: Query Code Map summary (files list)
        files = [f for f in os.listdir(Config.WORKSPACE_DIR) if os.path.isfile(
            os.path.join(Config.WORKSPACE_DIR, f)) and f.endswith(".py")]
        file_map = "\n".join([f"- {f}" for f in files])

        # Step 2: Create Execution Plan
        plan_res = self.planner.create_plan(user_prompt, file_map)
        plan_text = plan_res["plan_text"]
        if plan_text.startswith("Error:"):
            self.log(f"ERROR: Planner failed due to LLM error: {plan_text}")
            self._restore_backup()
            return {
                "success": False,
                "error": f"Planning failed: {plan_text}"
            }
        self.log("Execution plan designed successfully.")

        # Try to parse planned filename from plan_text (e.g. "- File: filename.py")
        import re
        planned_file = None
        match = re.search(r"-\s*File:\s*([\w\-\.]+)", plan_text, re.IGNORECASE)
        if match:
            planned_file = match.group(1).strip()
            self.log(f"Parsed planned filename: {planned_file}")

        # Step 3: Write Initial Code & Tests
        existing_content = ""
        if planned_file:
            planned_path = os.path.join(Config.WORKSPACE_DIR, planned_file)
            if os.path.exists(planned_path):
                try:
                    with open(planned_path, "r", encoding="utf-8") as f:
                        existing_content = f.read()
                    self.log(f"Detected existing file {planned_file}. Passing existing code context to CoderAgent for incremental refactoring.")
                except Exception as e:
                    self.log(f"Warning reading existing file {planned_file}: {e}")

        coder_res = self.coder.write_code(
            user_prompt, plan_text, current_code=existing_content, default_filename=planned_file)
        impl_file = coder_res["implementation_file"]
        impl_code = coder_res["implementation_code"]
        test_file = coder_res["test_file"]
        test_code = coder_res["test_code"]

        if not impl_code or not test_code or impl_code.startswith("Error:") or test_code.startswith("Error:"):
            self.log("ERROR: Coder failed to generate valid code blocks or LLM API error occurred.")
            self._restore_backup()
            return {
                "success": False,
                "error": f"Coding failed: {impl_code if impl_code.startswith('Error:') else 'Empty response'}"
            }

        if "test_placeholder" in test_code:
            self.log("ERROR: Coder failed to generate a specific unit test suite (returned test_placeholder).")
            self._restore_backup()
            return {
                "success": False,
                "error": "Failed to generate specific unit test suite for the task (returned test_placeholder)."
            }

        impl_path = os.path.join(Config.WORKSPACE_DIR, impl_file)
        test_path = os.path.join(Config.WORKSPACE_DIR, test_file)

        # Write files locally
        with open(impl_path, "w", encoding="utf-8") as f:
            f.write(impl_code)
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        self.log(f"Created core implementation file: {impl_file}")
        self.log(f"Created pytest test file: {test_file}")

        # Step 4: Self-Healing Testing Loop
        loop_count = 0
        max_retries = Config.MAX_HEALING_RETRIES
        error_history = set()  # To detect infinite loop locks
        stuck_count = 0  # Track consecutive stuck healer outcomes

        while loop_count < max_retries:
            self.log(f"Test Loop {loop_count + 1}/{max_retries}...")

            # Progressive Timeout: start at default, increase by 20s per retry loop
            current_timeout = Config.TIMEOUT_SECONDS + (loop_count * 20)

            # Execute Pytest
            test_res = self.tester.run_suite(
                test_path, timeout=current_timeout)

            if test_res["passed"]:
                self.log("GREEN! All unit tests passed.")
                break

            # If failed, fetch stack trace
            traceback = test_res["failures_summary"]
            self.log(f"Tests FAILED. Diagnostic error trace captured:\n{traceback}\n")

            # Infinite Loop Lock Detection
            err_hash = hashlib.md5(traceback.encode('utf-8')).hexdigest()
            loop_locked = err_hash in error_history
            if loop_locked:
                self.log(
                    "[Warning] DETECTED LOOP LOCK! AI is repeating the same error log. Resetting implementation to base coder state to escape local minima.")
                impl_code = coder_res["implementation_code"]
                # Save the reset code to disk
                with open(impl_path, "w", encoding="utf-8") as f:
                    f.write(impl_code)
                traceback += "\n\nCRITICAL NOTIFICATION: You are stuck in a loop and repeating the same error. The implementation has been RESET to the initial starting code. You MUST try a COMPLETELY different programming paradigm or structure from scratch. Do not repeat the same buggy code pattern."

            error_history.add(err_hash)

            # Query database memory for similar past solutions
            similar_exp = MemoryDB.query_similar_experiences(traceback)
            experience_prompt = ""
            if similar_exp:
                experience_prompt = "\n--- PAST HEALING MEMORY (LEARNED FROM SIMILAR ERROR) ---\n"
                for exp in similar_exp:
                    experience_prompt += f"Problem: {exp['task_description']}\nError: {exp['error_message']}\nFixed code:\n{exp['fix_code']}\n\n"
                self.log(
                    "Successfully retrieved similar past error experiences from SQLite DB.")

            # Trigger Healer Agent
            refactor_instruction = ""
            if loop_count >= 3:
                self.log(f"[Orchestrator] Loop {loop_count + 1} reached. Activating ARCHITECTURAL REFACTOR mode to rebuild the solution structure.")
                refactor_instruction = (
                    "\n\nCRITICAL ARCHITECTURAL REFACTOR REQUEST:\n"
                    "The current implementation is failing the test suite and cannot be resolved by minor edits. "
                    "The initial codebase design is likely structurally flawed. You MUST discard the current failed approach "
                    "and rewrite the entire implementation logic from scratch using a clean, robust, and correct software architecture. "
                    "Do NOT copy/paste the current code, and do NOT truncate any code blocks. Output the complete implementation."
                )

            if stuck_count > 0:
                traceback += f"\n\n[WARNING] Your previous fix attempt returned identical code and failed (Attempt {stuck_count}). You must try a COMPLETELY different logic structure or implementation approach. Do not output the same code!"

            # Decide on temperature override
            temp_override = None
            if loop_locked:
                temp_override = 0.8
            elif loop_count >= 3:
                temp_override = 0.7  # Creative boost for refactoring
            elif stuck_count > 0:
                temp_override = 0.5

            heal_res = self.healer.heal_code(
                user_prompt,
                impl_file, impl_code,
                test_file, test_code,
                traceback + experience_prompt + refactor_instruction,
                temperature_override=temp_override
            )

            # Check if code changed
            new_impl_code = heal_res["implementation_code"]
            new_test_code = heal_res["test_code"]

            if new_impl_code.startswith("Error:") or new_test_code.startswith("Error:"):
                self.log(f"ERROR: Healer failed due to LLM error: {new_impl_code}")
                loop_count += 1
                continue

            if new_impl_code == impl_code and new_test_code == test_code:
                stuck_count += 1
                if stuck_count >= 2:
                    self.log(
                        "Healer returned identical code twice. Healing is stuck. Halting to prevent timeout.")
                    break
                self.log(
                    "Healer returned identical code. Retrying with higher creativity (temperature override)...")
                loop_count += 1
                continue
            else:
                stuck_count = 0  # Reset stuck count if code changed

            impl_code = new_impl_code
            test_code = new_test_code

            with open(impl_path, "w", encoding="utf-8") as f:
                f.write(impl_code)
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            loop_count += 1

        # Final verification check
        final_test_res = self.tester.run_suite(test_path)
        if not final_test_res["passed"]:
            self.log(
                "CRITICAL: Self-healing loop finished but tests are still failing.")
            self._restore_backup()
            return {
                "success": False,
                "error": "Self-healing tests failed to resolve."
            }

        # Step 5: Verification & Quality Audit
        self.log("Initiating static analysis, security, and AST checks...")
        verify_res = self.verifier.verify(user_prompt, impl_file, impl_code)

        if not verify_res["passed"]:
            self.log(
                "VERIFICATION FAILED: Code failed AST or Security constraints. Restoring git backup.")
            self._restore_backup()
            return {
                "success": False,
                "error": "Verification failed due to security/AST constraints.",
                "details": verify_res["violations"]
            }

        # Step 6: Successful Save to Memory Database
        # Minify code for efficient storage
        minified_code = ASTTools.minify_code(impl_code)
        MemoryDB.save_experience(
            user_prompt, "Unit tests passed successfully", minified_code)
        self.log("Successfully saved learning experience to SQLite Database.")

        self.log("ALL CHECKPOINTS PASSED. Project successfully written and verified.")
        self._cleanup_backup()
        return {
            "success": True,
            "implementation_file": impl_file,
            "implementation_code": impl_code,
            "test_file": test_file,
            "test_code": test_code,
            "agent_score": verify_res["new_score"]
        }


if __name__ == "__main__":
    # Test orchestrator run
    orch = OrchestratorAgent()
    # Mock simple task
    res = orch.run_task("Write a simple fibonacci function in math_utils.py")
    print(res)
