"""Google Gemini API adapter (generateContent)."""

from __future__ import annotations

from typing import Any

import httpx

from .base import ChatMessage, ChatResponse, ModelClient, estimate_tokens
from ..http_client import make_http_client

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiClient(ModelClient):
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
        contents: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                continue
            role = "model" if msg.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.content}]})
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        url = f"{BASE_URL}/models/{self.model}:generateContent"
        if self._api_key:
            url += f"?key={self._api_key}"
        resp = self._http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = ""
        for cand in data.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                content += part.get("text", "")
        usage = data.get("usageMetadata") or {}
        return ChatResponse(
            content=content,
            input_tokens=int(usage.get("promptTokenCount") or estimate_tokens(str(messages))),
            output_tokens=int(usage.get("candidatesTokenCount") or estimate_tokens(content)),
            model=self.model,
        )

    def close(self) -> None:
        self._http.close()
