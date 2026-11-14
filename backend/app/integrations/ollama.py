import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings


class OllamaClient:
    """Minimal HTTP client locked to a local Ollama endpoint."""

    def __init__(self, settings: Settings):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    def status(self, timeout: float = 1.5) -> dict:
        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=timeout) as response:
                payload = json.loads(response.read())
            models = [item.get("name", "") for item in payload.get("models", [])]
            return {"available": True, "model": self.model, "models": models, "error": None}
        except (URLError, TimeoutError, HTTPError, ValueError) as error:
            return {"available": False, "model": self.model, "models": [], "error": str(error)}

    def list_models(self, timeout: float = 1.5) -> list[str]:
        return self.status(timeout=timeout)["models"]

    def generate_json(self, prompt: str, timeout: float = 45) -> dict | None:
        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps({"model": self.model, "prompt": prompt, "format": "json", "stream": False}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read())
            return json.loads(payload["response"])
        except (URLError, TimeoutError, HTTPError, ValueError, KeyError, TypeError):
            return None
