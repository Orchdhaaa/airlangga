"""Blackboard: durable shared working memory for one team and one run.

Typed, versioned entries (fact | decision | open_question | artifact |
risk) with author, evidence, confidence, valid_until, supersedes.
Members propose entries; only the Team Brain (or lead member in v1)
commits them. Every entry carries a write-time abstract (<=150 tokens);
readers get abstracts first and pull bodies by ID only if needed.
Retrieval is full-text search over entries plus tags.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

EntryType = Literal["fact", "decision", "open_question", "artifact", "risk"]

COMMIT_ROLES = ("team_brain", "lead")


def make_abstract(body: str, max_chars: int = 600) -> str:
    """Write-time abstract: about 150 tokens (~600 characters)."""
    text = " ".join(body.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + " …"


def entry_to_report(entry: dict[str, Any]) -> dict[str, Any]:
    """Shape one blackboard entry into a structured member report dict.

    ``TeamRuntime.commit_report`` stores the full ``Report`` model JSON in
    ``entry["body"]``, so claim text, evidence refs, confidence, verdict,
    diff, and open questions come back verbatim. Non-JSON entries fall back
    to ``entry["evidence"]`` or ``entry["body"]`` so text is never hidden.
    """
    body_raw = entry.get("body") or ""
    try:
        data = json.loads(body_raw)
    except (ValueError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    raw_claims = data.get("claims") or []
    claims = [
        {
            "claim": str(c.get("claim", "")),
            "evidence_refs": [str(ref) for ref in (c.get("evidence_refs") or [])],
            "confidence": c.get("confidence", 0.0),
        }
        for c in raw_claims
        if isinstance(c, dict)
    ]
    if not claims and entry.get("evidence"):
        claims = [
            {
                "claim": str(c),
                "evidence_refs": [],
                "confidence": entry.get("confidence", 0.0),
            }
            for c in entry["evidence"]
        ]
    elif not claims and isinstance(body_raw, str) and body_raw.strip() and not data:
        claims = [
            {
                "claim": body_raw.strip(),
                "evidence_refs": [],
                "confidence": entry.get("confidence", 0.0),
            }
        ]
    return {
        "entry_id": entry["id"],
        "contract_id": data.get("contract_id"),
        "member_id": entry["author"],
        "title": entry["title"],
        "status": entry["status"],
        "verdict": data.get("verdict_self"),
        "claims": claims,
        "diff": data.get("diff"),
        "open_questions": [str(q) for q in (data.get("open_questions") or [])],
        "cost": data.get("cost") or {},
        "created_at": entry["created_at"],
    }


class Blackboard:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                abstract TEXT NOT NULL,
                author TEXT NOT NULL,
                evidence TEXT NOT NULL,
                confidence REAL NOT NULL,
                valid_until TEXT,
                supersedes INTEGER,
                artifact_hash TEXT,
                status TEXT NOT NULL DEFAULT 'proposed',
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        # Full-text search when the SQLite build supports FTS5; otherwise
        # search() falls back to LIKE. The table itself is the source of truth.
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(title, body, content='entries', content_rowid='id')"
            )
            self._fts = True
        except sqlite3.OperationalError:
            self._fts = False
        self._conn.commit()

    def propose(
        self,
        run_id: str,
        team_id: str,
        type_: EntryType,
        title: str,
        body: str,
        author: str,
        evidence: list[str] | None = None,
        confidence: float = 0.0,
        valid_until: str | None = None,
        supersedes: int | None = None,
        artifact_hash: str | None = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO entries (run_id, team_id, type, title, body, abstract,"
            " author, evidence, confidence, valid_until, supersedes, artifact_hash,"
            " status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?)",
            (
                run_id,
                team_id,
                type_,
                title,
                body,
                make_abstract(body),
                author,
                json.dumps(evidence or []),
                confidence,
                valid_until,
                supersedes,
                artifact_hash,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        entry_id = int(cur.lastrowid)
        if self._fts:
            self._conn.execute(
                "INSERT INTO entries_fts(rowid, title, body) VALUES (?, ?, ?)",
                (entry_id, title, body),
            )
        self._conn.commit()
        return entry_id

    def commit(self, entry_id: int, by_role: str) -> None:
        """Commit a proposed entry. Only the Team Brain or lead may commit."""
        if by_role not in COMMIT_ROLES:
            raise PermissionError(
                f"role {by_role!r} may propose but not commit blackboard entries"
            )
        cur = self._conn.execute(
            "UPDATE entries SET status='committed' WHERE id=? AND status='proposed'",
            (entry_id,),
        )
        if cur.rowcount == 0:
            raise ValueError(f"entry {entry_id} is not in 'proposed' state")
        self._conn.commit()

    def archive(self, entry_id: int) -> None:
        self._conn.execute("UPDATE entries SET status='archived' WHERE id=?", (entry_id,))
        self._conn.commit()

    def get(self, entry_id: int) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT * FROM entries WHERE id=?", (entry_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no blackboard entry {entry_id}")
        return self._row_to_dict(row)

    def count_by_run(self) -> dict[str, int]:
        """Number of entries per run id (used for run-list claim counts)."""
        rows = self._conn.execute(
            "SELECT run_id, COUNT(*) FROM entries GROUP BY run_id"
        ).fetchall()
        return {run_id: n for run_id, n in rows}

    def list_for_run(
        self, run_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        """All entries for one run, across teams, in commit order.

        Used by run detail views and CLI trace: after a server restart the
        in-memory run registry is gone, so the team is not known — but the
        run id alone identifies its committed reports.
        """
        query = "SELECT * FROM entries WHERE run_id=?"
        params: list[Any] = [run_id]
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY id"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def list_entries(
        self, run_id: str, team_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM entries WHERE run_id=? AND team_id=?"
        params: list[Any] = [run_id, team_id]
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY id"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def search(self, run_id: str, team_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if self._fts:
            rows = self._conn.execute(
                "SELECT e.* FROM entries e JOIN entries_fts f ON e.id = f.rowid"
                " WHERE e.run_id=? AND e.team_id=? AND entries_fts MATCH ? ORDER BY rank LIMIT ?",
                (run_id, team_id, query, limit),
            ).fetchall()
            if rows:
                return [self._row_to_dict(r) for r in rows]
        like = f"%{query}%"
        rows = self._conn.execute(
            "SELECT * FROM entries WHERE run_id=? AND team_id=?"
            " AND (title LIKE ? OR body LIKE ?) ORDER BY id LIMIT ?",
            (run_id, team_id, like, like, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def is_stale(self, entry: dict[str, Any], current_artifact_hash: str | None = None) -> bool:
        """An entry is stale when it expired or its source artifact changed.

        Staleness is shown to the reader as a marker, never silently trusted.
        """
        valid_until = entry.get("valid_until")
        if valid_until:
            try:
                if datetime.fromisoformat(valid_until) < datetime.now(timezone.utc):
                    return True
            except ValueError:
                pass
        if current_artifact_hash and entry.get("artifact_hash"):
            return current_artifact_hash != entry["artifact_hash"]
        return False

    @staticmethod
    def _row_to_dict(row: tuple) -> dict[str, Any]:
        keys = [
            "id", "run_id", "team_id", "type", "title", "body", "abstract",
            "author", "evidence", "confidence", "valid_until", "supersedes",
            "artifact_hash", "status", "version", "created_at",
        ]
        out = dict(zip(keys, row))
        out["evidence"] = json.loads(out["evidence"])
        return out

    def close(self) -> None:
        self._conn.close()
