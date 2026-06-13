import os
import json
import time
from config import Config
from agents.orchestrator import OrchestratorAgent
from tools.memory_db import MemoryDB

class EvaluationRunner:
    @classmethod
    def run_suite(cls) -> dict:
        """
        Loads the test tasks from JSON, runs each task through the Orchestrator,
        measures performance, and saves a markdown evaluation report.
        """
        tasks_path = os.path.join(Config.WORKSPACE_DIR, "evaluator", "test_tasks.json")
        if not os.path.exists(tasks_path):
            print(f"[Evaluation] Error: Test tasks file not found at {tasks_path}")
            return {"success": False, "error": "Tasks file not found."}
            
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)
            
        print(f"[Evaluation] Loaded {len(tasks)} tasks for evaluation.")
        results = []
        total_success = 0
        
        # Reset agent score in DB to 100 for clean test run
        MemoryDB.init_db()
        conn = MemoryDB.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE agent_score SET current_score = 100 WHERE id = 1")
        conn.commit()
        conn.close()
        
        orchestrator = OrchestratorAgent()
        
        for idx, task in enumerate(tasks, 1):
            print("\n" + "="*50)
            print(f"Running Challenge {idx}/{len(tasks)}: {task['title']}")
            print(f"Description: {task['description']}")
            print("="*50)
            
            start_time = time.time()
            # Run the agent development cycle
            run_res = orchestrator.run_task(task["description"])
            elapsed = time.time() - start_time
            
            success = run_res.get("success", False)
            if success:
                total_success += 1
                
            results.append({
                "id": task["id"],
                "title": task["title"],
                "success": success,
                "elapsed_seconds": round(elapsed, 2),
                "impl_file": run_res.get("implementation_file", "None"),
                "test_file": run_res.get("test_file", "None"),
                "agent_score": MemoryDB.get_agent_score(),
                "error": run_res.get("error", "")
            })
            
            # Sleep briefly to settle subprocesses
            time.sleep(2)
            
        # Compile Markdown Report
        cls._generate_report(results, total_success, len(tasks))
        
        return {
            "success": True,
            "total_tasks": len(tasks),
            "passed_tasks": total_success,
            "results": results
        }

    @classmethod
    def _generate_report(cls, results: list, passed: int, total: int):
        report_path = os.path.join(Config.WORKSPACE_DIR, "evaluation_report.md")
        
        accuracy_rate = round((passed / total) * 100, 2)
        
        md = f"""# Báo cáo đánh giá hiệu năng lập trình tự động (AI Agent Evaluation Report)

Hệ thống đã tự động kích hoạt bộ bài test thử thách lập trình để đánh giá khả năng **Tự lập trình (Auto-code)**, **Tự chạy tests (Sandbox Execution)**, và **Tự sửa lỗi (Self-Healing)** của các Agent.

## Tóm tắt kết quả (Summary)
* **Tổng số bài kiểm tra:** {total}
* **Số bài hoàn thành xuất sắc (Passed):** {passed}
* **Tỷ lệ thành công (Accuracy Rate):** {accuracy_rate}%
* **Điểm số Agent tích lũy cuối cùng:** {MemoryDB.get_agent_score()}

---

## Chi tiết kết quả từng bài thử thách (Detailed Results)

"""
        for r in results:
            status_emoji = "🟢 THÀNH CÔNG (PASSED)" if r["success"] else "🔴 THẤT BẠI (FAILED)"
            md += f"""### Thử thách {r['id']}: {r['title']}
* **Trạng thái:** {status_emoji}
* **Thời gian xử lý:** {r['elapsed_seconds']} giây
* **File Code chính:** `{r['impl_file']}`
* **File Unit Tests:** `{r['test_file']}`
* **Điểm số tích lũy sau bài này:** {r['agent_score']}
"""
            if not r["success"]:
                md += f"* **Chi tiết lỗi:** `{r['error']}`\n"
            md += "\n---\n"
            
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md)
            
        print(f"\n[Evaluation] Suite finished. Accuracy: {accuracy_rate}%. Report written to {report_path}")

if __name__ == "__main__":
    EvaluationRunner.run_suite()
