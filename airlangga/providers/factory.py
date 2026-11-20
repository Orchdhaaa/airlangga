"""Build a model client from an endpoint record."""

from __future__ import annotations

from ..config import ModelEndpoint, resolve_auth_ref
from .anthropic import AnthropicClient
from .base import ModelClient
from .gemini import GeminiClient
from .mock import MockClient
from .openai_compat import OpenAICompatibleClient


def build_client(endpoint: ModelEndpoint, role: str = "member") -> ModelClient:
    """Dispatch on wire format, not on vendor name."""
    if endpoint.wire_format == "mock":
        return MockClient(model=endpoint.model, role=role)
    api_key = resolve_auth_ref(endpoint.auth_ref) if endpoint.auth_ref != "none" else None
    if endpoint.wire_format == "anthropic_messages":
        return AnthropicClient(model=endpoint.model, api_key=api_key)
    if endpoint.wire_format == "gemini":
        return GeminiClient(model=endpoint.model, api_key=api_key)
    # openai_chat is the default wire format for every OpenAI-compatible
    # endpoint: official APIs, custom base URLs, and local servers alike.
    return OpenAICompatibleClient(
        model=endpoint.model, base_url=endpoint.endpoint, api_key=api_key
    )
