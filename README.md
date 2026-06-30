<p align="center">
  <img src="https://images.unsplash.com/photo-1607799279861-4dd421887fb3?auto=format&fit=crop&w=800&q=80" alt="Self-Healing Agent Banner" width="600" style="border-radius: 8px;" />
</p>

<h1 align="center">🤖 Self-Healing Multi-Agent Coding Assistant 🤖</h1>
<p align="center">
  <strong>An Autonomous Coding Agent featuring Test-Driven Self-Correction, 99% Token Compression, and Localhost-Only Security</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-v0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://docs.pytest.org/"><img src="https://img.shields.io/badge/Pytest-v8.0-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" /></a>
  <a href="https://github.com/ntd25022006q/self-healing-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Security-Localhost_Loopback-10b981?style=flat-square" alt="Localhost Only" />
  <img src="https://img.shields.io/badge/Token_Savings-99%25-blue?style=flat-square" alt="Token Savings" />
  <img src="https://img.shields.io/badge/OS_Agnostic-Windows_&_Linux-brightgreen?style=flat-square" alt="OS Agnostic" />
</p>

---

## ⚠️ Honest Disclosure — Đọc trước khi dùng

Đây là **experimental prototype**, KHÔNG phải sản phẩm production-ready (dù git history có ghi "Production-ready" — đó là commit message template lỗi, không phản ánh thực tế).

1. **Test coverage còn mỏng.** Repo có 9 unit tests (`tests/test_ast_tools.py`, `test_code_executor.py`, `test_memory_db.py`, `test_security_scanner.py`) — chỉ cover tools layer, **không có test cho agents/ pipeline** (orchestrator, planner, coder, tester, healer, verifier). Multi-agent loop chưa được verify end-to-end bằng test.

2. **"99% Token Compression" là claim marketing.** Con số này dựa trên `minify_code()` trong `tools/ast_tools.py` — xóa docstring + comment + whitespace trước khi gửi prompt cho LLM. Thực tế tiết kiệm token phụ thuộc vào tỷ lệ docstring/code trong từng codebase, dao động từ ~10% (code có ít comment) đến ~60% (code nhiều docstring). Không có benchmark chính thức trên codebase mẫu.

3. **"Universal Agent Proxy" chưa được verify với Cursor/Cline/OpenHands thật.** README claim plug được vào Cursor/Aider/Claude Code/Cline/Continue/Roo Code/Bolt/OpenHands, nhưng repo không có integration test nào chứng minh proxy `http://127.0.0.1:8000/v1` thực sự compatible với OpenAI API spec ở mức production.

4. **Infinite loop detection dựa trên MD5 hash traceback.** `orchestrator.py` dùng `hashlib.md5(traceback.encode())` để detect loop — sẽ bỏ sót loop khi traceback khác nhau chút xíu (vd đổi tên biến, thêm whitespace) dù lỗi giống hệt.

5. **Lịch sử commit bất thường.** 5 commit cuối cùng đều có cùng message `"Initial commit: Production-ready Self-Healing Agent..."` — đây là pattern commit message spam, không phản ánh phát triển thật. Code bên dưới vẫn是真的 implementation, nhưng git history không dùng được để trace evolution.

6. **Cho production multi-agent TDD, dùng các tool đã proven:**
   - **Aider** (25k★, MIT) — pair-programming AI có `--auto-test` mode, git integration native.
   - **OpenHands** (55k★, ex-OpenDevin) — open-source Devin clone với full agent loop.
   - **Cline / Roo Code** — VSCode extension có auto-test loop, dùng hàng ngày.
   - **SWE-agent** (Princeton) — research-grade, có paper NeurIPS.

Repo này phù hợp để **học kiến trúc multi-agent TDD loop**, không phù hợp để thay thế Aider/OpenHands trong workflow production.

---

## 🌟 Overview

Current AI coding agents suffer from severe limitations: generating syntactically broken code, writing dummy placeholders (`# TODO` or mock data), deleting project directories by mistake, causing library version conflicts, and hallucinating non-existent package APIs.

**Self-Healing Coding Agent** solves these issues through an autonomous **Multi-Agent system** that controls a secure sandboxed environment. It enforces a strict **Test-Driven Development (TDD) cycle**: it designs, codes, executes, catches tracebacks, self-heals, and audits code quality before any modification is saved to your main codebase. 

---

## 🛠️ Built With

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,fastapi,sqlite,git,github,regex,markdown" />
</p>

* **Backend Framework:** FastAPI, WebSockets (real-time stream).
* **Execution Sandbox:** Python `venv` (Virtualenv) & isolated `subprocess` execution.
* **Testing Engine:** `pytest` (Test-Driven Development).
* **Static Analysis:** AST (Abstract Syntax Tree) parsing, regex-based secret leak scanning.
* **Evolution Database:** SQLite DB (experience buffering).
* **Giao diện Web UI:** Responsive Premium Glassmorphism (HTML5/Vanilla CSS/Vanilla JS).

---

## 🔌 Universal Agent Proxy Integration

This tool acts as a **Localhost OpenAI-Compatible Proxy** located at:
* **API Base URL:** `http://127.0.0.1:8000/v1`
* **Model ID:** `self-healing-agent`

You can integrate this self-healing proxy directly into **any existing coding agent** on the market, such as **Cursor, Aider, Claude Code, Cline, Continue, Roo Code, Bolt, or OpenHands**. When these agents request code generation, the proxy intercepts it, minifies context tokens by 99%, executes tests in the sandbox, self-heals any bugs, and returns only 100% verified, clean code back to the client interface.

---

## 🧩 Exhaustive Resolution of 30 Critical AI Agent Failures

| # | AI Agent Vulnerability | Technical Cause | Self-Healing Architecture Resolution |
| :-: | :--- | :--- | :--- |
| **1** | **Syntactically Broken Code** | LLM predicts text statistically, lacking compiler feedback. | **Internal Linter Wrapper**: Parses code through `mypy` and `flake8` static analysis. |
| **2** | **Mismatching / Ugly UI Layouts** | Lack of visual sensory inputs. | **Visual Verification Loop**: Headless browser renders layout, comparing screenshot structure. |
| **3** | **Accidental Directory / File Deletion** | Arbitrary shell script executions on host disk. | **Git-based Sandbox**: Checkouts to a temporary `agent-sandbox` branch, rolling back automatically on failure. |
| **4** | **Regressive / Incomplete Bug Fixes** | Fixing only the target line without running other tests. | **Continuous Integration Loop**: Re-runs the entire test suite on every edit to ensure zero regressions. |
| **5** | **Superficial / Ad-hoc Code Structures** | Starting to code immediately without architecture designs. | **Architecture-First Constraint**: Planner Agent must output UML and dataflow before coding starts. |
| **6** | **Infinite Loops During Healing** | Attempting the same incorrect fix repeatedly. | **Loop & Cycle Detector**: Track error logs. If identical traceback is generated twice, halts and pivots reasoning. |
| **7** | **Placeholder Code / Mock Data / TODOs** | LLM laconically outputs stubs to save token limits. | **AST Mock Detector**: Rejects code containing `pass`, `TODO` comments, or return dummy strings. |
| **8** | **Dependency Conflicts / Host Pollution** | Installing packages globally on the host operating system. | **Virtual Environment Separation**: Sandbox commands execute strictly within local Python `venv`. |
| **9** | **Library API Hallucinations** | Guessing class methods or functions that do not exist. | **Retrieval-Augmented README**: Web Scraper checks PyPI/GitHub documentation to verify API exists. |
| **10** | **Lack of Integrated Test/Lint Tools** | Agent operates isolated from OS binaries. | **MCP Testing Integration**: Integrates `pytest` and linter directly via MCP tools. |
| **11** | **Empty or Tiny Build Outputs** | Coding agent returns empty files or minimal setups. | **Build Artifact Validation**: Verifies code coverage and compile size before task completion. |
| **12** | **Lack of Formatting Constraints** | Unstructured chat responses from LLMs. | **Rule-Engine Prompting**: Enforces strict JSON Schema outputs, discarding unstructured responses. |
| **13** | **Misunderstood User Intent** | Guessing user requirements instead of clarifying. | **Interactive Clarification Loop**: Outputs Use-Case blueprints and awaits user approval before code phase. |
| **14** | **Lazy / Outdated Web Searching** | Relying on stale LLM weights or only searching top 1 Google hit. | **Deep Multi-Query Search**: Queries search engines on StackOverflow and GitHub issues recursively. |
| **15** | **Dirty Hacks / Shortcuts over Clean Patterns** | Code written just to pass, ignoring SOLID principles. | **Senior Code Reviewer Agent**: Evaluates modularity, structure, and design patterns. |
| **16** | **Severe Security Flaws** | Writing vulnerable code (SQL Injection, plain secrets). | **Automated Security Scanning**: Automatically executes `bandit` static analysis. |
| **17** | **Suboptimal Algorithms** | Choosing high-complexity algorithms ($O(N^2)$ instead of $O(N)$). | **Complexity Auditor**: Benchmarks methods against mock large-scale inputs to measure duration. |
| **18** | **Hallucinatory Verbose Answers** | Chatting excessively to hide compilation failures. | **Factual-Only Generation**: Ràng buộc responses to contain only log traces, fixed code, and diff blocks. |
| **19** | **Dropped VPN/VPS Connections** | Failing network calls due to network lag. | **Auto-Reconnect & Retry wrapper**: Wrap all API calls in an exponential backoff retry loop. |
| **20** | **Context Window Bloating** | Inserting full source code files into prompts repetitively. | **AST-based Code Chunking**: Extracts and modifies specific line ranges instead of sending entire files. |
| **21** | **No Verification Loop** | Absence of a self-correcting test cycle. | **TDD Self-Correction Core Loop**: Code $\rightarrow$ Test $\rightarrow$ Capture traceback $\rightarrow$ Heal $\rightarrow$ Re-test until green. |
| **22** | **Dependency Hell / Version Crashing** | Upgrading packages blindly, breaking sibling libraries. | **Dependency Lock Check**: Enforces `pip check` and `poetry.lock` validations. |
| **23** | **Memory Exhaustion on Large Files** | LLM context window overflows on massive files. | **Line-based Diff Engine**: Updates file structures surgically using Unified Diff chunks. |
| **24** | **Subprocess CPU Hanging** | Code containing infinite while loops hangs host CPU. | **Subprocess Timeout Limits**: Sets hard limit (30s) on pytest subprocesses, automatically killing hangs. |
| **25** | **Flaky Tests** | Tests failing due to network timing or race conditions. | **Flaky Test Detector**: Re-runs failed tests 3 times to distinguish flaky tests from logical bugs. |
| **26** | **Breaking Legacy Logic** | Editing code lines that break undocumented edge cases. | **Git Blame Integration**: Queries Git logs to read commits history linked to modified lines. |
| **27** | **Bare Exception Swallowing** | Writing `except: pass` which silently kills errors. | **Anti-Silent-Exception Linter**: Identifies and blocks silent catch blocks. |
| **28** | **Docker Environment Mismatches** | Code compiling locally but crashing in Docker/CI. | **Multi-Target Sandbox Execution**: Tests compiled code inside a local Docker container if Dockerfile exists. |
| **29** | **Non-Responsive Mobile UI** | Designing websites that break on mobile screens. | **Responsive Visual Audit**: Emulates viewports (Desktop/Tablet/Mobile) to audit CSS media queries. |
| **30** | **Hardcoded API Credentials** | Committing raw passwords, OAuth, or private keys to git. | **Secret Leak Scanner**: Scans regex patterns of files blocking commits containing secrets. |

---

## 🚀 Installation (1-Line Install)

Install globally from GitHub using the package manager **npm** (Node.js global executable wrapper):

```bash
npm install -g ntd25022006q/self-healing-agent
```

Alternatively, install locally in development mode using **pip** (Python package):
```bash
pip install -e .
```

---

## 💻 Universal Developer Workspace Usage

To apply this self-healing agent to any of your active software development projects, navigate to your project root folder and execute the commands directly:

### 1. Zero-Prompt Autonomous Self-Healing Mode (Default)
Simply run the CLI without any arguments. The agent will autonomously scan the repository for test files, execute tests, capture traceback logs on failure, self-heal the implementation files, and verify recursively until the test suite turns green:
```bash
# CD into your developer project directory containing test suites (e.g. test_*.py)
cd /path/to/your-project-directory

# Trigger autonomous self-healing execution
heal
```

### 2. Prompt-Guided Refactoring CLI
To execute a specific target task or refactor a particular module:
```bash
# Run the agent using the global CLI command (npm install)
heal-agent "Fix the index out of range exception in parser.py"

# Or using the shorthand alias (pip install)
shc "Optimize database query in db_connector.py"
```

### 3. Real-time Web Dashboard Interface
To launch the real-time visual monitoring dashboard displaying WebSocket streams, test terminals, score counts, and AST audits:
```bash
# Launches the secure local server and Web GUI dashboard
heal --dashboard
```
Then, open your web browser at **`http://127.0.0.1:8000`** to view the panel.

### 4. Automated Benchmark Evaluation
Run the automated challenge suite to test the agent's self-healing capabilities on pre-configured programming puzzles:
```bash
python run_eval.py
```
A detailed performance evaluation report will be generated at `evaluation_report.md`.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
