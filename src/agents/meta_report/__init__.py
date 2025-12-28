"""
Meta Report Agent - Best Practices Reporter

Generates incremental reports on best practices from PTOF analyses.
Supports multiple LLM providers: Gemini, OpenRouter, Ollama.
"""

from .orchestrator import MetaReportOrchestrator
from .registry import MetaReportRegistry

__all__ = ["MetaReportOrchestrator", "MetaReportRegistry"]
