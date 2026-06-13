import os
import sys
import argparse

# Reconfigure console standard streams to prevent Unicode encoding errors on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
        sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
    except Exception:
        pass

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import asyncio
import time

from config import Config
from agents.orchestrator import OrchestratorAgent
from tools.memory_db import MemoryDB
from evaluator.eval_runner import EvaluationRunner

# Initialize FastAPI App
app = FastAPI(title="Self-Healing Agent API")

# Mount Static Files & Templates
app.mount("/static", StaticFiles(directory=os.path.join(Config.WORKSPACE_DIR,
          "web", "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(
    Config.WORKSPACE_DIR, "web", "templates"))

# Middleware token check helper for API security


def verify_token(token: str):
    if token != Config.SESSION_TOKEN:
        raise HTTPException(
            status_code=401, detail="Unauthorized: Session token mismatch.")
    return True

# --- HTML Page Render ---


@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    score = MemoryDB.get_agent_score()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "session_token": Config.SESSION_TOKEN,
        "score": score
    })

# --- REST APIs ---


@app.get("/api/experiences")
async def get_experiences(token: str):
    verify_token(token)
    conn = MemoryDB.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experiences ORDER BY id DESC")
    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "task_description": r["task_description"],
            "error_message": r["error_message"],
            "fix_code": r["fix_code"],
            "score": r["score"],
            "created_at": r["created_at"]
        })
    conn.close()
    return results


@app.get("/api/score")
async def get_score(token: str):
    verify_token(token)
    return {"score": MemoryDB.get_agent_score()}

# --- OpenAI-Compatible Proxy Routes ---


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "self-healing-agent",
                "object": "model",
                "created": 1677858247,
                "owned_by": "self-healing-agent"
            }
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    # Extract user prompt
    user_prompt = ""
    for m in messages:
        if m.get("role") == "user":
            user_prompt = m.get("content", "")

    if not user_prompt:
        raise HTTPException(
            status_code=400, detail="Missing user prompt in messages.")

    print(f"[Proxy] Intercepted completions request: '{user_prompt[:60]}...'")

    # Run the self-healing development loop
    orch = OrchestratorAgent()
    res = orch.run_task(user_prompt)

    if res.get("success", False):
        final_code = res["implementation_code"]
        response_content = f"Here is the verified implementation code:\n\n```python\n{final_code}\n```"
    else:
        response_content = f"Self-healing agent failed to resolve code errors: {res.get('error', 'Compilation/Test failure')}"

    return {
        "id": "chatcmpl-self-healing-proxy",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "self-healing-agent",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }
        ]
    }

# --- WebSockets Hub ---


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    await websocket.accept()
    if token != Config.SESSION_TOKEN:
        await websocket.send_json({"type": "log", "message": "Unauthorized: Session token mismatch. Connection closing.", "level": "error"})
        await websocket.close()
        return

    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            action = data.get("action")

            if action == "run_task":
                prompt = data.get("prompt")

                # Define callback to stream logs through ws
                def socket_log(msg, level="info"):
                    # Basic parser to assign colors based on content
                    low = msg.lower()
                    if "success" in low or "passed" in low or "green" in low:
                        level = "success"
                    elif "error" in low or "failed" in low or "critical" in low:
                        level = "error"
                    elif "[orchestrator]" in low:
                        level = "system"

                    # Send async helper via event loop
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json(
                            {"type": "log", "message": msg, "level": level}),
                        loop
                    )

                loop = asyncio.get_running_loop()

                # Run the orchestrator in a separate executor to prevent blocking the ws loop
                def run_agent():
                    orch = OrchestratorAgent(log_callback=socket_log)
                    res = orch.run_task(prompt)

                    # Send final code update and score
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "code",
                            "impl_code": res.get("implementation_code", ""),
                            "test_code": res.get("test_code", "")
                        }),
                        loop
                    )

                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "score",
                            "score": MemoryDB.get_agent_score()
                        }),
                        loop
                    )

                    if res.get("success", False):
                        socket_log(
                            "Task finished successfully! Code generated and fully verified.", "success")
                    else:
                        socket_log(
                            f"Task aborted with error: {res.get('error', 'Unknown error')}", "error")

                loop.run_in_executor(None, run_agent)

    except WebSocketDisconnect:
        print("[WS] WebSocket client disconnected.")
    except Exception as e:
        print(f"[WS] Error: {e}")

# --- CLI runner functions ---


def run_cli_agent(prompt: str):
    print("=" * 60)
    print("Starting CLI Code-Repair & Self-Healing Loop...")
    print(f"Task: {prompt}")
    print("=" * 60)

    orch = OrchestratorAgent()
    res = orch.run_task(prompt)

    print("\n" + "=" * 60)
    if res.get("success", False):
        print("SUCCESS! Output written and tests verified.")
        print(f"Implementation File: {res['implementation_file']}")
        print(f"Test File: {res['test_file']}")
        print(f"Agent Final Score: {res['agent_score']}")
    else:
        print(f"FAILED: {res.get('error', 'Unknown Error')}")
    print("=" * 60)


def run_autonomous_mode():
    print("=" * 60)
    print("[Autonomous Mode] Scanning repository for test suites...")
    print("=" * 60)

    test_files = [f for f in os.listdir(
        Config.WORKSPACE_DIR) if f.startswith("test_") and f.endswith(".py")]

    if not test_files:
        print("[Autonomous Mode] No test suites (test_*.py) found in root directory.")
        print("To launch the Web Dashboard instead, run: heal --dashboard")
        return

    print(f"[Autonomous Mode] Found test suite(s): {', '.join(test_files)}")

    for test_file in test_files:
        print(f"\n[Autonomous Mode] Executing test suite: {test_file}")
        test_path = os.path.join(Config.WORKSPACE_DIR, test_file)

        from tools.code_executor import CodeExecutor
        res = CodeExecutor.run_tests(test_path)

        if res.get("success", False):
            print(
                f"[Autonomous Mode] 🟢 Test suite {test_file} passed successfully. Repository is healthy!")
            continue

        print(
            f"[Autonomous Mode] 🔴 Test suite {test_file} failed. Entering Self-Healing loop...")
        traceback = res.get("stderr", "") + "\n" + res.get("stdout", "")

        base_name = test_file.replace("test_", "")
        impl_path = os.path.join(Config.WORKSPACE_DIR, base_name)

        if not os.path.exists(impl_path):
            py_files = [f for f in os.listdir(Config.WORKSPACE_DIR) if f.endswith(
                ".py") and not f.startswith("test_") and f != "main.py" and f != "config.py"]
            if py_files:
                base_name = py_files[0]
                impl_path = os.path.join(Config.WORKSPACE_DIR, base_name)
            else:
                print(
                    f"[Autonomous Mode] Error: Could not locate implementation file for {test_file}")
                continue

        print(
            f"[Autonomous Mode] Target implementation file identified: {base_name}")

        with open(impl_path, "r", encoding="utf-8") as f:
            impl_code = f.read()
        with open(test_path, "r", encoding="utf-8") as f:
            test_code = f.read()

        loop_count = 0
        max_retries = Config.MAX_HEALING_RETRIES
        from agents.healer import HealerAgent
        healer = HealerAgent()

        while loop_count < max_retries:
            print(
                f"[Autonomous Mode] Self-Healing Attempt {loop_count + 1}/{max_retries}...")

            heal_res = healer.heal_code(
                f"Fix autonomous test failure in {base_name}",
                base_name, impl_code,
                test_file, test_code,
                traceback
            )

            impl_code = heal_res["implementation_code"]
            test_code = heal_res["test_code"]

            with open(impl_path, "w", encoding="utf-8") as f:
                f.write(impl_code)
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            res = CodeExecutor.run_tests(test_path)
            if res.get("success", False):
                print(
                    f"[Autonomous Mode] 🟢 Success! Code repaired and verified for {base_name}.")
                break

            traceback = res.get("stderr", "") + "\n" + res.get("stdout", "")
            loop_count += 1

        if loop_count >= max_retries:
            print(
                f"[Autonomous Mode] ❌ Failed to repair {base_name} within retry limit.")


def main_entry():
    parser = argparse.ArgumentParser(
        description="Self-Healing Coding Agent: Autonomous Code-Repair CLI & Web Dashboard")
    parser.add_argument("prompt", nargs="?", type=str,
                        help="Run code-repair and self-healing on a specific instruction/file")
    parser.add_argument("--eval", action="store_true",
                        help="Run the self-healing evaluation suite on code-repair challenges")
    parser.add_argument("--dashboard", "-d", action="store_true",
                        help="Launch the Web Dashboard UI")
    parser.add_argument("--port", type=int, default=Config.PORT,
                        help="Port to run the Web Dashboard on")

    args = parser.parse_args()

    # Initialize SQLite Database structure
    MemoryDB.init_db()

    if args.eval:
        # Run automated test suite
        print("Running automated challenges...")
        EvaluationRunner.run_suite()
    elif args.prompt:
        # Run single prompt CLI mode (positional)
        run_cli_agent(args.prompt)
    elif args.dashboard:
        # Launch Web Dashboard server explicitly
        print("=" * 60)
        print("Launching Self-Healing Agent Web Dashboard...")
        print(f"Secure Server API binding: http://127.0.0.1:{args.port}")
        print(f"Session Token: {Config.SESSION_TOKEN}")
        print("=" * 60)
        uvicorn.run("main:app", host="127.0.0.1", port=args.port, reload=False)
    else:
        # Default: Run Autonomous Self-Healing Mode on current directory
        run_autonomous_mode()


if __name__ == "__main__":
    main_entry()
