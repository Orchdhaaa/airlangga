"""Human-in-the-loop notifier.

Approvals (plan approval, spend above threshold, risky tools,
escalations) go to the user. The messaging channel is a small webhook
POST the user configures; the CLI is the fallback — when no webhook is
configured, the approval is printed to stdout and the run pauses until
the user answers in the terminal.
"""

from __future__ import annotations

import httpx

from .http_client import make_http_client


class Notifier:
    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url

    def notify(self, subject: str, body: str) -> str:
        """Send a notification. Returns 'webhook' or 'cli' (fallback)."""
        if self.webhook_url:
            try:
                with make_http_client(10.0) as client:
                    client.post(self.webhook_url, json={"subject": subject, "body": body})
                return "webhook"
            except httpx.HTTPError:
                pass
        print(f"[AIRLANGGA APPROVAL NEEDED] {subject}\n{body}")
        return "cli"

    def ask_human(self, question: str) -> str:
        """Ask the user and return their answer (CLI fallback path)."""
        self.notify("Approval requested", question)
        try:
            return input("Your answer (or 'no' to refuse): ").strip()
        except EOFError:
            return "no"
