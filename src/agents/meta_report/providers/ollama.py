"""Ollama local provider."""

import os
from typing import Optional

from .base import BaseProvider, LLMResponse, ProviderError


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider."""

    name = "ollama"

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.host = host or os.getenv("OLLAMA_HOST", "http://192.168.129.14:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:32b")

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text using Ollama."""
        try:
            import httpx
        except ImportError:
            raise ProviderError("httpx not installed. Run: pip install httpx")

        try:
            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": system_prompt or "",
                        "stream": False,
                        "options": {
                            "num_ctx": 8192,
                            "temperature": 0.7,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

            return LLMResponse(
                content=data.get("response", ""),
                model=self.model,
                provider=self.name,
                tokens_used=data.get("eval_count"),
            )

        except Exception as e:
            raise ProviderError(f"Ollama error: {e}")
