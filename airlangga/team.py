"""Team Runtime: roster, lifecycle, Main Brain + Team Runtime.

A team is a persistent organisation: a durable roster of named members,
each with a pinned model endpoint, tool allowlist, and budget. Members
are activated per task with a fresh, budgeted context built from their
record — persistent state, not persistent processes. Lifecycle states:
IDLE / WORKING / BLOCKED / REVIEWING / DONE, plus steering, handoff,
and replacement of a failed member.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .blackboard import Blackboard
from .brain import main_brain_prompt, member_prompt, team_brain_prompt
from .budget import BudgetGovernor
from .config import AirlanggaConfig, MemberConfig, TeamConfig
from .context import ContextBuilder
from .contracts import Contract, Report, check_acceptance
from .ledger import Ledger
from .policy import MemberPolicy, PolicyEngine
from .providers import build_client
from .providers.base import ChatMessage
from .router import NoCapableModel, Router
from .tools import build_member_tools
from .turn import TurnLoop


class MemberState(str, Enum):
    IDLE = "IDLE"
    WORKING = "WORKING"
    BLOCKED = "BLOCKED"
    REVIEWING = "REVIEWING"
    DONE = "DONE"


@dataclass
class MemberRecord:
    config: MemberConfig
    state: MemberState = MemberState.IDLE
    notes: list[str] = field(default_factory=list)
    track_record: dict[str, int] = field(
        default_factory=lambda: {"completed": 0, "failed": 0, "dissents": 0}
    )


class TeamRuntime:
    def __init__(
        self,
        config: AirlanggaConfig,
        team_name: str,
        run_id: str,
        ledger: Ledger,
        blackboard: Blackboard,
        budget: BudgetGovernor,
        workdir: str,
        files_root: str | Path | None = None,
    ) -> None:
        self.config = config
        self.team_name = team_name
        self.team_config: TeamConfig = config.team(team_name)
        self.run_id = run_id
        self.ledger = ledger
        self.blackboard = blackboard
        self.budget = budget
        self.workdir = workdir
        self.files_root = files_root
        self.members: dict[str, MemberRecord] = {
            m.id: MemberRecord(config=m) for m in self.team_config.members
        }
        self.policy_engine = PolicyEngine()
        self.router = Router(on_switch=self._log_switch)
        self.budget.set_cap(f"team:{team_name}", self.team_config.team_budget)
        for member_id, record in self.members.items():
            self.budget.set_cap(f"member:{member_id}", record.config.budget)

    # -- internal helpers -------------------------------------------------
    def _log_switch(self, endpoint: Any, reason: str) -> None:
        self.ledger.append(
            self.run_id,
            "fallback_switch",
            "router",
            {"endpoint": f"{endpoint.provider}/{endpoint.model}", "reason": reason},
        )

    def _set_state(self, member_id: str, state: MemberState,
                   extra: dict | None = None) -> None:
        self.members[member_id].state = state
        payload: dict[str, Any] = {"state": state.value}
        if extra:
            payload.update(extra)
        self.ledger.append(
            self.run_id, "member_state", member_id, payload
        )

    def lead_member(self) -> MemberRecord | None:
        lead_id = self.team_config.lead_member
        return self.members.get(lead_id) if lead_id else None

    # -- planning (Main Brain) --------------------------------------------
    def plan(self, goal: str) -> list[Contract]:
        """Main Brain decomposition: one contract per roster member, each
        scoped to that member's role. The plan tree is a ledger event."""
        contracts: list[Contract] = []
        for member in self.team_config.members:
            contract = Contract(
                goal=f"{goal} — {member.role} work ({member.id})",
                team_id=self.team_name,
                member_id=member.id,
                issuer="main_brain",
                budget=member.budget,
            )
            contracts.append(contract)
            self.ledger.append(
                self.run_id,
                "contract_created",
                "main_brain",
                {"contract_id": contract.id, "member_id": member.id, "goal": contract.goal},
            )
        self.ledger.append(
            self.run_id,
            "plan_created",
            "main_brain",
            {"goal": goal, "team": self.team_name, "contracts": [c.id for c in contracts]},
        )
        return contracts

    # -- activation ---------------------------------------------------------
    def activate(self, member_id: str, contract: Contract) -> Report:
        """Activate one member for one contract and return its report."""
        record = self.members[member_id]
        charter_extra = (
            {"charter_file": record.config.charter_file}
            if record.config.charter_file else None
        )
        self._set_state(member_id, MemberState.WORKING, charter_extra)
        try:
            endpoint = self.router.route(record.config)
        except NoCapableModel as exc:
            self._set_state(member_id, MemberState.BLOCKED)
            self.ledger.append(
                self.run_id, "contract_failed", member_id,
                {"contract_id": contract.id, "reason": str(exc)},
            )
            raise
        # Pre-flight budget estimate before any model call.
        self.budget.preflight(
            f"member:{member_id}", 2000, endpoint.cost_per_mtok_usd
        )
        client = build_client(endpoint, role=record.config.role)
        try:
            system_prompt = member_prompt(record.config, contract.goal,
                                          files_root=self.files_root)
            context = ContextBuilder(budget_tokens=record.config.context_limit // 4).build(
                system_prompt=system_prompt,
                contract_text=contract.goal,
                blackboard_slices=[
                    e["abstract"]
                    for e in self.blackboard.list_entries(self.run_id, self.team_name, status="committed")
                ],
            )
            # Member tools are built from the member's toolsets and gated
            # by the Policy Engine allowlist (real tool names, not labels).
            member_tools, tool_schemas = build_member_tools(
                list(record.config.toolsets), self.workdir
            )
            policy = MemberPolicy(
                allowed_tools=list(member_tools.keys()),
                approval_required=["external_post", "spend_above_usd_5"],
                write_root=self.workdir,
            )
            denied: list[str] = []
            loop = TurnLoop(
                client=client,
                tools=member_tools,
                tool_schemas=tool_schemas,
                max_turns=5,
                context_limit=record.config.context_limit,
                policy=policy,
                actor=member_id,
                budget=self.budget,
                budget_scope=f"member:{member_id}",
                on_denied=denied.append,
            )
            result = loop.run(context)
            for note in denied:
                self.ledger.append(self.run_id, "policy_denied", member_id, {"note": note})
            tokens = result.usage["input_tokens"] + result.usage["output_tokens"]
            usd = tokens / 1_000_000 * endpoint.cost_per_mtok_usd
            self.ledger.append(
                self.run_id, "cost", member_id,
                {"tokens": tokens, "usd": round(usd, 6), "tool_calls": result.tool_calls},
            )
            report = self._parse_report(result.content, contract, member_id, tokens, usd, result.tool_calls)
        finally:
            client.close()
        self._set_state(member_id, MemberState.REVIEWING)
        passed, reason = check_acceptance(contract, report)
        if passed:
            record.track_record["completed"] += 1
            self._set_state(member_id, MemberState.DONE)
            self.ledger.append(
                self.run_id, "contract_completed", member_id,
                {"contract_id": contract.id, "reason": reason},
            )
        else:
            record.track_record["failed"] += 1
            self._set_state(member_id, MemberState.BLOCKED)
            self.ledger.append(
                self.run_id, "contract_failed", member_id,
                {"contract_id": contract.id, "reason": reason},
            )
        return report

    @staticmethod
    def _parse_report(
        content: str, contract: Contract, member_id: str, tokens: int, usd: float, tool_calls: int
    ) -> Report:
        try:
            data = json.loads(content)
            claims = data.get("claims", [])
            return Report(
                contract_id=contract.id,
                member_id=member_id,
                claims=claims,
                open_questions=data.get("open_questions", []),
                cost={"tokens": float(tokens), "usd": usd, "tool_calls": float(tool_calls)},
                verdict_self=data.get("verdict_self", "pass"),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return Report(
                contract_id=contract.id,
                member_id=member_id,
                claims=[{"claim": content[:500], "evidence_refs": [], "confidence": 0.5}],
                cost={"tokens": float(tokens), "usd": usd, "tool_calls": float(tool_calls)},
                verdict_self="partial",
            )

    # -- team-level operations ----------------------------------------------
    def commit_report(self, report: Report, by_role: str = "lead") -> int:
        """Lead/Team Brain commits a member report to the blackboard."""
        entry_id = self.blackboard.propose(
            run_id=self.run_id,
            team_id=self.team_name,
            type_="fact",
            title=f"Report from {report.member_id} ({report.contract_id})",
            body=json.dumps(report.model_dump(), indent=2),
            author=report.member_id,
            evidence=[c.claim for c in report.claims],
            confidence=0.8,
        )
        self.blackboard.commit(entry_id, by_role=by_role)
        self.ledger.append(
            self.run_id, "blackboard_committed", by_role,
            {"entry_id": entry_id, "member_id": report.member_id},
        )
        return entry_id

    def run_team(self, goal: str) -> list[Report]:
        """Full v1 team run: plan → activate each member → commit reports."""
        contracts = self.plan(goal)
        reports: list[Report] = []
        for contract in contracts:
            if contract.member_id is None:
                continue
            report = self.activate(contract.member_id, contract)
            reports.append(report)
            self.commit_report(report)
        return reports


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:8]}"
