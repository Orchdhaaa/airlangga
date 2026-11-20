"""Configuration: loading and validating ``airlangga.yaml``.

The config schema is Airlangga's own. A config names the Main Brain, the
teams, and each member's pinned model endpoint. Secrets are never stored
here: ``auth_ref`` is a reference (``env:VAR``, ``none``) resolved at run
time, never a literal key.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class Budget(BaseModel):
    """Hard spending caps. Any field left unset means 'no cap at this level'."""

    tokens: int | None = None
    usd: float | None = None
    wall_clock_min: float | None = None
    tool_calls: int | None = None


class ModelEndpoint(BaseModel):
    """One model endpoint: where to call, how to authenticate, which wire
    format it speaks, and what it can do / costs. A vendor is just a named
    endpoint that speaks one of the wire formats in providers.py."""

    provider: str
    model: str
    endpoint: str | None = None
    auth_ref: str = "none"
    wire_format: Literal["openai_chat", "anthropic_messages", "gemini", "mock"] = (
        "openai_chat"
    )
    capabilities: list[str] = Field(default_factory=list)
    context_limit: int = 128_000
    cost_per_mtok_usd: float = 0.0

    def satisfies(self, required: list[str]) -> bool:
        """True when every required capability tag is present."""
        return all(cap in self.capabilities for cap in required)


class RoutingPolicy(BaseModel):
    require: list[str] = Field(default_factory=list)
    prefer: str = "cheapest_above_quality_floor"


class MemberConfig(BaseModel):
    id: str
    role: str
    provider: str
    model: str
    endpoint: str | None = None
    auth_ref: str = "none"
    wire_format: Literal["openai_chat", "anthropic_messages", "gemini", "mock"] = (
        "openai_chat"
    )
    capabilities: list[str] = Field(default_factory=list)
    context_limit: int = 128_000
    cost_per_mtok_usd: float = 0.0
    toolsets: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    # Files attached to this member (paths under the project files root).
    # charter_file is the persona/charter text the member is built from —
    # e.g. a user-written SUPERAGENT file. Files are first-class: the user
    # creates/edits them in the web UI and attaches them here.
    charter_file: str | None = None
    attached_files: list[str] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    approval: Literal["smart", "approve", "off"] = "smart"
    fallback: list[ModelEndpoint] = Field(default_factory=list)
    routing_policy: RoutingPolicy = Field(default_factory=RoutingPolicy)

    def endpoint_record(self) -> ModelEndpoint:
        return ModelEndpoint(
            provider=self.provider,
            model=self.model,
            endpoint=self.endpoint,
            auth_ref=self.auth_ref,
            wire_format=self.wire_format,
            capabilities=self.capabilities,
            context_limit=self.context_limit,
            cost_per_mtok_usd=self.cost_per_mtok_usd,
        )


class MainBrainConfig(BaseModel):
    provider: str = "mock"
    model: str = "mock-main"
    auth_ref: str = "none"
    wire_format: Literal["openai_chat", "anthropic_messages", "gemini", "mock"] = (
        "mock"
    )
    endpoint: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    context_limit: int = 128_000
    cost_per_mtok_usd: float = 0.0
    max_tokens_per_call: int = 4096
    budget: Budget = Field(default_factory=Budget)
    tools: list[str] = Field(
        default_factory=lambda: [
            "plan",
            "assign",
            "reallocate_budget",
            "accept",
            "reject",
            "ask_human",
            "finalize",
        ]
    )


class TeamConfig(BaseModel):
    template: str = "research"
    goal: str = ""
    team_budget: Budget = Field(default_factory=Budget)
    team_brain_mode: Literal["lead_member", "separate"] = "lead_member"
    lead_member: str | None = None
    members: list[MemberConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def _lead_must_exist(self) -> "TeamConfig":
        if self.team_brain_mode == "lead_member" and self.lead_member:
            ids = {m.id for m in self.members}
            if self.lead_member not in ids:
                raise ValueError(
                    f"lead_member '{self.lead_member}' is not in the roster {sorted(ids)}"
                )
        return self


class AirlanggaConfig(BaseModel):
    version: int = 1
    defaults: dict[str, Any] = Field(default_factory=dict)
    main_brain: MainBrainConfig = Field(default_factory=MainBrainConfig)
    teams: dict[str, TeamConfig] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "AirlanggaConfig":
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.model_validate(raw)

    def team(self, name: str) -> TeamConfig:
        try:
            return self.teams[name]
        except KeyError as exc:
            raise KeyError(f"no team named '{name}' in config") from exc


def resolve_auth_ref(auth_ref: str) -> str | None:
    """Resolve a credential reference to a secret value at run time.

    Supported forms: ``none`` (no credential), ``env:VAR_NAME`` (read from
    the process environment). Anything else raises — secrets are never
    pasted into config files, prompts, or logs.
    """
    if auth_ref in ("none", "", None):
        return None
    if auth_ref.startswith("env:"):
        name = auth_ref[4:]
        value = os.environ.get(name)
        if not value:
            raise ValueError(f"auth_ref {auth_ref!r}: environment variable is not set")
        return value
    raise ValueError(
        f"unsupported auth_ref {auth_ref!r}: use 'none' or 'env:VAR_NAME'"
    )
