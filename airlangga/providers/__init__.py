"""Provider abstraction: talk to any LLM over one interface.

A vendor is a named endpoint record that speaks one wire format
(``openai_chat``, ``anthropic_messages``, ``gemini``, ``mock``). Adding a
vendor means adding an endpoint record, not new code.
"""

from .base import ChatMessage, ChatResponse, ModelClient, ToolCall, estimate_tokens
from .factory import build_client
from .mock import MockClient

__all__ = [
    "ChatMessage",
    "ChatResponse",
    "ModelClient",
    "ToolCall",
    "build_client",
    "estimate_tokens",
    "MockClient",
]
