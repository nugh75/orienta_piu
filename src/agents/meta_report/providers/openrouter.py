"""OpenRouter provider."""

import os
from typing import Optional

from .base import BaseProvider, LLMResponse, ProviderError


class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider."""

    name = "openrouter"
    
    # Recommended chunk size for this provider
    recommended_chunk_size = 40

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-3-haiku",
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model
        self.base_url = base_url

    def is_available(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text using OpenRouter."""
        if not self.is_available():
            raise ProviderError("OpenRouter API key not configured. Set OPENROUTER_API_KEY.")

        try:
            import httpx
        except ImportError:
            raise ProviderError("httpx not installed. Run: pip install httpx")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://orientapiu.it",
                        "X-Title": "OrientaPiu Meta Report",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 4096,
                    },
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.name,
                tokens_used=usage.get("total_tokens"),
            )

        except httpx.HTTPError as e:
            raise ProviderError(f"OpenRouter API error: {e}")
        except (KeyError, IndexError) as e:
            raise ProviderError(f"Invalid OpenRouter response: {e}")
