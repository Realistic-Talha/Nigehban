"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Nigehban API."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment
    ENVIRONMENT: str = "dev"  # dev | prod

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://nigehban:nigehban@localhost:5432/nigehban"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM provider: ollama | groq | anthropic | mock (mock banned when ENVIRONMENT=prod)
    LLM_PROVIDER: str = "ollama"
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_FAST: str = "qwen2.5:7b-instruct"
    OLLAMA_MODEL_REASONING: str = "qwen2.5:14b-instruct"

    # Google Fact Check Tools API (optional — NEI when absent)
    GOOGLE_FACTCHECK_API_KEY: str = ""

    # Detection artifacts directory (ONNX from Colab)
    DETECTION_ARTIFACTS_DIR: str = "models/artifacts"

    # Search provider: duckduckgo | mock
    SEARCH_PROVIDER: str = "duckduckgo"
    SEARCH_API_KEY: str = ""

    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # WhatsApp Cloud API (Meta) — deferred channel
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "nigehban-internal-verify"
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""

    # Cloudflare R2 (S3-compatible object storage)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "nigehban-media"
    R2_ENDPOINT_URL: str = ""

    # S3-compatible storage (MinIO local dev default)
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "nigehban-media"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"

    # Local file storage fallback
    LOCAL_STORAGE_DIR: str = "uploads"

    # RSS / news feed sources for ingestion
    RSS_FEED_URLS: list[str] = []

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # AIGC / UnivFD — CLIP runs on Colab; laptop calls this public URL (cloudflared)
    # Example: https://xxxx.trycloudflare.com  (POST /score multipart file)
    AIGC_REMOTE_URL: str = ""
    AIGC_REMOTE_TIMEOUT: float = 60.0

    # Worker
    WORKER_POLL_INTERVAL: float = 1.0
    WORKER_INLINE: bool = True  # Run queue consumer inside API process (dev)
    TREND_SNAPSHOT_INTERVAL_MINUTES: int = 15


settings = Settings()
