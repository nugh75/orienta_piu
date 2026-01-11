"""Prompt components and examples for meta report generation."""

from .examples import EXAMPLES, get_example
from .components import (
    COMMON_RULES,
    CITATION_RULES,
    NARRATIVE_STYLE,
    NO_MARKDOWN_HEADERS,
    WITH_MARKDOWN_HEADERS,
    compose_prompt,
)

__all__ = [
    "EXAMPLES",
    "get_example",
    "COMMON_RULES",
    "CITATION_RULES",
    "NARRATIVE_STYLE",
    "NO_MARKDOWN_HEADERS",
    "WITH_MARKDOWN_HEADERS",
    "compose_prompt",
]
