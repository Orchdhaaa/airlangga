"""Bounded debate: propose → critique → revise → decide.

Applies only to contested decisions. Max 2 rounds, enforced by a runtime
loop counter, not by the prompt. Decision order is fixed: (1) a verifier
result decides if one exists; (2) otherwise the Team Brain rules;
(3) if the Team Brain is low-confidence or stakes are flagged, escalate
to the Main Brain, then to a human. Dissent is always recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

MAX_ROUNDS = 2


@dataclass
class Dissent:
    member_id: str
    reason: str


@dataclass
class DebateResult:
    decision: str  # the settled proposal text, or "escalated"
    rounds_used: int
    decided_by: str  # verifier | team_brain | escalated
    dissents: list[Dissent] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


class Debate:
    def __init__(self, max_rounds: int = MAX_ROUNDS) -> None:
        self.max_rounds = max_rounds

    def run(
        self,
        proposal: str,
        proposer_id: str,
        critic: Callable[[str, int], str],
        verifier: Callable[[str], bool | None] | None = None,
        team_brain_ruling: Callable[[str, list[Dissent]], str] | None = None,
        dissents: list[Dissent] | None = None,
    ) -> DebateResult:
        """Run a bounded debate.

        ``critic`` receives (current_proposal, round_no) and returns either
        a revised proposal or the same text (accept). ``verifier`` returns
        True/False when an executable check decides, None when it cannot.
        """
        dissents = list(dissents or [])
        current = proposal
        history: list[dict] = [{"round": 0, "action": "propose", "by": proposer_id, "text": current}]

        for round_no in range(1, self.max_rounds + 1):
            revised = critic(current, round_no)
            history.append({"round": round_no, "action": "critique", "text": revised})
            if revised == current:
                history.append({"round": round_no, "action": "accept", "text": current})
                break
            # Repeated-argument early close: a critique that only restates
            # the previous round ends the debate instead of looping.
            if round_no > 1 and revised == history[-3]["text"]:
                history.append({"round": round_no, "action": "early_close_repeated_argument"})
                break
            current = revised
            history.append({"round": round_no, "action": "revise", "text": current})

        rounds_used = max(h["round"] for h in history)

        if verifier is not None:
            verdict = verifier(current)
            if verdict is not None:
                return DebateResult(
                    decision=current if verdict else "escalated",
                    rounds_used=rounds_used,
                    decided_by="verifier",
                    dissents=dissents,
                    history=history,
                )
        if team_brain_ruling is not None:
            ruling = team_brain_ruling(current, dissents)
            return DebateResult(
                decision=ruling,
                rounds_used=rounds_used,
                decided_by="team_brain",
                dissents=dissents,
                history=history,
            )
        return DebateResult(
            decision="escalated",
            rounds_used=rounds_used,
            decided_by="escalated",
            dissents=dissents,
            history=history,
        )
