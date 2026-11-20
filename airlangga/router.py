"""Provider Router: route each activation by capability, not by name.

Every model carries capability tags. A role policy declares what it
requires; routing is by purpose with static rules first. Fallback chains
are capability-gated: a fallback that fails the role's required
capabilities is skipped, never used silently. Every switch is a ledger
event (recorded by the caller through ``on_switch``).
"""

from __future__ import annotations

from typing import Callable

from .config import MemberConfig, ModelEndpoint


class NoCapableModel(RuntimeError):
    pass


class Router:
    def __init__(self, on_switch: Callable[[ModelEndpoint, str], None] | None = None) -> None:
        self._on_switch = on_switch

    def route(self, member: MemberConfig) -> ModelEndpoint:
        """Pick the endpoint for one activation of ``member``.

        Pinned model first; on failure to satisfy the role's requirements,
        walk the fallback chain and take the first endpoint that satisfies
        them. A weak fallback is skipped, never used silently.
        """
        # ``require`` is authoritative for the fallback chain.
        required = member.routing_policy.require
        pinned = member.endpoint_record()
        if pinned.satisfies(required):
            return pinned
        for candidate in member.fallback:
            if candidate.satisfies(required):
                if self._on_switch:
                    self._on_switch(
                        candidate,
                        f"pinned model {pinned.model} failed require={required}; "
                        f"fell back to {candidate.provider}/{candidate.model}",
                    )
                return candidate
        raise NoCapableModel(
            f"member {member.id}: no endpoint satisfies require={required}; "
            f"pinned={pinned.provider}/{pinned.model}, "
            f"fallbacks={[f'{f.provider}/{f.model}' for f in member.fallback]}"
        )

    @staticmethod
    def cheapest(endpoints: list[ModelEndpoint]) -> ModelEndpoint:
        return min(endpoints, key=lambda e: e.cost_per_mtok_usd)
