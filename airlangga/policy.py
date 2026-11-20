"""Policy Engine: per-role tool allowlists, enforced at the tool-call
boundary — before the call executes.

Scopes are set by the team template / Main Brain and signed into the
contract. A member cannot grant itself tools; neither can a Team Brain.
Every denied call is logged by the caller (the turn loop records it in
the ledger). Approvals go to a human, never to a Brain.
"""

from __future__ import annotations

from dataclasses import dataclass

from .guardrails import is_hardline, is_write_denied


@dataclass
class ToolCallRequest:
    name: str
    arguments: dict
    actor: str  # member id


@dataclass
class PolicyDecision:
    allowed: bool
    needs_approval: bool = False
    reason: str = ""


@dataclass
class MemberPolicy:
    allowed_tools: list[str]
    approval_required: list[str]
    write_root: str | None = None  # agent writes land only inside this root
    network_allow: list[str] | None = None


class PolicyEngine:
    def check(self, policy: MemberPolicy, call: ToolCallRequest) -> PolicyDecision:
        # Layer 1: the hardline floor can never be overridden.
        action_text = call.name + " " + " ".join(str(v) for v in call.arguments.values())
        matched = is_hardline(action_text)
        if matched:
            return PolicyDecision(False, False, f"hardline denylist matched: {matched}")

        if call.name not in policy.allowed_tools:
            return PolicyDecision(
                False, False, f"tool {call.name!r} is not in member {call.actor}'s allowlist"
            )

        # Layer 2: file-write safety.
        if call.name in ("write_file", "patch_file"):
            path = str(call.arguments.get("path", ""))
            if is_write_denied(path):
                return PolicyDecision(False, False, f"write to denied path: {path}")
            if policy.write_root and not path.startswith(policy.write_root):
                return PolicyDecision(
                    False, False, f"write outside run workspace: {path}"
                )

        if call.name in policy.approval_required:
            return PolicyDecision(True, True, f"tool {call.name!r} requires human approval")

        return PolicyDecision(True, False, "allowed")
