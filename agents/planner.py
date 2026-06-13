from agents.base import BaseAgent
from tools.web_search import WebSearchTool


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Planner", "Architect who designs the code layout and checks official APIs.")

    def create_plan(self, user_prompt: str, file_map_summary: str = "") -> dict:
        """
        Creates an architectural execution plan based on user requirements and current codebase context.
        If necessary, it searches Google/GitHub to confirm API specifications.
        """
        print("[Planner] Designing execution plan...")

        # Step 1: Detect libraries mentioned in user prompt and verify online
        search_results_summary = ""
        import re
        libs = re.findall(
            r"using ([\w\-]+) library|with ([\w\-]+)|install ([\w\-]+)", user_prompt, re.IGNORECASE)
        found_libs = [lib for group in libs for lib in group if lib]

        for lib in found_libs:
            print(f"[Planner] Verifying API for library: {lib}...")
            # Search PyPI to get correct name/API
            search_res = WebSearchTool.search(
                f"site:pypi.org/project/{lib} usage examples", max_results=2)
            if search_res:
                search_results_summary += f"\nDocumentation for '{lib}':\n"
                for r in search_res:
                    search_results_summary += f"- {r['url']}: {r['snippet']}\n"

        system_prompt = """
You are a Senior Systems Architect. Your task is to design an implementation plan for a coding task.
You must output a structured planning blueprint.
Rules:
1. Define the exact files to create or modify.
2. Outline the classes, functions, and key logic required.
3. Choose the best, most optimized algorithms.
4. Avoid any mock placeholders. Keep it production-ready.
5. Consider OS compatibility (ensure code is platform-agnostic, using pathlib and sys.executable).
6. MODULARITY PRINCIPLE: Prefer creating a NEW dedicated file (CREATE) for complex classes, new modules, or distinct feature sets (e.g., parsers, evaluators, schedulers), rather than modifying (MODIFY) or cramming them into existing unrelated files. Only modify an existing file if the new code directly relates to, extends, or corrects the existing logic in that file.
"""

        user_content = f"""
User Request: {user_prompt}

Current Project Files:
{file_map_summary if file_map_summary else "Empty Directory"}

Verified Library Documentation:
{search_results_summary if search_results_summary else "No specific external library documentation verified."}

Please output your plan using the following format:
PLAN:
- File: [file_name] (Action: CREATE/MODIFY)
  - Purpose: [brief purpose]
  - Architecture: [classes and functions to declare]
  - Dependencies: [imported libraries]
"""

        response = self.generate(system_prompt, user_content)
        return {
            "plan_text": response,
            "verified_docs": search_results_summary
        }


if __name__ == "__main__":
    planner = PlannerAgent()
    # Test planning
    p = planner.create_plan(
        "Build a command line tool that calculates geopy distance using Nominatim")
    print(p["plan_text"])
