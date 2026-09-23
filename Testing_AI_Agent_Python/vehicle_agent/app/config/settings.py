import os

from dotenv import load_dotenv


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

ENV_FILE = os.path.join(
    BASE_DIR,
    ".env",
)

load_dotenv(
    ENV_FILE
)


class Settings:

    # =====================================================
    # Ollama
    # =====================================================

    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://127.0.0.1:11434",
    )

    ollama_model: str = os.getenv(
        "OLLAMA_MODEL",
        "qwen3:8b",
    )

    ollama_timeout: int = int(
        os.getenv(
            "OLLAMA_TIMEOUT",
            "180",
        )
    )

    ollama_num_predict: int = int(
        os.getenv(
            "OLLAMA_NUM_PREDICT",
            "256",
        )
    )

    ollama_keep_alive: str = os.getenv(
        "OLLAMA_KEEP_ALIVE",
        "10m",
    )

    ollama_num_ctx: int = int(
        os.getenv(
            "OLLAMA_NUM_CTX",
            "4096",
        )
    )

    # Keep a small, per-user in-memory (and disk-persisted) history so
    # follow-up messages such as "what about the second one?" have
    # context. Bounded on purpose.
    agent_memory_messages: int = int(
        os.getenv(
            "AGENT_MEMORY_MESSAGES",
            "8",
        )
    )

    agent_memory_file: str = os.getenv(
        "AGENT_MEMORY_FILE",
        os.path.join(BASE_DIR, "storage", "conversation_memory.json"),
    )

    agent_data_answer_cache_seconds: int = int(
        os.getenv("AGENT_DATA_ANSWER_CACHE_SECONDS", "45")
    )

    # Conversation history is batched to disk on this interval instead of
    # on every chat request, so a burst of messages does not rewrite the
    # whole history file (all users) on each one.
    agent_memory_save_interval_seconds: float = float(
        os.getenv(
            "AGENT_MEMORY_SAVE_INTERVAL_SECONDS",
            "3",
        )
    )

    # =====================================================
    # Pitstrack
    # =====================================================

    pitstrack_base_url: str = os.getenv(
        "PITSTRACK_BASE_URL",
        "https://tracking.dev.pitstrack.com",
    )

    pitstrack_token: str = os.getenv(
        "PITSTRACK_TOKEN",
        "",
    ).strip()

    pitstrack_account_id: str = os.getenv(
        "PITSTRACK_ACCOUNT_ID",
        "142",
    ).strip()

    pitstrack_timeout: int = int(
        os.getenv(
            "PITSTRACK_TIMEOUT",
            "15",
        )
    )

    pitstrack_vehicles_cache_seconds: int = int(
        os.getenv(
            "PITSTRACK_VEHICLES_CACHE_SECONDS",
            "60",
        )
    )

    # =====================================================
    # Agent
    # =====================================================

    app_name: str = "Vehicle Fleet AI Agent"

    api_secret: str = os.getenv(
        "PYTHON_AGENT_SECRET",
        "vehicle-ai-local-secret",
    )


settings = Settings()
