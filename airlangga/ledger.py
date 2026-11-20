"""Run Ledger: append-only, event-sourced SQLite (WAL mode).

Every plan, assignment, message, tool call, cost, verdict, dissent, and
fallback switch is an immutable event with a timestamp, an actor, and a
causal parent. On restart the runtime replays events to reconstruct the
plan tree, contract states, blackboard, budgets consumed, and member
states — no run depends on a process staying alive.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Ledger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                type TEXT NOT NULL,
                actor TEXT NOT NULL,
                parent_id TEXT,
                payload TEXT NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id, seq)")
        self._conn.commit()

    def append(
        self,
        run_id: str,
        type_: str,
        actor: str,
        payload: dict[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO events (run_id, ts, type, actor, parent_id, payload)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, utc_now(), type_, actor, parent_id, json.dumps(payload or {})),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def events(self, run_id: str | None = None) -> list[dict[str, Any]]:
        if run_id is None:
            rows = self._conn.execute(
                "SELECT seq, run_id, ts, type, actor, parent_id, payload FROM events ORDER BY seq"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT seq, run_id, ts, type, actor, parent_id, payload FROM events"
                " WHERE run_id = ? ORDER BY seq",
                (run_id,),
            ).fetchall()
        return [
            {
                "seq": r[0],
                "run_id": r[1],
                "ts": r[2],
                "type": r[3],
                "actor": r[4],
                "parent_id": r[5],
                "payload": json.loads(r[6]),
            }
            for r in rows
        ]

    def run_ids(self) -> list[str]:
        rows = self._conn.execute("SELECT DISTINCT run_id FROM events ORDER BY run_id").fetchall()
        return [r[0] for r in rows]

    def replay(self, run_id: str) -> list[dict[str, Any]]:
        """Replay a run's events in order. Alias for events(run_id)."""
        return self.events(run_id)

    def reconstruct(self, run_id: str) -> dict[str, Any]:
        """Rebuild run state from the event log (crash-resume primitive).

        Returns contract states, committed blackboard entry ids, total cost
        per actor, and member states, as recorded — nothing is inferred
        from in-memory state.
        """
        state: dict[str, Any] = {
            "contracts": {},
            "blackboard_committed": [],
            "cost_by_actor": {},
            "member_states": {},
            "dissents": [],
            "fallback_switches": [],
        }
        for ev in self.events(run_id):
            p = ev["payload"]
            t = ev["type"]
            if t == "contract_created":
                state["contracts"][p.get("contract_id")] = "open"
            elif t == "contract_completed":
                state["contracts"][p.get("contract_id")] = "done"
            elif t == "contract_failed":
                state["contracts"][p.get("contract_id")] = "failed"
            elif t == "blackboard_committed":
                state["blackboard_committed"].append(p.get("entry_id"))
            elif t == "cost":
                actor = ev["actor"]
                cur = state["cost_by_actor"].setdefault(actor, {"tokens": 0, "usd": 0.0, "tool_calls": 0})
                cur["tokens"] += int(p.get("tokens", 0))
                cur["usd"] += float(p.get("usd", 0.0))
                cur["tool_calls"] += int(p.get("tool_calls", 0))
            elif t == "member_state":
                state["member_states"][ev["actor"]] = p.get("state")
            elif t == "dissent":
                state["dissents"].append(p)
            elif t == "fallback_switch":
                state["fallback_switches"].append(p)
        return state

    def close(self) -> None:
        self._conn.close()
