"""Trace viewer (CLI) + replay command + single-agent baseline.

The trace renders the plan tree, who did what, cost per node, and debate
outcomes from the ledger — nothing is trusted that is not in the ledger.
Replay re-runs a recorded task against a different model config and
compares cost and pass rate, including a single-agent baseline: if the
team does not beat the baseline on cost-adjusted quality for a task type,
do not use a team for that type.
"""

from __future__ import annotations

from .ledger import Ledger


def render_trace(ledger: Ledger, run_id: str) -> str:
    events = ledger.events(run_id)
    state = ledger.reconstruct(run_id)
    lines: list[str] = [f"Run {run_id} — {len(events)} events", ""]
    for ev in events:
        payload = ev["payload"]
        detail = ""
        if ev["type"] == "cost":
            detail = f"tokens={payload.get('tokens')} usd=${payload.get('usd'):.4f} tools={payload.get('tool_calls')}"
        elif ev["type"] in ("contract_created", "contract_completed", "contract_failed"):
            detail = f"{payload.get('contract_id')} {payload.get('goal', payload.get('reason', ''))}"
        elif ev["type"] == "plan_created":
            detail = f"goal={payload.get('goal')!r} contracts={len(payload.get('contracts', []))}"
        elif ev["type"] == "fallback_switch":
            detail = f"{payload.get('endpoint')}: {payload.get('reason')}"
        elif ev["type"] == "blackboard_committed":
            detail = f"entry={payload.get('entry_id')} member={payload.get('member_id')}"
        elif ev["type"] == "member_state":
            detail = payload.get("state", "")
        elif ev["type"] == "dissent":
            detail = f"{payload.get('member_id')}: {payload.get('reason')}"
        elif ev["type"] == "policy_denied":
            detail = str(payload.get("note", ""))
        lines.append(f"  #{ev['seq']:>3} [{ev['ts']}] {ev['actor']:<16} {ev['type']:<20} {detail}")
    lines.append("")
    lines.append("Cost by actor:")
    for actor, cost in sorted(state["cost_by_actor"].items()):
        lines.append(
            f"  {actor:<16} tokens={cost['tokens']} usd=${cost['usd']:.4f} tools={cost['tool_calls']}"
        )
    lines.append(f"Contracts: {state['contracts']}")
    lines.append(f"Member states: {state['member_states']}")
    if state["dissents"]:
        lines.append(f"Dissents: {len(state['dissents'])} recorded")
    return "\n".join(lines)


def baseline_comparison(team_cost_usd: float, team_passed: bool, baseline_cost_usd: float, baseline_passed: bool) -> str:
    """Compare a team run against the single-agent baseline.

    The team wins only when it passes and is cheaper per passing run than
    the baseline, or when the baseline fails and the team passes.
    """
    if team_passed and not baseline_passed:
        return "team wins: baseline failed, team passed"
    if not team_passed:
        return "team loses: team did not pass"
    if team_cost_usd <= baseline_cost_usd:
        return "team wins: passed at equal or lower cost than the single-agent baseline"
    return "team loses on cost: passed, but more expensive than the single-agent baseline"
