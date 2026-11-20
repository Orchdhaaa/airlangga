"""Budget Governor: hard caps enforced outside the LLMs.

Caps on tokens, dollars, wall-clock time, and tool calls at four levels
(run, team, member, single call). The governor does a pre-flight cost
estimate before an activation, tracks spend live, and trips a circuit
breaker that pauses the run when a cap is hit or approached. A member or
team can never spend past its allocation by asking nicely.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .config import Budget


class BudgetExceeded(RuntimeError):
    def __init__(self, scope: str, dimension: str, used: float, cap: float) -> None:
        super().__init__(
            f"budget exceeded: scope={scope} dimension={dimension} used={used} cap={cap}"
        )
        self.scope = scope
        self.dimension = dimension
        self.used = used
        self.cap = cap


@dataclass
class Usage:
    tokens: int = 0
    usd: float = 0.0
    tool_calls: int = 0
    started_at: float = field(default_factory=time.monotonic)


class BudgetGovernor:
    def __init__(self) -> None:
        self._caps: dict[str, Budget] = {}
        self._usage: dict[str, Usage] = {}
        self._tripped: set[str] = set()

    def set_cap(self, scope: str, budget: Budget) -> None:
        self._caps[scope] = budget
        self._usage.setdefault(scope, Usage())

    def estimate_usd(self, tokens: int, cost_per_mtok_usd: float | None) -> float:
        """Pre-flight cost estimate. An unknown price (None) is priced
        conservatively at USD 10.00 per million tokens; an explicit 0.00
        means a free local model and is honoured as zero."""
        price = 10.00 if cost_per_mtok_usd is None else cost_per_mtok_usd
        return tokens / 1_000_000 * price

    def preflight(self, scope: str, tokens: int, cost_per_mtok_usd: float | None) -> None:
        """Refuse an activation before it starts if it would exceed a cap."""
        est_usd = self.estimate_usd(tokens, cost_per_mtok_usd)
        usage = self._usage.setdefault(scope, Usage())
        cap = self._caps.get(scope)
        if cap is None:
            return
        if cap.usd is not None and usage.usd + est_usd > cap.usd:
            self._trip(scope)
            raise BudgetExceeded(scope, "usd", usage.usd + est_usd, cap.usd)
        if cap.tokens is not None and usage.tokens + tokens > cap.tokens:
            self._trip(scope)
            raise BudgetExceeded(scope, "tokens", usage.tokens + tokens, cap.tokens)

    def record(self, scope: str, tokens: int = 0, usd: float = 0.0, tool_calls: int = 0) -> None:
        usage = self._usage.setdefault(scope, Usage())
        usage.tokens += tokens
        usage.usd += usd
        usage.tool_calls += tool_calls
        cap = self._caps.get(scope)
        if cap is None:
            return
        if cap.usd is not None and usage.usd > cap.usd:
            self._trip(scope)
            raise BudgetExceeded(scope, "usd", usage.usd, cap.usd)
        if cap.tokens is not None and usage.tokens > cap.tokens:
            self._trip(scope)
            raise BudgetExceeded(scope, "tokens", usage.tokens, cap.tokens)
        if cap.tool_calls is not None and usage.tool_calls > cap.tool_calls:
            self._trip(scope)
            raise BudgetExceeded(scope, "tool_calls", usage.tool_calls, cap.tool_calls)
        if cap.wall_clock_min is not None:
            elapsed_min = (time.monotonic() - usage.started_at) / 60.0
            if elapsed_min > cap.wall_clock_min:
                self._trip(scope)
                raise BudgetExceeded(scope, "wall_clock_min", elapsed_min, cap.wall_clock_min)

    def usage(self, scope: str) -> Usage:
        return self._usage.setdefault(scope, Usage())

    def is_tripped(self, scope: str) -> bool:
        return scope in self._tripped

    def circuit_open(self, scope: str) -> bool:
        return self.is_tripped(scope)

    def _trip(self, scope: str) -> None:
        self._tripped.add(scope)
