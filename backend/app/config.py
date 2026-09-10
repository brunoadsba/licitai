"""
Configurações da aplicação.
Carrega variáveis de ambiente com validação via Pydantic Settings.
Nenhum secret é hardcoded — todos vêm de variáveis de ambiente.
"""

import logging
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Ambiente ---
    # development: token/DB opcionais (piloto local).
    # production/staging: DATABASE_URL e API_TOKEN obrigatórios.
    app_env: Literal["development", "staging", "production"] = "development"

    # --- Banco de Dados ---
    database_url: str = "sqlite+aiosqlite:///./licitacao.db"

    # --- Provedor de LLM ---
    llm_provider: Literal["groq", "gemini", "ollama"] = "groq"
    # Se False, recusa documentos classificados como sigilosos em provedores cloud.
    llm_allow_cloud: bool = True

    # --- Groq ---
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    # --- Google Gemini ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    # --- Ollama ---
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3:32b"

    # --- Embeddings (RAG Fase 4) ---
    embeddings_provider: Literal["gemini", "ollama"] = "gemini"
    embeddings_model: str = "gemini-embedding-001"
    embeddings_dim: int = 3072

    # --- Aplicação ---
    allowed_origins: str = "http://localhost:3000"
    max_upload_size_mb: int = 50

    # --- Rate Limiting ---
    rate_limit_max: int = 600

    # --- LLM ---
    llm_timeout_seconds: float = 120.0
    # Orçamento máximo aproximado de tokens por análise (soft limit).
    llm_max_tokens_per_analysis: int = 250_000

    # --- Concorrência da análise ---
    analysis_concurrency: int = 3
    max_concurrent_analyses: int = 2
    # Limite global de chamadas LLM concorrentes no processo.
    llm_global_concurrency: int = 6
    # Soft budget: 0 = ilimitado. Estima ~4 calls/item (multi), ~2 (economic), ~1 (single).
    analysis_max_llm_calls: int = 0

    # --- Copiloto (Chat Consultivo) ---
    chat_enabled: bool = True
    chat_require_grounding: bool = True
    chat_top_k_sources: int = 5
    chat_max_message_length: int = 2000
    chat_max_sources_stored: int = 8
    chat_force_fake_provider: bool = False

    # --- SMTP (RF04) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_require_tls: bool = True

    # --- Segurança ---
    # Vazio desabilita o token apenas em development.
    api_token: str = ""

    # --- Jobs / Worker ---
    job_lease_seconds: int = 300
    job_max_attempts: int = 3
    worker_poll_interval_seconds: float = 2.0

    # --- Schema ---
    expected_schema_version: str = "20260908_003"

    @field_validator("*", mode="before")
    @classmethod
    def _strip_crlf(cls, v):
        """Tolera .env com CRLF (Windows/WSL)."""
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> "Settings":
        if self.app_env == "development":
            return self
        if not self.database_url or self.database_url.startswith("sqlite"):
            raise ValueError(
                "DATABASE_URL PostgreSQL é obrigatória quando APP_ENV != development."
            )
        if not self.api_token:
            raise ValueError(
                "API_TOKEN é obrigatório quando APP_ENV != development."
            )
        return self

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    ALLOWED_FILE_EXTENSIONS: set[str] = {".pdf", ".docx", ".odt"}
    ALLOWED_MIME_TYPES: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.oasis.opendocument.text",
    }


settings = Settings()
