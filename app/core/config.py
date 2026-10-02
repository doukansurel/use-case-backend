import json
import urllib.parse
from functools import lru_cache
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "VisionQC - Kalite Kontrol ve Etiketleme Sistemi API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Database Settings (NeonDB PostgreSQL veya SQLite)
    DATABASE_URL: str = "sqlite+aiosqlite:///./visionqc.db"
    DB_SSL: Optional[bool] = None

    # LLM / Model Provider Settings ("gemini", "openai")
    LLM_PROVIDER: str = "gemini"
    LLM_MAX_RETRIES: int = 2
    PROMPT_VERSION: str = "v2.1"
    ENABLE_HEURISTIC_FALLBACK: bool = False  # Üretimde varsayılan olarak kapalıdır; sahte heuristik sonuçlar yerine FAILED durumuna geçilir.

    # Google Gemini Settings
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "*"
    ]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Optional[str]) -> str:
        if not v:
            return "sqlite+aiosqlite:///./visionqc.db"
        v = v.strip()
        # NeonDB / PostgreSQL standard asyncpg driver normalization
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # asyncpg, URL query string içinde 'sslmode' veya 'channel_binding' kabul etmez
        if "postgresql+asyncpg://" in v and "?" in v:
            base_url, query_str = v.split("?", 1)
            params = urllib.parse.parse_qs(query_str)
            params.pop("sslmode", None)
            params.pop("channel_binding", None)
            if params:
                new_query = urllib.parse.urlencode(params, doseq=True)
                v = f"{base_url}?{new_query}"
            else:
                v = base_url

        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
