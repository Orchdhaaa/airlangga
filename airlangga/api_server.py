"""OpenAI-compatible API server stub (stdlib http.server, no new deps).

Endpoints:
- ``GET /v1/models`` — lists model aliases. Each alias routes to a team
  member (``airlangga/<team>/<member>``), plus ``airlangga/main-brain``.
- ``POST /v1/chat/completions`` — an OpenAI-shaped chat request. The
  ``model`` field names an alias; the request is answered by that
  member's configured provider through our own provider abstraction
  (mock provider when the config uses it — the offline path).

This is a v1 stub: single-process, no auth beyond the local bind
(default 127.0.0.1), no streaming. Admission control (an API key /
allowlist) is a v2 hardening item; do not expose it publicly as-is.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import AirlanggaConfig
from .providers import build_client
from .providers.base import ChatMessage


def model_aliases(config: AirlanggaConfig) -> list[dict[str, Any]]:
    aliases = [{"id": "airlangga/main-brain", "object": "model", "owned_by": "airlangga"}]
    for team_name, team in config.teams.items():
        for member in team.members:
            aliases.append(
                {
                    "id": f"airlangga/{team_name}/{member.id}",
                    "object": "model",
                    "owned_by": "airlangga",
                    "provider": member.provider,
                    "model": member.model,
                }
            )
    return aliases


def _answer(config: AirlanggaConfig, model_alias: str, messages: list[dict[str, Any]]) -> str:
    """Answer a chat request through the aliased member's provider."""
    endpoint = None
    role = "member"
    if model_alias == "airlangga/main-brain":
        main = config.main_brain
        from .config import ModelEndpoint

        endpoint = ModelEndpoint(
            provider=main.provider, model=main.model, endpoint=main.endpoint,
            auth_ref=main.auth_ref, wire_format=main.wire_format,
            capabilities=main.capabilities, cost_per_mtok_usd=main.cost_per_mtok_usd,
        )
        role = "main_brain"
    else:
        parts = model_alias.split("/")
        if len(parts) == 3 and parts[0] == "airlangga":
            member = next(
                (m for m in config.teams[parts[1]].members if m.id == parts[2]), None
            )
            if member is not None:
                endpoint = member.endpoint_record()
                role = member.role
    if endpoint is None:
        raise ValueError(f"unknown model alias: {model_alias!r}")
    client = build_client(endpoint, role=role)
    try:
        response = client.chat(
            [ChatMessage(role=m.get("role", "user"), content=m.get("content", "")) for m in messages]
        )
        return response.content
    finally:
        client.close()


def make_handler(config: AirlanggaConfig) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:  # keep test output quiet
            return None

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/v1/models":
                self._send_json(200, {"object": "list", "data": model_aliases(config)})
            elif self.path == "/health":
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/v1/chat/completions":
                self._send_json(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                content = _answer(
                    config, str(payload.get("model", "")), list(payload.get("messages", []))
                )
            except (ValueError, KeyError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:  # provider failure surfaces as 502
                self._send_json(502, {"error": f"provider error: {exc}"})
                return
            self._send_json(
                200,
                {
                    "id": "chatcmpl-airlangga",
                    "object": "chat.completion",
                    "model": payload.get("model", ""),
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
                    ],
                },
            )

    return Handler


def run_server(
    config: AirlanggaConfig, host: str = "127.0.0.1", port: int = 8765
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(config))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
