"""Task Contracts: the only way work crosses layers.

A contract carries a goal, inputs as artifact references, an output
schema, an acceptance check, a budget, a deadline, and an idempotency
key. It is signed by its issuer and validated by the runtime before a
member may start. A report that fails its output schema is a typed
quality-gate failure, not a conversation to repair in chat.
"""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from .config import Budget


def new_idempotency_key(contract_id: str, goal: str) -> str:
    digest = hashlib.sha256(f"{contract_id}:{goal}".encode()).hexdigest()[:16]
    return f"{contract_id}-{digest}"


class AcceptanceCheck(BaseModel):
    kind: Literal["schema", "shell", "judge"] = "schema"
    # schema: required top-level fields that must be present in the report.
    required_fields: list[str] = Field(default_factory=list)
    # shell: command (argv list) whose exit code 0 means pass.
    command: list[str] = Field(default_factory=list)
    timeout_s: int = 30


class Contract(BaseModel):
    id: str = Field(default_factory=lambda: f"contract-{uuid.uuid4().hex[:8]}")
    goal: str
    team_id: str
    member_id: str | None = None
    inputs: list[str] = Field(default_factory=list)  # artifact:// refs
    output_schema: dict[str, Any] = Field(default_factory=dict)
    acceptance: AcceptanceCheck = Field(default_factory=AcceptanceCheck)
    budget: Budget = Field(default_factory=Budget)
    deadline_utc: str | None = None
    idempotency_key: str = ""
    issuer: str = "main_brain"
    status: Literal["open", "working", "done", "failed", "blocked"] = "open"

    def model_post_init(self, __context: Any) -> None:
        if not self.idempotency_key:
            self.idempotency_key = new_idempotency_key(self.id, self.goal)


class Claim(BaseModel):
    claim: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Report(BaseModel):
    contract_id: str
    member_id: str
    claims: list[Claim] = Field(default_factory=list)
    diff: str | None = None  # artifact:// ref to what changed
    open_questions: list[str] = Field(default_factory=list)
    cost: dict[str, float] = Field(default_factory=dict)
    verdict_self: Literal["pass", "fail", "partial"] = "pass"


def validate_report(report: Report, contract: Contract) -> list[str]:
    """Return a list of validation errors; empty means the report is valid."""
    errors: list[str] = []
    if report.contract_id != contract.id:
        errors.append(
            f"report contract_id {report.contract_id!r} does not match contract {contract.id!r}"
        )
    for field_name in contract.acceptance.required_fields:
        if field_name not in report.model_dump():
            errors.append(f"missing required report field: {field_name}")
    return errors


def check_acceptance(contract: Contract, report: Report) -> tuple[bool, str]:
    """Run the contract's acceptance check. Returns (passed, reason)."""
    errors = validate_report(report, contract)
    if errors:
        return False, "; ".join(errors)
    if contract.acceptance.kind == "shell":
        if not contract.acceptance.command:
            return False, "shell acceptance check has no command"
        try:
            proc = subprocess.run(
                contract.acceptance.command,
                capture_output=True,
                timeout=contract.acceptance.timeout_s,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return False, f"acceptance command failed to run: {exc}"
        if proc.returncode != 0:
            return False, f"acceptance command exited {proc.returncode}"
    # "schema" and "judge" kinds: schema validation above is the check;
    # a judge verdict is supplied by the caller as verdict_self.
    if contract.acceptance.kind == "judge" and report.verdict_self == "fail":
        return False, "judge verdict: fail"
    return True, "accepted"
