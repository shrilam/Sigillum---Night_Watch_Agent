"""Environment-backed settings for local Nightwatch development."""

from dataclasses import dataclass
import os
from collections.abc import Mapping
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./data/nightwatch.db"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5-coder:7b"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        values = os.environ if environ is None else environ
        try:
            port = int(values.get("NIGHTWATCH_PORT", "8000"))
        except ValueError as error:
            raise ValueError("NIGHTWATCH_PORT must be an integer") from error
        if not 1 <= port <= 65535:
            raise ValueError("NIGHTWATCH_PORT must be between 1 and 65535")

        host = values.get("NIGHTWATCH_HOST", "127.0.0.1")
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("NIGHTWATCH_HOST must be a loopback address")

        ollama_base_url = values.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        parsed_ollama_url = urlsplit(ollama_base_url)
        if parsed_ollama_url.scheme != "http" or parsed_ollama_url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("OLLAMA_BASE_URL must use HTTP on a loopback address")

        return cls(
            host=host,
            port=port,
            database_url=values.get("NIGHTWATCH_DATABASE_URL", "sqlite:///./data/nightwatch.db"),
            ollama_base_url=ollama_base_url,
            ollama_model=values.get("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        )
