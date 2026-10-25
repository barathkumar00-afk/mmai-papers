"""Application configuration.

All configuration is environment-driven (``.env``). No secrets, model paths or
API keys are hard-coded here -- every value has a documented default that can be
overridden through an environment variable or the ``.env`` file.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ``backend/`` directory. All relative paths in ``.env`` resolve against this.
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the MedExplain AI backend."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ server
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    APP_NAME: str = "MedExplain AI Backend"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # ------------------------------------------------------------------ ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:7b"
    OLLAMA_VISION_MODEL: str = ""
    OLLAMA_EMBEDDING_MODEL: str = ""
    OLLAMA_TIMEOUT_SECONDS: float = 120.0
    OLLAMA_CONNECT_TIMEOUT_SECONDS: float = 5.0

    # ------------------------------------------------------------- model mode
    # true  -> deterministic simulated responses, identical response schemas
    # false -> real configured local models
    MOCK_MODE: bool = True

    # ---------------------------------------------------------- speech / ASR
    WHISPER_MODEL_PATH: str = ""
    WHISPER_DEVICE: str = "auto"  # auto | cpu | cuda
    WHISPER_COMPUTE_TYPE: str = "int8"

    # ------------------------------------------------------------ embeddings
    # "ollama"  -> use OLLAMA_BASE_URL /api/embeddings (no torch required)
    # "sentence-transformers" -> local sentence-transformers checkpoint
    # "hashing" -> deterministic dependency-free fallback (no semantics)
    EMBEDDING_PROVIDER: str = "ollama"
    SENTENCE_TRANSFORMER_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 768

    # ------------------------------------------------------------- retrieval
    FAISS_INDEX_PATH: str = "data/indexes/medical.index"
    FAISS_METADATA_PATH: str = "data/indexes/metadata.json"
    KNOWLEDGE_DIR: str = "data/knowledge"
    CHUNK_SIZE: int = 900
    CHUNK_OVERLAP: int = 150
    RETRIEVAL_TOP_K: int = 5
    FAISS_INDEX_TYPE: str = "Flat"  # Flat | HNSW | IVF

    # ---------------------------------------------------------------- uploads
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".png", ".jpg", ".jpeg", ".dcm", ".dicom", ".webp", ".bmp"]
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"]
    MAX_CLINICAL_TEXT_CHARS: int = 20000

    # ------------------------------------------------------------------- cors
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True

    # ------------------------------------------------------------- clinical UI
    # Phrase surfaced in every clinical reasoning response.
    HUMAN_REVIEW_NOTICE: str = (
        "Decision-support output. Requires review by a qualified healthcare professional."
    )
    SAFETY_DISCLAIMER: str = (
        "MedExplain AI is a clinical research prototype providing AI-assisted decision support. "
        "It is not an autonomous diagnostic system, is not a substitute for a qualified "
        "clinician, and must not be used as the sole basis for diagnosis or treatment. "
        "All outputs require review and verification by a licensed healthcare professional."
    )

    # ---------------------------------------------------------------- helpers
    @field_validator("ALLOWED_ORIGINS", "ALLOWED_IMAGE_EXTENSIONS", "ALLOWED_AUDIO_EXTENSIONS", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allow comma-separated env values in addition to JSON lists."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def resolve_path(self, value: str) -> Path:
        """Resolve a possibly-relative configured path against ``backend/``."""
        candidate = Path(value)
        return candidate if candidate.is_absolute() else (BACKEND_ROOT / candidate)

    @property
    def faiss_index_path(self) -> Path:
        return self.resolve_path(self.FAISS_INDEX_PATH)

    @property
    def faiss_metadata_path(self) -> Path:
        return self.resolve_path(self.FAISS_METADATA_PATH)

    @property
    def knowledge_dir(self) -> Path:
        return self.resolve_path(self.KNOWLEDGE_DIR)

    @property
    def whisper_model_path(self) -> Optional[Path]:
        if not self.WHISPER_MODEL_PATH:
            return None
        return self.resolve_path(self.WHISPER_MODEL_PATH)

    @property
    def vision_model(self) -> Optional[str]:
        return self.OLLAMA_VISION_MODEL or None

    @property
    def embedding_model(self) -> Optional[str]:
        return self.OLLAMA_EMBEDDING_MODEL or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()


# Ensure runtime directories exist so FAISS/knowledge paths are always writable.
def ensure_directories() -> None:
    settings = get_settings()
    settings.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
    settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(settings.resolve_path("data/indexes"), exist_ok=True)
