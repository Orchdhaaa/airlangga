"""Provider base types. Original design; wire-format adapters live in
``openai_compat.py``, ``anthropic.py``, ``gemini.py`` and ``mock.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def estimate_tokens(text: str) -> int:
    """Cheap, deterministic token estimate (about 4 characters per token)."""
    return max(1, len(text) // 4)


@dataclass
class ChatMessage:
    role: str  # system | user | assistant | tool
    content: str
    tool_call_id: str | None = None
    name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            out["tool_call_id"] = self.tool_call_id
        if self.name:
            out["name"] = self.name
        return out


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = "end_turn"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ModelClient:
    """One activation's view of one model endpoint."""

    def __init__(self, model: str, endpoint: str | None = None) -> None:
        self.model = model
        self.endpoint = endpoint

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        raise NotImplementedError

    def close(self) -> None:
        return None
