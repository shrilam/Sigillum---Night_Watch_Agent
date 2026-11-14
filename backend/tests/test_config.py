import pytest

from app.core.config import Settings


def test_settings_default_to_local_only_runtime() -> None:
    settings = Settings.from_env({})

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.database_url == "sqlite:///./data/nightwatch.db"
    assert settings.ollama_base_url == "http://127.0.0.1:11434"


def test_settings_accept_loopback_override() -> None:
    settings = Settings.from_env({"NIGHTWATCH_HOST": "localhost", "NIGHTWATCH_PORT": "8123"})

    assert settings.host == "localhost"
    assert settings.port == 8123


def test_settings_reject_non_loopback_bind() -> None:
    with pytest.raises(ValueError, match="loopback"):
        Settings.from_env({"NIGHTWATCH_HOST": "0.0.0.0"})


def test_settings_reject_invalid_port() -> None:
    with pytest.raises(ValueError, match="between 1 and 65535"):
        Settings.from_env({"NIGHTWATCH_PORT": "70000"})


def test_settings_reject_remote_ollama_endpoint() -> None:
    with pytest.raises(ValueError, match="loopback"):
        Settings.from_env({"OLLAMA_BASE_URL": "https://example.com"})
