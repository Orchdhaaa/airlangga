"""Brains: Main Brain and Team Brain as two configurations of one
turn loop, with layered prompts.

Main Brain (strategic): goal, delegation policy, synthesis rules. It
has no domain tools — only plan, assign, reallocate_budget, accept,
reject, ask_human, finalize — and reads briefs and verdicts only.
Team Brain (tactical): team goal, roster, shared context. In v1 a
lead member fills this role instead of a separate LLM tier.
"""

from __future__ import annotations

from pathlib import Path

from .config import MainBrainConfig, MemberConfig
from .guardrails import is_write_denied
from .providers.base import ChatMessage
from .turn import TurnLoop

MAIN_BRAIN_TOOLS = ["plan", "assign", "reallocate_budget", "accept", "reject", "ask_human", "finalize"]
TEAM_BRAIN_TOOLS = ["assign_member", "request_critique", "commit_to_blackboard", "merge", "rule", "escalate"]


def main_brain_prompt(goal: str) -> str:
    return (
        "You are the Main Brain of Airlangga, a persistent Agentic Team runtime.\n"
        "Your job is strategic only: decompose the goal into signed task contracts,\n"
        "assign them to teams, judge structured reports, and finalise.\n"
        "You do not do member work. You never see member transcripts.\n"
        "You may only use these tools: " + ", ".join(MAIN_BRAIN_TOOLS) + ".\n"
        f"Goal: {goal}\n"
        "Return a plan as JSON: list of contracts with goal, team, budget, deadline."
    )


def team_brain_prompt(team_name: str, team_goal: str, roster: list[str]) -> str:
    return (
        f"You are the Team Brain for team {team_name}.\n"
        f"Team goal: {team_goal}\n"
        f"Roster: {', '.join(roster)}.\n"
        "Your job is tactical: assign member contracts, request critiques,\n"
        "commit blackboard entries, merge results, rule on conflicts, escalate.\n"
        "You may only use these tools: " + ", ".join(TEAM_BRAIN_TOOLS) + ".\n"
        "Members propose blackboard entries; only you commit them."
    )


CHARTER_MAX_BYTES = 16_384


def load_charter_text(member: MemberConfig, files_root: str | Path | None) -> str | None:
    """Read a member's charter file (persona text) safely inside
    files_root. Returns None when there is no charter, the path
    escapes the root, hits a credential path, or cannot be read as
    UTF-8 text. Oversized charters are truncated cleanly at 16 KB."""
    if not member.charter_file or not files_root:
        return None
    rel = member.charter_file.replace("\\", "/")
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if not parts or ".." in parts or rel.startswith("/") or "\x00" in rel:
        return None
    if is_write_denied("/".join(parts)):
        return None
    root = Path(files_root).resolve()
    target = (root / "/".join(parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    data = text.encode("utf-8")
    if len(data) > CHARTER_MAX_BYTES:
        text = data[:CHARTER_MAX_BYTES].decode("utf-8", errors="ignore")
        text += "\n[Charter truncated at 16 KB]"
    return text


def member_prompt(member: MemberConfig, contract_goal: str,
                  files_root: str | Path | None = None) -> str:
    base = (
        f"You are {member.id}, role {member.role}, in an Agentic Team.\n"
        f"Your contract: {contract_goal}\n"
        "Return only a structured report as JSON: claims (with evidence_refs "
        "and confidence), open_questions, verdict_self (pass/fail/partial).\n"
        "Do not message other members directly; use the blackboard via the "
        "Team Brain. Do not invent evidence."
    )
    charter = load_charter_text(member, files_root)
    if charter is not None:
        base = (
            f"--- PERSONA CHARTER ({member.charter_file}) ---\n"
            f"{charter}\n--- END CHARTER ---\n\n"
        ) + base
    if member.attached_files:
        base += "\nFiles available to read: " + ", ".join(member.attached_files) + ".\n"
    return base


class Brain:
    """A Brain is a TurnLoop plus a layered system prompt."""

    def __init__(self, loop: TurnLoop, system_prompt: str) -> None:
        self.loop = loop
        self.system_prompt = system_prompt

    def ask(self, user_text: str) -> str:
        result = self.loop.run(
            [ChatMessage(role="system", content=self.system_prompt),
             ChatMessage(role="user", content=user_text)]
        )
        return result.content
