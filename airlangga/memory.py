"""Long-term memory (cross-run) + per-member private notes.

The blackboard is run-and-team-scoped working memory. Promotion from
the blackboard to long-term memory is an explicit, Main-Brain-approved
step, with provenance kept. Per-member private notes are never promoted
without that approval and never visible to other members.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class LongTermMemory:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                provenance TEXT NOT NULL,
                approved_by TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def promote(
        self, run_id: str, team_id: str, author: str, text: str,
        provenance: str, approved_by: str,
    ) -> int:
        """Promote a blackboard entry to long-term memory. Only the Main
        Brain may approve a promotion; the approver is recorded."""
        if approved_by != "main_brain":
            raise PermissionError("only the Main Brain may approve a memory promotion")
        cur = self._conn.execute(
            "INSERT INTO memories (run_id, team_id, author, text, provenance, approved_by)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, team_id, author, text, provenance, approved_by),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, run_id, team_id, author, text, provenance FROM memories"
            " WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [
            dict(zip(["id", "run_id", "team_id", "author", "text", "provenance"], r))
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
