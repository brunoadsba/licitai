"""
Configurações da aplicação.
Carrega variáveis de ambiente com validação via Pydantic Settings.
Nenhum secret é hardcoded — todos vêm de variáveis de ambiente.
"""

import logging
import secrets
from typing import Literal

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

    # --- Banco de Dados ---
    database_url: str = "sqlite+aiosqlite:///./licitacao.db"

    # --- Provedor de LLM ---
    llm_provider: Literal["groq", "gemini", "ollama"] = "groq"

    # --- Groq ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # --- Google Gemini ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # --- Ollama ---
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3:32b"

    # --- Embeddings (RAG Fase 4) ---
    # Provedor de embeddings para busca semântica: "gemini" (API) ou "ollama" (local).
    embeddings_provider: Literal["gemini", "ollama"] = "gemini"
    embeddings_model: str = "gemini-embedding-001"
    # Dimensão dos vetores do modelo (gemini-embedding-001 = 3072; bge-m3 = 1024).
    # Usada apenas para validação/report no script de ingestão.
    embeddings_dim: int = 3072

    # --- Aplicação ---
    allowed_origins: str = "http://localhost:3000"
    max_upload_size_mb: int = 50

    # --- Rate Limiting ---
    rate_limit_max: int = 600

    # --- LLM ---
    llm_timeout_seconds: float = 120.0

    # --- Copiloto (Chat Consultivo) ---
    chat_enabled: bool = True
    chat_require_grounding: bool = True
    chat_top_k_sources: int = 5
    chat_max_message_length: int = 2000
    chat_max_sources_stored: int = 8
    chat_force_fake_provider: bool = False

    # --- SMTP (RF04 — envio de pendências por fornecedor) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # --- Segurança ---
    # TODO(security): Em produção, usar secret management (KMS, Vault, etc.)
    # Para o MVP single-user, geramos um token efêmero por instância.
    @property
    def csrf_secret(self) -> str:
        """Gera secret efêmero para CSRF. Seguro para single-instance."""
        if not hasattr(self, "_csrf_secret"):
            self._csrf_secret = secrets.token_hex(32)
            logger.warning(
                "CSRF secret gerado efêmeramente. "
                "Em produção, configure via variável de ambiente."
            )
        return self._csrf_secret

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # Tipos de arquivo permitidos (allowlist)
    ALLOWED_FILE_EXTENSIONS: set[str] = {".pdf", ".docx", ".odt"}
    ALLOWED_MIME_TYPES: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.oasis.opendocument.text",
    }


settings = Settings()
