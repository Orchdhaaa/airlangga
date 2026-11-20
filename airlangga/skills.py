"""Skills loader: load a skill from a YAML or Markdown file.

Our own format — no skill code from any other agent project is used.
A skill is a declarative record: name, description, version, the
instructions text the member follows, and the tools it may use. A skill
never executes code on load; loading only parses and validates the
record. Skills are scanned for credential access / exfiltration markers
before they are accepted (the scan is a finding report, not execution).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

_SCAN_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|password|secret|access[_-]?token)\b"),
    re.compile(r"(?i)(curl|wget)\s+.*\|\s*(sh|bash)"),
    re.compile(r"(?i)os\.environ"),
    re.compile(r"(?i)(rm\s+-rf|mkfs|shutdown)"),
)


class Skill(BaseModel):
    name: str
    description: str = ""
    version: str = "1"
    instructions: str = ""
    tools: list[str] = Field(default_factory=list)
    author: str = ""


def scan_skill_text(text: str) -> list[str]:
    """Return finding descriptions for suspicious content, else []."""
    findings: list[str] = []
    for pattern in _SCAN_PATTERNS:
        if pattern.search(text):
            findings.append(f"suspicious pattern: {pattern.pattern}")
    return findings


def load_skill_file(path: str | Path) -> Skill:
    """Load one skill from .yaml/.yml or .md (YAML frontmatter + body)."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        data = yaml.safe_load(raw) or {}
        findings = scan_skill_text(raw)
    elif path.suffix.lower() == ".md":
        data, body = _split_frontmatter(raw)
        data["instructions"] = body.strip() or data.get("instructions", "")
        findings = scan_skill_text(raw)
    else:
        raise ValueError(f"unsupported skill file: {path.suffix} (use .yaml or .md)")
    if findings:
        raise ValueError(f"skill {path} blocked by scan: {'; '.join(findings)}")
    return Skill.model_validate(data)


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            front = yaml.safe_load(raw[3:end]) or {}
            return dict(front), raw[end + 4 :]
    return {}, raw


def load_skills_dir(directory: str | Path) -> list[Skill]:
    """Load every skill file in a directory (sorted, deterministic)."""
    directory = Path(directory)
    skills: list[Skill] = []
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in (".yaml", ".yml", ".md"):
            skills.append(load_skill_file(path))
    return skills
