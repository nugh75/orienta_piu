"""LLM Providers for Meta Report generation."""

import os
from typing import Optional

from .base import BaseProvider, ProviderError
from .gemini import GeminiProvider
from .openrouter import OpenRouterProvider
from .ollama import OllamaProvider


def get_provider(name: str = "auto", model: Optional[str] = None) -> BaseProvider:
    """Get a provider by name with optional model override.
    
    Args:
        name: Provider name ('ollama', 'openrouter', 'gemini', or 'auto')
        model: Optional model name override
        
    Returns:
        Configured provider instance
    """
    if name == "auto":
        # Ordine: ollama > gemini > openrouter (ollama locale come default)
        for provider_name in ["ollama", "gemini", "openrouter"]:
            try:
                provider = get_provider(provider_name, model)
                if provider.is_available():
                    return provider
            except Exception:
                continue
        raise ProviderError("No LLM provider available. Set OLLAMA_HOST, GEMINI_API_KEY, or OPENROUTER_API_KEY.")

    if name == "ollama":
        ollama_model = model or os.getenv("OLLAMA_MODEL", "gemma3:27b")
        return OllamaProvider(model=ollama_model)
    
    elif name == "openrouter":
        openrouter_model = model or os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-001")
        return OpenRouterProvider(model=openrouter_model)
    
    elif name == "gemini":
        gemini_model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        return GeminiProvider(model=gemini_model)
    
    else:
        raise ProviderError(f"Unknown provider: {name}. Available: ollama, openrouter, gemini")


def get_provider_for_slot(slot_type: str, provider_school: str = "ollama", provider_synthesis: str = "openrouter",
                          model_school: Optional[str] = None, model_synthesis: Optional[str] = None) -> BaseProvider:
    """Get the appropriate provider for a slot type.
    
    Args:
        slot_type: Type of slot (school_analysis, synthesis, etc.)
        provider_school: Provider name for school-level calls
        provider_synthesis: Provider name for synthesis calls
        model_school: Model for school-level calls
        model_synthesis: Model for synthesis calls
        
    Returns:
        Configured provider for the slot type
    """
    # Slot types that use synthesis provider
    synthesis_slots = {"intro_generale", "synthesis", "comparison", "territorial", "conclusion"}
    
    if slot_type in synthesis_slots:
        return get_provider(provider_synthesis, model_synthesis)
    else:
        return get_provider(provider_school, model_school)


__all__ = [
    "BaseProvider", 
    "ProviderError", 
    "GeminiProvider", 
    "OpenRouterProvider", 
    "OllamaProvider", 
    "get_provider",
    "get_provider_for_slot",
]

