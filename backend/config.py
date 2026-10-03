from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name, "1" if default else "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _csv(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


@dataclass(frozen=True)
class Settings:
    ncbi_email: str = _env("NCBI_EMAIL", "alexxc@live.se")
    ncbi_tool: str = _env("NCBI_TOOL", "MED-R5")
    ncbi_api_key: str = _env("NCBI_API_KEY", "")
    lm_studio_url: str = _env("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
    lm_model: str = _env("LM_MODEL", "local-model")
    lm_temperature: float = float(_env("LM_TEMPERATURE", "0.2"))
    lm_max_tokens: int = int(_env("LM_MAX_TOKENS", "900"))
    evidence_db_path: str = _env("EVIDENCE_DB_PATH", "")
    cors_allow_origins: list[str] = tuple(_csv(_env("CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173")))
    cors_allow_credentials: bool = _env_bool("CORS_ALLOW_CREDENTIALS", False)
    cors_allow_methods: list[str] = tuple(_csv(_env("CORS_ALLOW_METHODS", "GET,POST,OPTIONS")))
    cors_allow_headers: list[str] = tuple(_csv(_env("CORS_ALLOW_HEADERS", "*")))


SETTINGS = Settings()
