import os
import uuid


class Config:
    # LLM Settings
    # ollama, openai, gemini
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "a0376948ee1c4aafb282d14f9902a3c9.cu_hGeR4xgnCClbiNSXSCUU8")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "qwen3-coder:480b")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ollama.com/v1")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Paths & Workspace
    WORKSPACE_DIR = os.path.abspath(os.getenv("WORKSPACE_DIR", "."))
    MEMORY_DB_PATH = os.path.join(WORKSPACE_DIR, "experience_memory.db")

    # Server & Security Settings
    HOST = "127.0.0.1"  # Strict localhost binding for security
    PORT = int(os.getenv("PORT", 8000))
    # Session token generated on start for API security
    SESSION_TOKEN = str(uuid.uuid4())

    # Agent constraints
    MAX_HEALING_RETRIES = int(os.getenv("MAX_HEALING_RETRIES", 8))
    AST_CHECK_ENABLED = True
    TIMEOUT_SECONDS = 30  # Timeout for subprocess execution to prevent hangs

    @classmethod
    def get_llm_config(cls):
        return {
            "provider": cls.LLM_PROVIDER,
            "ollama_host": cls.OLLAMA_HOST,
            "ollama_model": cls.OLLAMA_MODEL,
            "openai_key": cls.OPENAI_API_KEY,
            "openai_model": cls.OPENAI_MODEL,
            "openai_base_url": cls.OPENAI_BASE_URL,
            "gemini_key": cls.GEMINI_API_KEY,
            "gemini_model": cls.GEMINI_MODEL
        }


# Ensure workspace folder structure exists
os.makedirs(os.path.join(Config.WORKSPACE_DIR, "agents"), exist_ok=True)
os.makedirs(os.path.join(Config.WORKSPACE_DIR, "tools"), exist_ok=True)
os.makedirs(os.path.join(Config.WORKSPACE_DIR, "evaluator"), exist_ok=True)
os.makedirs(os.path.join(Config.WORKSPACE_DIR,
            "web", "templates"), exist_ok=True)
os.makedirs(os.path.join(Config.WORKSPACE_DIR,
            "web", "static", "css"), exist_ok=True)
os.makedirs(os.path.join(Config.WORKSPACE_DIR,
            "web", "static", "js"), exist_ok=True)
