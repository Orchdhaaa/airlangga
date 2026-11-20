"""OpenAI-compatible chat-completions adapter.

Speaks the OpenAI chat-completions wire format. Any endpoint that accepts
it — OpenAI, DeepSeek, OpenRouter, Ollama, vLLM, llama.cpp, a custom
base_url — is reachable through this one adapter.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from .base import ChatMessage, ChatResponse, ModelClient, ToolCall, estimate_tokens
from ..http_client import make_http_client

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatibleClient(ModelClient):
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        super().__init__(model=model, endpoint=base_url or DEFAULT_BASE_URL)
        self._api_key = api_key
        self._http = make_http_client(timeout_s, base_url=base_url or DEFAULT_BASE_URL)

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.as_dict() for m in messages],
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        resp = self._http.post(
            f"{self.endpoint.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]["message"]
        content = choice.get("content") or ""
        tool_calls: list[ToolCall] = []
        for raw in choice.get("tool_calls") or []:
            fn = raw.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {"_raw": fn.get("arguments") or ""}
            tool_calls.append(
                ToolCall(id=raw.get("id", ""), name=fn.get("name", ""), arguments=args)
            )
        usage = data.get("usage") or {}
        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=int(usage.get("prompt_tokens") or estimate_tokens(str(messages))),
            output_tokens=int(usage.get("completion_tokens") or estimate_tokens(content)),
            model=data.get("model", self.model),
            stop_reason=data["choices"][0].get("finish_reason") or "end_turn",
        )

    def close(self) -> None:
        self._http.close()
