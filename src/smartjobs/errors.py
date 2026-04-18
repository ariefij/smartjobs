from __future__ import annotations


class LLMRequiredError(RuntimeError):
    """Raised when a runtime feature must use OpenAI LLM but no client is configured."""


class LLMResponseFormatError(RuntimeError):
    """Raised when the LLM response does not match the required JSON contract."""
