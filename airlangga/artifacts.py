"""Artifact Store: per-run workspace, passed by reference.

Files, patches, and reports live here and are referenced as
``artifact://<id>``, never pasted wholesale into prompts. Each artifact
has an ID, a content hash, an author, and a version, so a changed
artifact is detectable by the blackboard's staleness check.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Artifact:
    id: str
    name: str
    sha256: str
    version: int
    author: str
    size_bytes: int

    @property
    def ref(self) -> str:
        return f"artifact://{self.id}"


class ArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "_index.json"
        self._index: dict[str, dict] = {}
        if self._index_path.exists():
            self._index = json.loads(self._index_path.read_text(encoding="utf-8"))

    def _save_index(self) -> None:
        self._index_path.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def store(self, name: str, content: bytes | str, author: str) -> Artifact:
        data = content.encode("utf-8") if isinstance(content, str) else content
        digest = hashlib.sha256(data).hexdigest()
        prior = [a for a in self._index.values() if a["name"] == name]
        version = max((a["version"] for a in prior), default=0) + 1
        artifact_id = uuid.uuid4().hex[:12]
        path = self.root / f"{artifact_id}-{name}"
        path.write_bytes(data)
        record = {
            "id": artifact_id,
            "name": name,
            "sha256": digest,
            "version": version,
            "author": author,
            "size_bytes": len(data),
            "path": str(path),
        }
        self._index[artifact_id] = record
        self._save_index()
        return Artifact(
            id=artifact_id,
            name=name,
            sha256=digest,
            version=version,
            author=author,
            size_bytes=len(data),
        )

    def get(self, artifact_id: str) -> bytes:
        record = self._index[artifact_id]
        return Path(record["path"]).read_bytes()

    def verify(self, artifact_id: str) -> bool:
        """True when the stored bytes still match the recorded hash."""
        record = self._index[artifact_id]
        data = Path(record["path"]).read_bytes()
        return hashlib.sha256(data).hexdigest() == record["sha256"]

    def list(self) -> list[Artifact]:
        return [
            Artifact(
                id=r["id"],
                name=r["name"],
                sha256=r["sha256"],
                version=r["version"],
                author=r["author"],
                size_bytes=r["size_bytes"],
            )
            for r in self._index.values()
        ]
