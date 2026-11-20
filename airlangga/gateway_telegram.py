"""Telegram gateway: connect a Telegram bot, receive goals, send status
and approvals.

Small and original: long-polling over the Telegram Bot API with httpx.
The token comes from the environment (``TELEGRAM_BOT_TOKEN``), never
from the repo. Only user IDs on the allowlist are admitted — anyone else
gets no answer at all (default deny). Approvals (plan / spend / risky
tools) are sent to an allowed user and the gateway waits for a yes/no
reply from that user; anything else is not an approval.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import httpx

from .http_client import make_http_client

API_BASE = "https://api.telegram.org"


class TelegramNotConfigured(RuntimeError):
    pass


class TelegramGateway:
    def __init__(
        self,
        token: str | None = None,
        allowed_user_ids: list[int] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise TelegramNotConfigured(
                "TELEGRAM_BOT_TOKEN is not set; set it in the environment, never in the repo"
            )
        self.token = token
        self.allowed_user_ids = set(allowed_user_ids or [])
        self._http = http_client or make_http_client(30.0)
        self._offset = 0

    @property
    def _base(self) -> str:
        return f"{API_BASE}/bot{self.token}"

    # -- low-level API ------------------------------------------------------
    def send_message(self, chat_id: int, text: str) -> dict[str, Any]:
        resp = self._http.post(
            f"{self._base}/sendMessage", json={"chat_id": chat_id, "text": text}
        )
        resp.raise_for_status()
        return resp.json()

    def get_updates(self, timeout_s: int = 10) -> list[dict[str, Any]]:
        resp = self._http.get(
            f"{self._base}/getUpdates",
            params={"offset": self._offset, "timeout": timeout_s},
        )
        resp.raise_for_status()
        updates = resp.json().get("result", [])
        if updates:
            self._offset = max(u["update_id"] for u in updates) + 1
        return updates

    # -- admission + handling ------------------------------------------------
    def is_allowed(self, user_id: int) -> bool:
        return user_id in self.allowed_user_ids

    def handle_update(self, update: dict[str, Any]) -> dict[str, Any] | None:
        """Parse one update. Returns None for non-message updates or for
        users not on the allowlist (default deny: no reply, no action)."""
        message = update.get("message") or {}
        sender = message.get("from") or {}
        user_id = sender.get("id")
        if user_id is None or not self.is_allowed(int(user_id)):
            return None
        text = (message.get("text") or "").strip()
        return {
            "user_id": int(user_id),
            "chat_id": int(message["chat"]["id"]),
            "text": text,
            "kind": "goal" if text.startswith("/goal ") else "command" if text.startswith("/") else "message",
            "goal": text[len("/goal "):].strip() if text.startswith("/goal ") else "",
        }

    def request_approval(
        self,
        chat_id: int,
        question: str,
        poll: Callable[[], list[dict[str, Any]]] | None = None,
        max_polls: int = 30,
    ) -> bool:
        """Ask an allowed user for approval and wait for a yes/no reply.

        Sends the question, then polls for updates. Returns True only on
        an explicit yes from an allowed user; anything else (no, timeout,
        a reply from a non-allowed user) is a refusal.
        """
        self.send_message(
            chat_id,
            f"Approval requested:\n{question}\nReply YES to approve, NO to refuse.",
        )
        poll_fn = poll or (lambda: self.get_updates(timeout_s=10))
        for _ in range(max_polls):
            for update in poll_fn():
                parsed = self.handle_update(update)
                if parsed is None or parsed["chat_id"] != chat_id:
                    continue
                answer = parsed["text"].strip().lower()
                if answer in ("yes", "y", "/approve", "approve"):
                    return True
                if answer in ("no", "n", "/deny", "deny"):
                    return False
        return False

    def poll_loop(
        self,
        on_goal: Callable[[dict[str, Any]], str],
        max_iterations: int | None = None,
    ) -> None:
        """Long-poll for goals. ``on_goal`` receives a parsed update and
        returns the reply text, which is sent back to the user."""
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            iterations += 1
            for update in self.get_updates(timeout_s=10):
                parsed = self.handle_update(update)
                if parsed is None:
                    continue
                if parsed["kind"] == "goal":
                    reply = on_goal(parsed)
                    self.send_message(parsed["chat_id"], reply)
                elif parsed["kind"] == "command":
                    self.send_message(
                        parsed["chat_id"],
                        "Send a goal with: /goal <your goal>",
                    )

    def close(self) -> None:
        self._http.close()
