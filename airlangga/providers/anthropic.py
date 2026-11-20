"""Anthropic Messages API adapter."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .base import ChatMessage, ChatResponse, ModelClient, ToolCall, estimate_tokens
from ..http_client import make_http_client

BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicClient(ModelClient):
    def __init__(
        self, model: str, api_key: str | None = None, timeout_s: float = 120.0
    ) -> None:
        super().__init__(model=model, endpoint=BASE_URL)
        self._api_key = api_key
        self._http = make_http_client(timeout_s, base_url=BASE_URL)

    def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        system = ""
        rest: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                system += msg.content + "\n"
            else:
                rest.append({"role": msg.role, "content": msg.content})
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": rest,
        }
        if system.strip():
            payload["system"] = system.strip()
        if tools:
            payload["tools"] = [
                {"name": t["name"], "description": t.get("description", ""), "input_schema": t.get("parameters", {"type": "object", "properties": {}})}
                for t in tools
            ]
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_key or "",
            "anthropic-version": ANTHROPIC_VERSION,
        }
        resp = self._http.post(f"{BASE_URL}/messages", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = ""
        tool_calls: list[ToolCall] = []
        for block in data.get("content") or []:
            if block.get("type") == "text":
                content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=block.get("input") or {},
                    )
                )
        usage = data.get("usage") or {}
        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=int(usage.get("input_tokens") or estimate_tokens(str(messages))),
            output_tokens=int(usage.get("output_tokens") or estimate_tokens(content)),
            model=data.get("model", self.model),
            stop_reason=data.get("stop_reason") or "end_turn",
        )

    def close(self) -> None:
        self._http.close()
