"""Context Builder: assemble each activation's context under a hard
per-role token budget, in priority order.

Priority: contract → pinned decisions → retrieved blackboard slices
(top-k) → recent events. Long content is passed by reference
(``artifact://id`` + abstract), never pasted wholesale. Truncation
leaves a visible "N items omitted" marker; exceeding a role's budget
raises a logged defect alarm (here: a ``ContextBudgetExceeded``).
"""

from __future__ import annotations

from .providers.base import ChatMessage, estimate_tokens


class ContextBudgetExceeded(RuntimeError):
    pass


class ContextBuilder:
    def __init__(self, budget_tokens: int) -> None:
        self.budget_tokens = budget_tokens

    def build(
        self,
        system_prompt: str,
        contract_text: str,
        pinned_decisions: list[str] | None = None,
        blackboard_slices: list[str] | None = None,
        recent_events: list[str] | None = None,
    ) -> list[ChatMessage]:
        sections: list[tuple[str, str]] = [
            ("contract", contract_text),
        ]
        for item in pinned_decisions or []:
            sections.append(("pinned_decision", item))
        for item in blackboard_slices or []:
            sections.append(("blackboard", item))
        for item in recent_events or []:
            sections.append(("event", item))

        used = estimate_tokens(system_prompt)
        messages = [ChatMessage(role="system", content=system_prompt)]
        omitted = 0
        body_parts: list[str] = []
        for kind, text in sections:
            cost = estimate_tokens(text)
            if used + cost > self.budget_tokens:
                omitted += 1
                continue
            used += cost
            body_parts.append(f"[{kind}] {text}")
        if omitted:
            body_parts.append(f"[{omitted} item(s) omitted: context budget reached]")
        if used > self.budget_tokens:
            raise ContextBudgetExceeded(
                f"system prompt alone ({used} tokens) exceeds budget {self.budget_tokens}"
            )
        messages.append(ChatMessage(role="user", content="\n\n".join(body_parts)))
        return messages
