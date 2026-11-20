"""Turn Loop: our own single-agent loop, written from first principles.

Assemble messages → call the model → dispatch tool calls → feed tool
results back → repeat until a stop condition. Retry with backoff,
recovery from a failed tool call, and overflow handling (drop the oldest
non-system messages when the window fills) are runtime concerns, not
prompt instructions. Team behaviour lives in the Team Runtime above
this loop, not inside it.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from .budget import BudgetGovernor, BudgetExceeded
from .policy import MemberPolicy, PolicyEngine, ToolCallRequest
from .providers.base import ChatMessage, ChatResponse, ModelClient, estimate_tokens

ToolFn = Callable[[dict[str, Any]], str]


class TurnResult:
    def __init__(self, content: str, usage: dict[str, int], tool_calls: int, turns: int) -> None:
        self.content = content
        self.usage = usage
        self.tool_calls = tool_calls
        self.turns = turns


class TurnLoop:
    def __init__(
        self,
        client: ModelClient,
        tools: dict[str, ToolFn] | None = None,
        tool_schemas: list[dict[str, Any]] | None = None,
        max_turns: int = 10,
        context_limit: int = 128_000,
        policy: MemberPolicy | None = None,
        policy_engine: PolicyEngine | None = None,
        actor: str = "member",
        budget: BudgetGovernor | None = None,
        budget_scope: str | None = None,
        on_denied: Callable[[str], None] | None = None,
    ) -> None:
        self.client = client
        self.tools = tools or {}
        self.tool_schemas = tool_schemas or []
        self.max_turns = max_turns
        self.context_limit = context_limit
        self.policy = policy
        self.policy_engine = policy_engine or PolicyEngine()
        self.actor = actor
        self.budget = budget
        self.budget_scope = budget_scope
        self.on_denied = on_denied

    def _compact(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        """Overflow handling: drop oldest non-system messages until the
        window fits, keeping a visible marker of what was dropped."""
        total = sum(estimate_tokens(m.content) for m in messages)
        if total <= self.context_limit:
            return messages
        kept = [m for m in messages if m.role == "system"]
        rest = [m for m in messages if m.role != "system"]
        dropped = 0
        while rest and sum(estimate_tokens(m.content) for m in kept + rest) > self.context_limit:
            rest.pop(0)
            dropped += 1
        if dropped:
            kept.append(
                ChatMessage(
                    role="user",
                    content=f"[{dropped} earlier message(s) compacted: context window reached]",
                )
            )
        return kept + rest

    def run(self, messages: list[ChatMessage]) -> TurnResult:
        history = list(messages)
        total_in = total_out = 0
        tool_calls_made = 0
        last_content = ""
        for _turn in range(1, self.max_turns + 1):
            history = self._compact(history)
            response = self._call_with_retry(history)
            total_in += response.input_tokens
            total_out += response.output_tokens
            last_content = response.content
            if self.budget and self.budget_scope:
                try:
                    self.budget.record(
                        self.budget_scope,
                        tokens=response.total_tokens,
                        usd=0.0,
                        tool_calls=len(response.tool_calls),
                    )
                except BudgetExceeded:
                    raise
            if not response.tool_calls:
                break
            for call in response.tool_calls:
                tool_calls_made += 1
                result = self._dispatch(call.name, call.arguments)
                history.append(
                    ChatMessage(role="assistant", content=response.content or "", name=call.name)
                )
                history.append(
                    ChatMessage(role="tool", content=result, tool_call_id=call.id, name=call.name)
                )
        return TurnResult(
            content=last_content,
            usage={"input_tokens": total_in, "output_tokens": total_out},
            tool_calls=tool_calls_made,
            turns=self.max_turns,
        )

    def _call_with_retry(self, messages: list[ChatMessage], attempts: int = 3) -> ChatResponse:
        delay = 1.0
        last_exc: Exception | None = None
        for _ in range(attempts):
            try:
                return self.client.chat(messages, tools=self.tool_schemas or None)
            except Exception as exc:  # provider outage / rate limit: back off
                last_exc = exc
                time.sleep(delay)
                delay *= 2
        assert last_exc is not None
        raise last_exc

    def _dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        if self.policy is not None:
            decision = self.policy_engine.check(
                self.policy, ToolCallRequest(name=name, arguments=arguments, actor=self.actor)
            )
            if not decision.allowed:
                if self.on_denied:
                    self.on_denied(f"denied tool call {name}: {decision.reason}")
                return f"POLICY_DENIED: {decision.reason}"
            if decision.needs_approval:
                return f"APPROVAL_REQUIRED: {decision.reason}"
        fn = self.tools.get(name)
        if fn is None:
            return f"TOOL_ERROR: no tool named {name!r}"
        try:
            return str(fn(arguments))
        except Exception as exc:  # recovery: a failed tool call is a result, not a crash
            return f"TOOL_ERROR: {name} failed: {exc}"
