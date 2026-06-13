import subprocess
import sys
import os

if __name__ == "__main__":
    print("[Shortcut] Triggering Agent Evaluation Suite...")
    python_exec = sys.executable
    cmd = [python_exec, "main.py", "--eval"]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user.")
    except Exception as e:
        print(f"Error running evaluation: {e}")
