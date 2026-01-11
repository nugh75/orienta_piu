"""Ollama local provider."""

import os
import time
from typing import Optional

from .base import BaseProvider, LLMResponse, ProviderError


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider with retry and dynamic chunk sizing.

    Ottimizzato per modelli locali 27B con:
    - Context window configurabile (default 16384)
    - Chunk size ridotto per migliore qualità
    - Temperature più bassa per coerenza
    """

    name = "ollama"

    # Recommended chunk size for this provider (ridotto per modelli locali)
    recommended_chunk_size = 15  # Era 25

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.host = host or os.getenv("OLLAMA_HOST", "http://192.168.129.14:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:32b")
        self.max_retries = max_retries
        self.retry_delay = retry_delay

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
        """Generate text using Ollama with retry and exponential backoff."""
        try:
            import httpx
        except ImportError:
            raise ProviderError("httpx not installed. Run: pip install httpx")

        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
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
                                "num_ctx": int(os.getenv("META_REPORT_OLLAMA_CTX", "16384")),
                                "temperature": 0.5,  # Ridotta per maggiore coerenza
                                "top_p": 0.9,
                                "repeat_penalty": 1.1,  # Evita ripetizioni
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
                last_error = e
                if attempt < self.max_retries:
                    # Exponential backoff: 2s, 4s, 8s...
                    wait_time = self.retry_delay * (2 ** (attempt - 1))
                    print(f"[ollama] Attempt {attempt}/{self.max_retries} failed: {e}")
                    print(f"[ollama] Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    print(f"[ollama] All {self.max_retries} attempts failed")

        raise ProviderError(f"Ollama error after {self.max_retries} retries: {last_error}")
