"""Google Gemini provider."""

import os
from typing import Optional

from .base import BaseProvider, LLMResponse, ProviderError


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self._client = None

    def is_available(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.api_key)

    def _get_client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ProviderError("google-generativeai not installed. Run: pip install google-generativeai")
        return self._client

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text using Gemini."""
        if not self.is_available():
            raise ProviderError("Gemini API key not configured. Set GEMINI_API_KEY.")

        client = self._get_client()

        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"

            response = client.generate_content(full_prompt)

            return LLMResponse(
                content=response.text,
                model=self.model,
                provider=self.name,
                tokens_used=None,  # Gemini doesn't always provide this
            )

        except Exception as e:
            raise ProviderError(f"Gemini API error: {e}")
