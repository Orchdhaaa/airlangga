"""Router (capability-gated fallbacks), Budget Governor, Policy Engine."""

import pytest

from airlangga.budget import BudgetExceeded, BudgetGovernor
from airlangga.config import Budget, MemberConfig, ModelEndpoint
from airlangga.policy import MemberPolicy, PolicyEngine, ToolCallRequest
from airlangga.router import NoCapableModel, Router


def _member(**overrides):
    data = {
        "id": "m1",
        "role": "researcher",
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "wire_format": "anthropic_messages",
        "capabilities": ["tool_calling", "structured_json"],
        "routing_policy": {"require": ["tool_calling", "structured_json"]},
    }
    data.update(overrides)
    return MemberConfig(**data)


def test_router_uses_pinned_when_capable():
    router = Router()
    endpoint = router.route(_member())
    assert endpoint.model == "claude-sonnet-4-5"


def test_router_skips_weak_fallback():
    weak = ModelEndpoint(
        provider="ollama", model="tiny", wire_format="openai_chat",
        capabilities=["structured_json"],  # missing tool_calling
    )
    strong = ModelEndpoint(
        provider="openai", model="gpt-5-mini", wire_format="openai_chat",
        capabilities=["tool_calling", "structured_json"],
    )
    member = _member(capabilities=[], fallback=[weak, strong])
    endpoint = router_route(member)
    assert endpoint.model == "gpt-5-mini"


def router_route(member):
    switches = []
    router = Router(on_switch=lambda ep, reason: switches.append((ep.model, reason)))
    endpoint = router.route(member)
    assert switches, "a fallback switch must be logged"
    return endpoint


def test_router_raises_when_no_capable_model():
    weak = ModelEndpoint(
        provider="ollama", model="tiny", wire_format="openai_chat",
        capabilities=["structured_json"],
    )
    member = _member(capabilities=[], fallback=[weak])
    with pytest.raises(NoCapableModel):
        Router().route(member)


def test_budget_governor_caps_and_circuit_breaker():
    gov = BudgetGovernor()
    gov.set_cap("member:m1", Budget(tokens=100, usd=1.00, tool_calls=5))
    gov.record("member:m1", tokens=50, usd=0.40, tool_calls=2)
    assert gov.usage("member:m1").tokens == 50
    assert gov.is_tripped("member:m1") is False
    with pytest.raises(BudgetExceeded):
        gov.record("member:m1", tokens=60, usd=0.10)
    assert gov.circuit_open("member:m1") is True


def test_budget_preflight_blocks_expensive_activation():
    gov = BudgetGovernor()
    gov.set_cap("member:m1", Budget(usd=0.01))
    with pytest.raises(BudgetExceeded):
        gov.preflight("member:m1", tokens=100_000, cost_per_mtok_usd=3.00)


def test_policy_denies_unlisted_tool_and_hardline():
    engine = PolicyEngine()
    policy = MemberPolicy(allowed_tools=["web_search"], approval_required=[])
    denied = engine.check(policy, ToolCallRequest("shell", {"cmd": "ls"}, "m1"))
    assert denied.allowed is False
    hardline = engine.check(
        MemberPolicy(allowed_tools=["shell"], approval_required=[]),
        ToolCallRequest("shell", {"cmd": "rm -rf /"}, "m1"),
    )
    assert hardline.allowed is False


def test_policy_write_denied_and_approval_required():
    engine = PolicyEngine()
    policy = MemberPolicy(
        allowed_tools=["write_file", "external_post"],
        approval_required=["external_post"],
        write_root="/tmp/run",
    )
    assert engine.check(
        policy, ToolCallRequest("write_file", {"path": "/home/user/.ssh/id_rsa"}, "m1")
    ).allowed is False
    assert engine.check(
        policy, ToolCallRequest("write_file", {"path": "/tmp/run/out.md"}, "m1")
    ).allowed is True
    decision = engine.check(
        policy, ToolCallRequest("external_post", {"text": "hi"}, "m1")
    )
    assert decision.allowed is True and decision.needs_approval is True
