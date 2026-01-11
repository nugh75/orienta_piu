"""LLM Providers for Meta Report generation."""

from .base import BaseProvider, ProviderError
from .gemini import GeminiProvider
from .openrouter import OpenRouterProvider
from .ollama import OllamaProvider

def get_provider(name: str = "auto") -> BaseProvider:
    """Get a provider by name. 'auto' tries ollama first, then gemini, then openrouter."""
    providers = {
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
    }

    if name == "auto":
        # Ordine: ollama > gemini > openrouter (ollama locale come default)
        for provider_name in ["ollama", "gemini", "openrouter"]:
            try:
                provider = providers[provider_name]()
                if provider.is_available():
                    return provider
            except Exception:
                continue
        raise ProviderError("No LLM provider available. Set OLLAMA_HOST, GEMINI_API_KEY, or OPENROUTER_API_KEY.")

    if name not in providers:
        raise ProviderError(f"Unknown provider: {name}. Available: {list(providers.keys())}")

    provider = providers[name]()
    if not provider.is_available():
        raise ProviderError(f"Provider {name} is not available. Check configuration.")
    return provider

__all__ = ["BaseProvider", "ProviderError", "GeminiProvider", "OpenRouterProvider", "OllamaProvider", "get_provider"]
