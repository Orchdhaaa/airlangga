"""Mock provider: deterministic, offline, no API key, no network.

Used by the demo run, the replay baseline, and tests. It answers with a
structured JSON report derived from the last user message, so the full
team pipeline can be exercised end to end without any paid service.
"""

from __future__ import annotations

import json
from typing import Any

from .base import ChatMessage, ChatResponse, estimate_tokens, ModelClient


class MockClient(ModelClient):
    def __init__(self, model: str = "mock", role: str = "member") -> None:
        super().__init__(model=model)
        self.role = role

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        prompt = ""
        for msg in reversed(messages):
            if msg.role == "user":
                prompt = msg.content
                break
        in_tokens = sum(estimate_tokens(m.content) for m in messages)
        report = {
            "claims": [
                {
                    "claim": f"Mock {self.role} completed its assigned work for: {prompt[:120]}",
                    "evidence_refs": [],
                    "confidence": 0.8,
                }
            ],
            "open_questions": [],
            "verdict_self": "pass",
        }
        content = json.dumps(report)
        return ChatResponse(
            content=content,
            input_tokens=in_tokens,
            output_tokens=estimate_tokens(content),
            model=self.model,
        )
