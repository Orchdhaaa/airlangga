"""Airlangga Web UI — node-graph team editor + config + runs.

Original code, built from scratch for Airlangga. The UI is an n8n-style
node graph in *idea* only (draggable nodes, drawn connections): the
connections here are between **brains**, models, files and tools — e.g.
Model A powers which brains, which files/folders attach to a member,
which members belong to which team. No n8n or Hermes UI code is used.

Backend: stdlib ``http.server`` (same pattern as ``api_server.py``), no
new dependencies. The UI is one self-contained HTML file (``ui.html``)
with inline CSS/JS — no build step, no copied front-end code.

Auth: a UI token from the ``AIRLANGGA_UI_TOKEN`` environment variable.
When a token is set, every *API* call requires it (header
``X-Airlangga-Token`` or ``?token=``) and still answers 401 JSON
without one. The HTML page itself (``/``, ``/ui``, ``/ui.html``) is
always served (HTTP 200) and carries a login form: a browser that
opens the bare URL gets the login page, never a 401 JSON — the page
validates the entered token against ``/api/state``, stores it in
``sessionStorage`` (this tab only, never in the URL), and then loads
the app. ``?token=...`` still works as a convenience: the page stores
it and cleans the URL. When no token is set the server binds
localhost only and warns; binding a public address without a token
is refused (fail closed). There is no default password anywhere.

The token lives in a token file (``AIRLANGGA_UI_TOKEN_FILE``, or
``<project-root>/.ui-token`` by default — the systemd unit loads it as
an EnvironmentFile, so a restart keeps the current token). A logged-in
user can change the token from the UI (Settings → Change UI password,
``POST /api/settings/ui-token``): the new token is written to that file
(mode 0600) and the running server picks it up without a restart — the
auth check re-reads the file whenever it changes, so the old token
stops working immediately.

Persistence:
- ``airlangga.yaml`` — teams, members, Main Brain (source of truth).
- ``airlangga-graph.json`` — node positions + edges of the graph.
- ``files/`` — user files/folders, editable in the UI and attachable to
  members as charter/attached files. Writes are scoped to this root;
  credential paths are denied (Policy Engine denylist) and ``..``
  escapes are blocked.
- ``.airlangga-ui.json`` — UI settings (Telegram allowlist, approval
  default, cron jobs). ``.airlangga-secrets.json`` (0600) holds a
  Telegram bot token entered in the UI; it is never returned by the API.
- ``runs/ledger.db`` — run ledger; runs are read from it, new runs are
  executed by the Team Runtime in a background thread.
- ``runs/blackboard.db`` — committed member reports; run detail reads
  team output from here, so a run's answers survive a restart.
"""

from __future__ import annotations

import io
import json
import os
import re
import secrets
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

from .blackboard import Blackboard, entry_to_report
from .budget import BudgetGovernor
from .config import (
    AirlanggaConfig,
    Budget,
    MainBrainConfig,
    MemberConfig,
    TeamConfig,
)
from .guardrails import is_write_denied
from .ledger import Ledger
from .team import TeamRuntime, new_run_id
from .trace import render_trace

PACKAGE_DIR = Path(__file__).resolve().parent

UI_DEFAULT_PORT = 8100

# ZIP import safety limits (see UIStore.import_zip).
ZIP_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ZIP_MAX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
ZIP_MAX_FILES = 200
ZIP_MAX_RATIO = 100

NODE_TYPES = ("main_brain", "team", "member", "model", "file", "folder", "tool", "skill")
EDGE_KINDS = (
    "assigns", "has_member", "uses_model", "powers", "has_charter",
    "has_file", "uses_tool", "uses_skill", "depends_on",
)

# Provider presets offered in the UI. A preset is just a named endpoint
# record (official API, custom base_url, or local); the wire format is
# what the code actually uses. No credentials are stored here.
PROVIDER_PRESETS: list[dict[str, Any]] = [
    {"provider": "anthropic", "label": "Anthropic (official API)", "wire_format": "anthropic_messages",
     "endpoint": "https://api.anthropic.com", "auth_ref": "env:ANTHROPIC_API_KEY",
     "models": ["claude-opus-4-6", "claude-sonnet-4-5"], "capabilities": ["tool_calling", "structured_json", "long_context"]},
    {"provider": "openai", "label": "OpenAI (official API)", "wire_format": "openai_chat",
     "endpoint": "https://api.openai.com/v1", "auth_ref": "env:OPENAI_API_KEY",
     "models": ["gpt-5", "gpt-5-mini"], "capabilities": ["tool_calling", "structured_json", "vision"]},
    {"provider": "deepseek", "label": "DeepSeek (custom base_url)", "wire_format": "openai_chat",
     "endpoint": "https://api.deepseek.com/v1", "auth_ref": "env:DEEPSEEK_API_KEY",
     "models": ["deepseek-chat", "deepseek-reasoner"], "capabilities": ["tool_calling", "structured_json"]},
    {"provider": "openrouter", "label": "OpenRouter (custom base_url)", "wire_format": "openai_chat",
     "endpoint": "https://openrouter.ai/api/v1", "auth_ref": "env:OPENROUTER_API_KEY",
     "models": ["anthropic/claude-sonnet-4-5", "openai/gpt-5-mini"], "capabilities": ["tool_calling", "structured_json"]},
    {"provider": "gemini", "label": "Google Gemini (official API)", "wire_format": "gemini",
     "endpoint": "https://generativelanguage.googleapis.com/v1beta", "auth_ref": "env:GEMINI_API_KEY",
     "models": ["gemini-2.5-pro", "gemini-2.5-flash"], "capabilities": ["tool_calling", "structured_json", "vision"]},
    {"provider": "ollama", "label": "Ollama (local)", "wire_format": "openai_chat",
     "endpoint": "http://localhost:11434/v1", "auth_ref": "none",
     "models": ["llama3.1:8b", "qwen3:8b"], "capabilities": ["tool_calling", "structured_json"]},
    {"provider": "custom", "label": "Custom endpoint (OpenAI-compatible)", "wire_format": "openai_chat",
     "endpoint": "", "auth_ref": "env:CUSTOM_API_KEY",
     "models": [], "capabilities": ["tool_calling", "structured_json"]},
    {"provider": "mock", "label": "Mock (offline demo, no key)", "wire_format": "mock",
     "endpoint": None, "auth_ref": "none",
     "models": ["mock"], "capabilities": ["tool_calling", "structured_json"]},
]

TOOLSETS = ["web", "file_read", "file_write", "terminal", "skills_research", "browser"]


def _all_providers(store: "UIStore") -> list[dict[str, Any]]:
    """Built-in presets plus user-saved custom base_url providers
    (settings.custom_providers), so a custom endpoint immediately
    appears in every provider dropdown (Graph, Teams, Models)."""
    providers = [dict(p) for p in PROVIDER_PRESETS]
    try:
        custom = store.load_settings().get("custom_providers") or []
    except Exception:
        custom = []
    seen = {p["provider"] for p in providers}
    for c in custom:
        if not isinstance(c, dict) or not c.get("provider") or c["provider"] in seen:
            continue
        providers.append({
            "provider": c["provider"],
            "label": c.get("label") or c["provider"],
            "wire_format": c.get("wire_format") or "openai_chat",
            "endpoint": c.get("endpoint") or "",
            "auth_ref": c.get("auth_ref") or "none",
            "models": list(c.get("models") or []),
            "capabilities": list(c.get("capabilities") or ["tool_calling", "structured_json"]),
        })
        seen.add(c["provider"])
    return providers


# Starter rosters seeded by POST /api/teams when seed_members is true:
# a new team is runnable in under a minute.
TEAM_SEEDS: dict[str, list[dict[str, Any]]] = {
    "research": [
        {"id": "researcher", "role": "researcher", "toolsets": ["web", "file_read"]},
        {"id": "fact_checker", "role": "fact checker", "toolsets": ["web", "file_read"]},
        {"id": "writer", "role": "writer", "toolsets": ["file_read", "file_write"]},
    ],
    "code-review": [
        {"id": "coder", "role": "coder", "toolsets": ["file_read", "file_write", "terminal"]},
        {"id": "reviewer", "role": "reviewer", "toolsets": ["file_read", "terminal"]},
        {"id": "tester", "role": "tester", "toolsets": ["file_read", "terminal"]},
    ],
    "content": [
        {"id": "drafter", "role": "drafter", "toolsets": ["web", "file_read", "file_write"]},
        {"id": "editor", "role": "editor", "toolsets": ["file_read", "file_write"]},
        {"id": "fact_checker", "role": "fact checker", "toolsets": ["web", "file_read"]},
    ],
}

SAMPLE_CHARTER = """# SUPERAGENT — persona charter

You are SUPERAGENT, a senior security researcher and builder.
Work style: code first, working proof over theory, verify every claim
against a primary source before reporting it. Never fake data, never
invent coverage. If a check cannot be verified, say so plainly.

Rules:
- Every finding needs evidence: file, line, command output, or a live read.
- Destructive actions need explicit human approval first.
- Keep reports short, structured, and priced in USD where money is involved.
"""


# ---------------------------------------------------------------------------
# Store: config + graph + files + settings, all on disk under project_root
# ---------------------------------------------------------------------------

def resolve_token_file(project_root: str | Path) -> Path:
    """Path of the UI-token file. ``AIRLANGGA_UI_TOKEN_FILE`` wins when
    set (e.g. the systemd unit's EnvironmentFile); otherwise the file
    next to the project root, ``<project-root>/.ui-token``."""
    env_path = os.environ.get("AIRLANGGA_UI_TOKEN_FILE")
    if env_path:
        return Path(env_path)
    return Path(project_root).resolve() / ".ui-token"


def parse_token_file(path: Path) -> str | None:
    """Read the ``AIRLANGGA_UI_TOKEN=<value>`` line from a token file.
    Returns None when the file is missing or holds no such line."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("AIRLANGGA_UI_TOKEN="):
            return line.split("=", 1)[1].strip()
    return None


def validate_new_ui_token(value: Any) -> str:
    """Validate a candidate UI token. Raises UIError (HTTP 400) when it
    is too short or contains characters that cannot live on one line of
    the token file."""
    if not isinstance(value, str) or len(value) < 8:
        raise UIError("new token must be at least 8 characters long")
    if any(ch.isspace() for ch in value) or "=" in value:
        raise UIError("new token must not contain whitespace or '='")
    return value


class UIError(ValueError):
    """A user-facing error: surfaced as HTTP 400, never a stack trace.

    ``payload`` carries extra machine-readable fields (e.g. an error
    ``code`` or ``binary: True``) merged into the JSON error body.
    """

    def __init__(self, message: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


def _node(node_id: str, type_: str, label: str, x: int, y: int, data: dict | None = None) -> dict:
    return {"id": node_id, "type": type_, "label": label, "x": x, "y": y, "data": data or {}}


def _edge(edge_id: str, source: str, target: str, kind: str) -> dict:
    return {"id": edge_id, "from": source, "to": target, "kind": kind}


def _slug(text: str) -> str:
    """Slugify a label into a config-safe name (team/member id)."""
    return re.sub(r"[^a-z0-9_-]+", "-", str(text or "").lower()).strip("-")


def _model_slug(provider: str, model: str, endpoint: str | None, auth_ref: str) -> str:
    """URL-safe slug for a shared model node from its endpoint tuple."""
    raw = f"{provider}-{model}-{endpoint or ''}-{auth_ref or ''}"
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug or "model"


def _blackboard_entry_to_report(entry: dict[str, Any]) -> dict[str, Any]:
    """Alias for ``blackboard.entry_to_report`` kept for readability."""
    return entry_to_report(entry)


class UIStore:
    def __init__(self, project_root: str | Path, config_name: str = "airlangga.yaml") -> None:
        self.root = Path(project_root).resolve()
        self.config_path = self.root / config_name
        self.graph_path = self.root / "airlangga-graph.json"
        self.files_root = self.root / "files"
        self.settings_path = self.root / ".airlangga-ui.json"
        self.secrets_path = self.root / ".airlangga-secrets.json"
        self.token_file = resolve_token_file(self.root)
        self.runs_dir = self.root / "runs"
        self.files_root.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.runs: dict[str, dict[str, Any]] = {}
        if not (self.files_root / "superagent.md").exists():
            (self.files_root / "superagent.md").write_text(SAMPLE_CHARTER, encoding="utf-8")

    # -- config -------------------------------------------------------------
    def load_config(self) -> AirlanggaConfig:
        return AirlanggaConfig.load(self.config_path)

    def save_config(self, config: AirlanggaConfig) -> None:
        with self._lock:
            self.config_path.write_text(
                yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
                encoding="utf-8",
            )

    # -- graph ---------------------------------------------------------------
    def default_graph(self, config: AirlanggaConfig) -> dict:
        nodes: list[dict] = []
        edges: list[dict] = []
        folder_paths = {e["path"] for e in self.file_tree() if e.get("type") == "folder"}
        nodes.append(_node("main_brain", "main_brain", "Main Brain", 60, 60,
                           {"provider": config.main_brain.provider, "model": config.main_brain.model}))
        # Shared model nodes: identical (provider, model, endpoint,
        # auth_ref) tuples render as ONE node powering every brain /
        # member that uses it — "which brains Model A powers".
        model_nodes: dict[tuple, str] = {}

        def model_node_for(provider, model, endpoint, auth_ref, wire_format, capabilities, cost) -> str:
            key = (provider, model, endpoint, auth_ref)
            if key in model_nodes:
                return model_nodes[key]
            mid = unique_model_id(f"model:{_model_slug(provider, model, endpoint, auth_ref)}")
            ypos = 60 + 130 * len(model_nodes)
            nodes.append(_node(mid, "model", f"{provider}/{model}", 1020, ypos,
                               {"provider": provider, "model": model, "endpoint": endpoint,
                                "auth_ref": auth_ref, "wire_format": wire_format,
                                "capabilities": list(capabilities or []),
                                "cost_per_mtok_usd": cost}))
            model_nodes[key] = mid
            return mid

        def unique_model_id(base: str) -> str:
            candidate, n = base, 2
            existing = {nd['id'] for nd in nodes}
            while candidate in existing:
                candidate = f"{base}-{n}"
                n += 1
            return candidate

        mb = config.main_brain
        mb_model = model_node_for(mb.provider, mb.model, mb.endpoint, mb.auth_ref,
                                  mb.wire_format, mb.capabilities, mb.cost_per_mtok_usd)
        edges.append(_edge("e-powers-main", mb_model, "main_brain", "powers"))
        y = 60
        for team_name, team in config.teams.items():
            team_id = f"team:{team_name}"
            nodes.append(_node(team_id, "team", team_name, 380, y,
                               {"template": team.template, "goal": team.goal,
                                "team_brain_mode": team.team_brain_mode, "lead_member": team.lead_member}))
            edges.append(_edge(f"e-main-{team_name}", "main_brain", team_id, "assigns"))
            my = y
            for member in team.members:
                member_id = f"member:{team_name}:{member.id}"
                nodes.append(_node(member_id, "member", member.id, 700, my,
                                   {"role": member.role, "team": team_name,
                                    "charter_file": member.charter_file,
                                    "attached_files": member.attached_files,
                                    "toolsets": member.toolsets, "skills": member.skills,
                                    "approval": member.approval}))
                edges.append(_edge(f"e-team-{team_name}-{member.id}", team_id, member_id, "has_member"))
                model_id = model_node_for(member.provider, member.model, member.endpoint,
                                          member.auth_ref, member.wire_format,
                                          member.capabilities, member.cost_per_mtok_usd)
                edges.append(_edge(f"e-model-{team_name}-{member.id}", member_id, model_id, "uses_model"))
                for tool in member.toolsets:
                    tool_id = f"tool:{tool}"
                    if not any(n["id"] == tool_id for n in nodes):
                        nodes.append(_node(tool_id, "tool", tool, 1340, 60 + 90 * len([n for n in nodes if n["type"] == "tool"]), {"toolset": tool}))
                    edges.append(_edge(f"e-tool-{team_name}-{member.id}-{tool}", member_id, tool_id, "uses_tool"))
                for skill in member.skills:
                    skill_id = f"skill:{skill}"
                    if not any(n["id"] == skill_id for n in nodes):
                        nodes.append(_node(skill_id, "skill", f"{skill}.yaml", 1340, 60 + 90 * len([n for n in nodes if n["type"] == "skill"]), {"path": f"{skill}.yaml"}))
                    edges.append(_edge(f"e-skill-{team_name}-{member.id}-{skill}", member_id, skill_id, "uses_skill"))
                if member.charter_file:
                    file_id = f"file:{member.charter_file}"
                    if not any(n["id"] == file_id for n in nodes):
                        nodes.append(_node(file_id, "file", member.charter_file, 1340, 420, {"path": member.charter_file}))
                    edges.append(_edge(f"e-charter-{team_name}-{member.id}", member_id, file_id, "has_charter"))
                for attached in member.attached_files:
                    # An attached path that is a folder on disk (or
                    # ends in '/') renders as a folder: node, so a
                    # saved member -> folder edge stays in fresh_keys
                    # and is not dropped as contradicting the config.
                    is_folder = attached in folder_paths or attached.endswith("/")
                    node_type = "folder" if is_folder else "file"
                    file_id = f"{node_type}:{attached}"
                    if not any(n["id"] == file_id for n in nodes):
                        nodes.append(_node(file_id, node_type, attached, 1340, 480, {"path": attached}))
                    edges.append(_edge(f"e-file-{team_name}-{member.id}-{attached}", member_id, file_id, "has_file"))
                my += 130
            y = my + 40
        return {"nodes": nodes, "edges": edges}

    def load_graph(self) -> dict:
        config = self.load_config()
        if not self.graph_path.exists():
            graph = self.default_graph(config)
            self.save_graph(graph)
            return graph
        graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
        return self._sync_graph(config, graph)

    def save_graph(self, graph: dict) -> dict:
        self._validate_graph(graph)
        with self._lock:
            self.graph_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
        return graph

    def _validate_graph(self, graph: dict) -> None:
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        ids = [n.get("id") for n in nodes]
        if len(ids) != len(set(ids)):
            raise UIError("graph node ids must be unique")
        for node in nodes:
            if node.get("type") not in NODE_TYPES:
                raise UIError(f"unknown node type: {node.get('type')!r}")
        known = set(ids)
        for edge in edges:
            if edge.get("kind") not in EDGE_KINDS:
                raise UIError(f"unknown edge kind: {edge.get('kind')!r}")
            if edge.get("from") not in known or edge.get("to") not in known:
                raise UIError(f"edge {edge.get('id')!r} references an unknown node")

    def _sync_graph(self, config: AirlanggaConfig, graph: dict) -> dict:
        """Merge the saved graph with the current config: keep saved
        positions, add nodes for new config entries, drop stale ones.

        Every node the user saved is kept — including graph-added
        team/member/tool/skill/model nodes that have no config backing
        yet. An earlier version dropped those on load (only file/folder
        nodes survived), so a node created in the graph silently
        vanished on the next reload. Stale config-derived nodes are
        removed only by an explicit delete (see _prune_graph_nodes),
        never by a plain load.

        Edges are reconciled the same way: a config-derived edge that
        contradicts the current config (e.g. a has_charter edge whose
        member no longer has that charter) is dropped, so deleting a
        connection in the graph and saving it cannot resurrect on the
        next load. Edges touching draft (not-yet-in-config) nodes and
        graph-only depends_on edges are always kept.
        """
        kept = {n["id"]: n for n in graph.get("nodes", [])}
        fresh = self.default_graph(config)
        # Endpoint tuples already covered by a saved model node, so a
        # fresh shared model node for the same endpoint is not duplicated
        # and fresh edges pointing at it are rewired to the saved node.
        covered: dict[tuple, str] = {}
        for n in kept.values():
            if n.get("type") == "model":
                d = n.get("data", {}) or {}
                covered[(d.get("provider"), d.get("model"), d.get("endpoint"), d.get("auth_ref"))] = n["id"]
        rewire: dict[str, str] = {}
        # A saved folder node covers an attachment path: a fresh
        # file: node for the same path must not be duplicated, and
        # fresh has_file edges are rewired to the folder node (same
        # mechanism as the model-node dedup above). This keeps a
        # member -> folder edge alive even when the folder path
        # does not exist on disk yet (custom path from the picker).
        saved_folders = {}
        for n in kept.values():
            if n.get("type") == "folder":
                p = (n.get("data") or {}).get("path") or n.get("label")
                if p:
                    saved_folders[p] = n["id"]
        for node in fresh["nodes"]:
            if node["type"] == "model":
                d = node.get("data", {}) or {}
                key = (d.get("provider"), d.get("model"), d.get("endpoint"), d.get("auth_ref"))
                if key in covered:
                    rewire[node["id"]] = covered[key]
                    continue
            if node["type"] == "file":
                p = (node.get("data") or {}).get("path")
                if p in saved_folders:
                    rewire[node["id"]] = saved_folders[p]
                    continue
            kept.setdefault(node["id"], node)
        nodes = list(kept.values())
        ids = {n["id"] for n in nodes}
        fresh_edges = []
        for e in fresh["edges"]:
            e = dict(e)
            e["from"] = rewire.get(e.get("from", ""), e.get("from", ""))
            e["to"] = rewire.get(e.get("to", ""), e.get("to", ""))
            fresh_edges.append(e)
        fresh_keys = {(e["from"], e["to"], e["kind"]) for e in fresh_edges}
        saved_edges = [e for e in graph.get("edges", [])
                       if e.get("from") in ids and e.get("to") in ids]
        edges = [e for e in saved_edges
                 if self._edge_still_valid(config, nodes, e, fresh_keys)]
        # Add any missing config-derived edges.
        have = {(e["from"], e["to"], e["kind"]) for e in edges}
        for edge in fresh_edges:
            key = (edge["from"], edge["to"], edge["kind"])
            if key not in have and edge["from"] in ids and edge["to"] in ids:
                edges.append(edge)
        # Drop orphaned model nodes: a saved per-member model node whose
        # endpoint tuple is covered by another model node AND which no
        # edge touches anymore (left behind by dedup rewiring).
        used = {e["from"] for e in edges} | {e["to"] for e in edges}
        by_tuple: dict[tuple, list[dict]] = {}
        for n in nodes:
            if n.get("type") == "model":
                d = n.get("data", {}) or {}
                by_tuple.setdefault((d.get("provider"), d.get("model"), d.get("endpoint"), d.get("auth_ref")), []).append(n)
        drop_ids = set()
        for group in by_tuple.values():
            if len(group) > 1:
                for n in group:
                    if n["id"] not in used:
                        drop_ids.add(n["id"])
        if drop_ids:
            nodes = [n for n in nodes if n["id"] not in drop_ids]
        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _edge_still_valid(config: AirlanggaConfig, nodes: list[dict],
                          edge: dict, fresh_keys: set) -> bool:
        """True when a saved graph edge survives a config sync. A
        config-derived edge that the current config no longer implies
        is dropped (it was deleted); edges touching draft nodes and
        graph-only depends_on edges are always kept."""
        kind = edge.get("kind")
        if kind == "depends_on":
            return True
        key = (edge.get("from"), edge.get("to"), kind)
        if key in fresh_keys:
            return True
        by_id = {n.get("id"): n for n in nodes}
        src = by_id.get(edge.get("from", ""))
        dst = by_id.get(edge.get("to", ""))
        if src is None or dst is None:
            return False

        def member_in_config(node: dict | None) -> bool:
            if node is None or node.get("type") != "member":
                return False
            label = node.get("label")
            return any(m.id == label for t in config.teams.values() for m in t.members)

        def team_in_config(node: dict | None) -> bool:
            if node is None or node.get("type") != "team":
                return False
            return node.get("id", "").removeprefix("team:") in config.teams

        if kind == "assigns":
            return not team_in_config(dst)
        if kind == "has_member":
            return not team_in_config(src) or not member_in_config(dst)
        if kind in ("has_charter", "has_file", "uses_tool", "uses_skill", "uses_model"):
            return not member_in_config(src)
        if kind == "powers":
            if dst.get("type") == "main_brain":
                return False
            return not member_in_config(dst)
        return True

    def _prune_graph_nodes(self, team: str, member: str | None = None) -> None:
        """Drop the graph nodes of a team (or one member) after an
        explicit delete through the API. This is the ONLY place saved
        graph nodes are removed: a plain load never drops anything,
        so user-created nodes survive. Shared tool/file nodes are
        left alone — another member may still use them."""
        if not self.graph_path.exists():
            return
        try:
            graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        def doomed(nid: str) -> bool:
            if member is None:
                return (nid == f"team:{team}"
                        or nid.startswith(f"member:{team}:")
                        or nid.startswith(f"model:{team}:"))
            return nid in (f"member:{team}:{member}", f"model:{team}:{member}")

        nodes = [n for n in graph.get("nodes", []) if not doomed(str(n.get("id", "")))]
        if len(nodes) == len(graph.get("nodes", [])):
            return
        kept_ids = {n["id"] for n in nodes}
        edges = [e for e in graph.get("edges", [])
                 if e.get("from") in kept_ids and e.get("to") in kept_ids]
        with self._lock:
            self.graph_path.write_text(
                json.dumps({"nodes": nodes, "edges": edges}, indent=2), encoding="utf-8")

    @staticmethod
    def _apply_model_data(target: Any, data: dict) -> None:
        """Copy model fields from a graph model node onto a config
        object (Main Brain or member). Only fields the node actually
        carries are overwritten."""
        if data.get("provider"):
            target.provider = data["provider"]
        if data.get("model"):
            target.model = data["model"]
        if "endpoint" in data:
            target.endpoint = data.get("endpoint") or None
        if data.get("auth_ref"):
            target.auth_ref = data["auth_ref"]
        if data.get("wire_format"):
            target.wire_format = data["wire_format"]
        if data.get("capabilities"):
            target.capabilities = list(data["capabilities"])
        if data.get("cost_per_mtok_usd") is not None:
            try:
                target.cost_per_mtok_usd = float(data["cost_per_mtok_usd"])
            except (TypeError, ValueError):
                pass

    def apply_graph_to_config(self, graph: dict) -> tuple[AirlanggaConfig, dict]:
        """Apply graph edits back to airlangga.yaml and canonicalize
        provisional node IDs.

        Full bidirectional reconciliation: teams and members created in
        the graph are created in the config; Main Brain and member
        models follow connected model nodes; member wiring (charter /
        attached files / toolsets / skills) is recomputed
        authoritatively from the graph's current edges, so deleting a
        connection in the graph and saving removes it from the config
        instead of resurrecting on reload. Draft (unassigned) members
        stay in the graph only. Returns (config, canonical_graph) —
        the caller must persist the canonical graph (provisional
        ``team:<ts>`` / ``member:<ts>`` ids rewritten to their
        canonical ``team:<slug>`` / ``member:<team>:<id>`` form).
        """
        config = self.load_config()
        nodes_list: list[dict] = [
            dict(n, data=dict(n.get("data") or {})) for n in graph.get("nodes", [])
        ]
        edges: list[dict] = [dict(e) for e in graph.get("edges", [])]
        nodes: dict[str, dict] = {n["id"]: n for n in nodes_list}

        def rewrite_id(old: str, new: str) -> None:
            if old == new or old not in nodes:
                return
            node = nodes.pop(old)
            node["id"] = new
            nodes[new] = node
            for e in edges:
                if e.get("from") == old:
                    e["from"] = new
                if e.get("to") == old:
                    e["to"] = new

        def unique_id(base: str) -> str:
            candidate, n = base, 2
            while candidate in nodes:
                candidate = f"{base}-{n}"
                n += 1
            return candidate

        # -- canonicalize team nodes ------------------------------------
        team_of_node: dict[str, str] = {}
        for node in list(nodes.values()):
            if node.get("type") != "team":
                continue
            slug = _slug(node.get("label") or "")
            node_id = node["id"]
            suffix = node_id.removeprefix("team:")
            if slug and node_id == f"team:{slug}":
                team_of_node[node_id] = slug
            elif slug and slug in config.teams:
                new_id = unique_id(f"team:{slug}")
                rewrite_id(node_id, new_id)
                team_of_node[new_id] = slug
            elif suffix in config.teams:
                # Config-backed team whose label was renamed: identity
                # stays the config name; the label is display-only.
                team_of_node[node_id] = suffix
            elif slug:
                new_id = unique_id(f"team:{slug}")
                rewrite_id(node_id, new_id)
                team_of_node[new_id] = slug
            # else: unusable label — stays in the graph only.

        # -- canonicalize member nodes ----------------------------------
        member_team: dict[str, str] = {}
        for e in edges:
            if e.get("kind") == "has_member":
                member_team[e.get("to", "")] = e.get("from", "")
        member_of_node: dict[str, tuple[str, str]] = {}
        for node in list(nodes.values()):
            if node.get("type") != "member":
                continue
            node_id = node["id"]
            team_node = member_team.get(node_id)
            team_name = team_of_node.get(team_node or "") if team_node else None
            if team_name is None:
                team_name = node.get("data", {}).get("team")
            member_slug = _slug(node.get("label") or "")
            existing: tuple[str, str] | None = None
            if node_id.startswith("member:"):
                rest = node_id[len("member:"):]
                if ":" in rest:
                    t, m = rest.split(":", 1)
                    if t in config.teams and any(x.id == m for x in config.teams[t].members):
                        existing = (t, m)
            if existing is not None:
                member_of_node[node_id] = existing
                continue
            if team_name and member_slug:
                canonical = unique_id(f"member:{team_name}:{member_slug}")
                if node_id != canonical:
                    rewrite_id(node_id, canonical)
                    node_id = canonical
                member_of_node[node_id] = (team_name, member_slug)
            # else: unassigned draft — stays in the graph only.

        # -- main brain ---------------------------------------------------
        mb_node = nodes.get("main_brain")
        if mb_node is not None:
            self._apply_model_data(config.main_brain, mb_node.get("data", {}) or {})
        for e in edges:
            model_node = None
            if e.get("kind") == "powers" and e.get("to") == "main_brain":
                model_node = nodes.get(e.get("from", ""))
            elif e.get("kind") == "uses_model" and e.get("from") == "main_brain":
                model_node = nodes.get(e.get("to", ""))
            if model_node is not None and model_node.get("type") == "model":
                self._apply_model_data(config.main_brain, model_node.get("data", {}) or {})

        # -- teams ---------------------------------------------------------
        for node_id, team_name in list(team_of_node.items()):
            node = nodes.get(node_id)
            if node is None:
                continue
            d = node.get("data", {}) or {}
            team = config.teams.get(team_name)
            budget = d.get("team_budget")
            if isinstance(budget, (int, float)):
                budget = {"usd": budget}
            if team is None:
                team = TeamConfig.model_validate({
                    "template": d.get("template") or "research",
                    "goal": d.get("goal") or "",
                    "team_budget": budget or {},
                    "team_brain_mode": d.get("team_brain_mode") or "lead_member",
                    "lead_member": d.get("lead_member"),
                    "members": [],
                })
                config.teams[team_name] = team
            else:
                if d.get("template"):
                    team.template = d["template"]
                if "goal" in d:
                    team.goal = d.get("goal") or ""
                if d.get("team_brain_mode"):
                    team.team_brain_mode = d["team_brain_mode"]
                if d.get("lead_member"):
                    team.lead_member = d["lead_member"]
                if budget:
                    team.team_budget = Budget.model_validate(budget)

        # -- members ------------------------------------------------------
        def model_data_for(node_id: str) -> dict | None:
            for e in edges:
                if e.get("kind") == "uses_model" and e.get("from") == node_id:
                    target = nodes.get(e.get("to", ""))
                    if target is not None and target.get("type") == "model":
                        return target.get("data", {}) or {}
                if e.get("kind") == "powers" and e.get("to") == node_id:
                    source = nodes.get(e.get("from", ""))
                    if source is not None and source.get("type") == "model":
                        return source.get("data", {}) or {}
            return None

        def wiring_for(node_id: str, node_data: dict, draft: bool) -> dict:
            charter = None
            attached: list[str] = []
            toolsets: list[str] = []
            skills: list[str] = []
            for e in edges:
                if e.get("from") != node_id:
                    continue
                target = nodes.get(e.get("to", ""))
                if target is None:
                    continue
                kind = e.get("kind")
                tdata = target.get("data", {}) or {}
                if kind == "has_charter" and target.get("type") == "file":
                    charter = tdata.get("path") or target.get("label")
                elif kind == "has_file" and target.get("type") in ("file", "folder"):
                    p = tdata.get("path") or target.get("label")
                    if p and p not in attached:
                        attached.append(p)
                elif kind == "uses_tool" and target.get("type") == "tool":
                    t = tdata.get("toolset") or target.get("label")
                    if t and t not in toolsets:
                        toolsets.append(t)
                elif kind == "uses_skill" and target.get("type") == "skill":
                    s = (tdata.get("path") or target.get("label") or "").removesuffix(".yaml")
                    if s and s not in skills:
                        skills.append(s)
            if draft:
                # A draft member has no config yet: inspector checkbox
                # edits in node.data are merged with the graph edges.
                for p in node_data.get("attached_files") or []:
                    if p not in attached:
                        attached.append(p)
                for t in node_data.get("toolsets") or []:
                    if t not in toolsets:
                        toolsets.append(t)
                for s in node_data.get("skills") or []:
                    if s not in skills:
                        skills.append(s)
                if charter is None and node_data.get("charter_file"):
                    charter = node_data["charter_file"]
            return {"charter_file": charter, "attached_files": attached,
                    "toolsets": toolsets, "skills": skills}

        for node_id, (team_name, member_id) in list(member_of_node.items()):
            node = nodes.get(node_id)
            if node is None:
                continue
            team = config.teams.get(team_name)
            if team is None:
                continue
            d = node.get("data", {}) or {}
            existing = next((m for m in team.members if m.id == member_id), None)
            if existing is None:
                # Maybe the member lives in another team: move it.
                for other_name, other in config.teams.items():
                    found = next((m for m in other.members if m.id == member_id), None)
                    if found is not None:
                        other.members = [m for m in other.members if m.id != member_id]
                        if other.lead_member == member_id:
                            other.lead_member = other.members[0].id if other.members else None
                        existing = found
                        break
            wiring = wiring_for(node_id, d, draft=existing is None)
            model_data = model_data_for(node_id)
            if existing is None:
                body: dict[str, Any] = {
                    "id": member_id,
                    "role": d.get("role") or "researcher",
                    "provider": "mock", "model": "mock",
                    "endpoint": None, "auth_ref": "none",
                    "wire_format": "mock",
                    "capabilities": ["tool_calling", "structured_json"],
                    "toolsets": wiring["toolsets"], "skills": wiring["skills"],
                    "charter_file": wiring["charter_file"],
                    "attached_files": wiring["attached_files"],
                    "approval": d.get("approval") or "smart",
                }
                if model_data:
                    for key in ("provider", "model", "endpoint", "auth_ref",
                                "wire_format", "capabilities", "cost_per_mtok_usd"):
                        if model_data.get(key) is not None:
                            body[key] = model_data[key]
                team.members.append(MemberConfig.model_validate(body))
            else:
                if d.get("role"):
                    existing.role = d["role"]
                if d.get("approval"):
                    existing.approval = d["approval"]
                if isinstance(d.get("budget"), dict) and d["budget"].get("usd") is not None:
                    existing.budget = Budget.model_validate(d["budget"])
                existing.charter_file = wiring["charter_file"]
                existing.attached_files = wiring["attached_files"]
                existing.toolsets = wiring["toolsets"]
                existing.skills = wiring["skills"]
                if model_data:
                    self._apply_model_data(existing, model_data)
        # Lead member fallback: a lead-mode team always has a lead when
        # it has members.
        for team in config.teams.values():
            if team.team_brain_mode == "lead_member":
                ids = [m.id for m in team.members]
                if ids and team.lead_member not in ids:
                    team.lead_member = ids[0]
        self.save_config(config)
        canonical = {"nodes": list(nodes.values()), "edges": edges}
        return config, canonical

    # -- files (scoped to files/) --------------------------------------------
    def resolve_file(self, rel: str) -> Path:
        """Resolve a user file path inside files/. Raises UIError on
        traversal escapes and credential paths."""
        if not rel or rel.startswith("/"):
            raise UIError("file path must be relative, e.g. 'notes/brief.md'")
        if is_write_denied(rel):
            raise UIError(f"refused: credential path {rel!r} is never editable here")
        candidate = (self.files_root / rel).resolve()
        try:
            candidate.relative_to(self.files_root.resolve())
        except ValueError:
            raise UIError(f"refused: path {rel!r} escapes the files root") from None
        return candidate

    def file_tree(self) -> list[dict]:
        out: list[dict] = []
        for path in sorted(self.files_root.rglob("*")):
            if path.is_dir():
                out.append({"path": str(path.relative_to(self.files_root)), "type": "folder"})
            else:
                out.append({"path": str(path.relative_to(self.files_root)), "type": "file",
                            "size": path.stat().st_size})
        return out

    def read_file(self, rel: str) -> str:
        target = self.resolve_file(rel)
        if not target.exists() or not target.is_file():
            raise UIError(f"no such file: {rel!r}")
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise UIError(
                "Binary file cannot be edited as text.",
                {"binary": True, "size": target.stat().st_size},
            ) from None

    def write_file(self, rel: str, content: str) -> str:
        target = self.resolve_file(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return rel

    def delete_file(self, rel: str) -> None:
        target = self.resolve_file(rel)
        if target.is_dir():
            if any(target.iterdir()):
                raise UIError(f"folder {rel!r} is not empty; delete its files first")
            target.rmdir()
        elif target.exists():
            target.unlink()
        else:
            raise UIError(f"no such file: {rel!r}")

    def import_zip(self, raw: bytes, dest: str = "", overwrite: bool = False) -> dict:
        """Validate a ZIP archive fully in memory, then extract it under
        files/. Atomic: any rejected entry means nothing is written."""
        if len(raw) < 4 or raw[:4] not in (b"PK\x03\x04", b"PK\x05\x06"):
            raise UIError("File is not a valid ZIP archive.", {"code": "not_a_zip"})
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            raise UIError("File is not a valid ZIP archive.", {"code": "not_a_zip"})
        dest = (dest or "").strip().strip("/")
        if dest:
            self.resolve_file(dest)  # blocks traversal + credential folders
        extracted: list[dict] = []
        skipped: list[str] = []
        ignored_metadata = 0
        declared_total = 0
        file_count = 0
        entries: list[tuple[str, zipfile.ZipInfo]] = []
        for info in zf.infolist():
            raw_name = info.filename.replace("\\", "/")
            base = raw_name.rstrip("/").rsplit("/", 1)[-1]
            if raw_name.startswith("__MACOSX/") or raw_name == "__MACOSX" or base in (".DS_Store", "Thumbs.db"):
                ignored_metadata += 1
                continue
            if info.flag_bits & 0x1:
                raise UIError(f"Password-protected ZIP entries are not supported: {raw_name}",
                              {"code": "encrypted_entry", "entry": raw_name})
            if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise UIError(f"Symbolic links inside ZIP archives are not allowed: {raw_name}",
                              {"code": "symlink_entry", "entry": raw_name})
            parts = [p for p in raw_name.split("/") if p not in ("", ".")]
            if (raw_name.startswith("/") or re.match(r"^[A-Za-z]:", raw_name)
                    or "\x00" in raw_name or ".." in parts):
                raise UIError(f"Unsafe path blocked: {raw_name}",
                              {"code": "path_traversal", "entry": raw_name})
            if info.is_dir():
                continue
            clean = "/".join(parts)
            rel = f"{dest}/{clean}" if dest else clean
            if is_write_denied(rel):
                raise UIError(f"Restricted credential path blocked: {rel}",
                              {"code": "credential_path", "entry": raw_name})
            self.resolve_file(rel)  # raises UIError on escape
            file_count += 1
            if file_count > ZIP_MAX_FILES:
                raise UIError(f"Archive contains more than {ZIP_MAX_FILES} files.",
                              {"code": "too_many_files"})
            declared_total += info.file_size
            if declared_total > ZIP_MAX_UNCOMPRESSED_BYTES:
                raise UIError("Extracted content exceeds the 25 MB safety limit.",
                              {"code": "uncompressed_too_large"})
            if info.file_size > 1_048_576 and (info.compress_size == 0
                    or info.file_size / info.compress_size > ZIP_MAX_RATIO):
                raise UIError(f"Suspicious compression ratio blocked on entry: {raw_name}",
                              {"code": "zip_bomb_ratio", "entry": raw_name})
            entries.append((rel, info))
        total_bytes = 0
        with self._lock:
            for rel, info in entries:
                target = self.resolve_file(rel)
                if target.exists() and not overwrite:
                    skipped.append(rel)
                    continue
                data = zf.read(info)  # bounded by the validated headers
                total_bytes += len(data)
                if total_bytes > ZIP_MAX_UNCOMPRESSED_BYTES:
                    raise UIError("Extracted content exceeds the 25 MB safety limit.",
                                  {"code": "uncompressed_too_large"})
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                extracted.append({"path": rel, "size": len(data)})
        return {"ok": True, "dest": dest, "extracted": extracted,
                "skipped": skipped, "ignored_metadata": ignored_metadata,
                "total_bytes": total_bytes}

    # -- settings / secrets ----------------------------------------------------
    def load_settings(self) -> dict:
        defaults: dict[str, Any] = {
            "telegram": {"allowlist": [], "bot_token_set": False},
            "approval_default": "smart",
            "budgets": {"run_usd": 20.0, "team_usd": 15.0},
            "cron": [],
        }
        if self.settings_path.exists():
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
            defaults.update(saved)
        defaults["telegram"]["bot_token_set"] = bool(
            os.environ.get("TELEGRAM_BOT_TOKEN") or self._secret("telegram_bot_token")
        )
        return defaults

    def save_settings(self, settings: dict) -> dict:
        settings = {k: v for k, v in settings.items() if k != "telegram_bot_token"}
        token = settings.get("telegram", {}).pop("bot_token", None)
        if token:
            self._set_secret("telegram_bot_token", token)
        with self._lock:
            self.settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return self.load_settings()

    # -- UI token ------------------------------------------------------------
    def read_ui_token(self) -> str | None:
        """Current token from the token file, if the file exists."""
        return parse_token_file(self.token_file)

    def write_ui_token(self, new_token: str) -> None:
        """Persist a new UI token to the token file (mode 0600, single
        ``AIRLANGGA_UI_TOKEN=<value>`` line). The file is the source of
        truth at (re)start, so the new token survives a restart."""
        new_token = validate_new_ui_token(new_token)
        with self._lock:
            self.token_file.write_text(f"AIRLANGGA_UI_TOKEN={new_token}\n", encoding="utf-8")
            os.chmod(self.token_file, 0o600)

    def _secret(self, key: str) -> str | None:
        if not self.secrets_path.exists():
            return None
        return json.loads(self.secrets_path.read_text(encoding="utf-8")).get(key)

    def _set_secret(self, key: str, value: str) -> None:
        data = {}
        if self.secrets_path.exists():
            data = json.loads(self.secrets_path.read_text(encoding="utf-8"))
        data[key] = value
        self.secrets_path.write_text(json.dumps(data), encoding="utf-8")
        os.chmod(self.secrets_path, 0o600)

    # -- runs ------------------------------------------------------------------
    def list_runs(self) -> list[dict]:
        ledger_path = self.runs_dir / "ledger.db"
        out: list[dict] = []
        live = {r["run_id"]: r for r in self.runs.values()}
        bb_path = self.runs_dir / "blackboard.db"
        bb = Blackboard(bb_path) if bb_path.exists() else None
        try:
            if ledger_path.exists():
                store = Ledger(ledger_path)
                try:
                    for run_id in store.run_ids():
                        state = store.reconstruct(run_id)
                        claim_count = (
                            sum(len(entry_to_report(e)["claims"]) for e in bb.list_for_run(run_id))
                            if bb is not None else 0
                        )
                        out.append({
                            "run_id": run_id,
                            "status": live.get(run_id, {}).get("status", "done"),
                            "goal": next((e["payload"].get("goal", "") for e in store.events(run_id)
                                          if e["type"] == "plan_created"), ""),
                            "events": len(store.events(run_id)),
                            "claims": claim_count,
                            "cost_by_actor": state["cost_by_actor"],
                            "contracts": state["contracts"],
                            "member_states": state["member_states"],
                            "dissents": state["dissents"],
                        })
                finally:
                    store.close()
        finally:
            if bb is not None:
                bb.close()
        for run_id, rec in live.items():
            if run_id not in {r["run_id"] for r in out}:
                out.append({"run_id": run_id, "status": rec["status"], "goal": rec.get("goal", ""),
                            "events": 0,
                            "claims": sum(r["claims"] for r in rec.get("reports", [])),
                            "cost_by_actor": {}, "contracts": {},
                            "member_states": {}, "dissents": []})
        return sorted(out, key=lambda r: r["run_id"], reverse=True)

    def run_reports(self, run_id: str) -> list[dict]:
        """Committed member reports for a run, from the blackboard.

        The blackboard is the durable home of team output: commit_report
        stores the full Report model per member. The ledger alone only
        records *that* a report was committed, never its text — which is
        why run output used to be invisible everywhere.
        """
        bb_path = self.runs_dir / "blackboard.db"
        if not bb_path.exists():
            return []
        bb = Blackboard(bb_path)
        try:
            return [_blackboard_entry_to_report(e) for e in bb.list_for_run(run_id)]
        finally:
            bb.close()

    def run_detail(self, run_id: str) -> dict:
        ledger_path = self.runs_dir / "ledger.db"
        if not ledger_path.exists():
            # The run is registered in self.runs but the background thread
            # has not created the ledger yet (load_config + Ledger init
            # take a few ms; on a slow host the first poll can land before
            # that). A known run is "running", not an error — only an
            # unknown run with no ledger at all is a 400.
            live = self.runs.get(run_id)
            if live is not None:
                return {
                    "run_id": run_id,
                    "status": live["status"],
                    "events": [],
                    "reports": [],
                    "cost_by_actor": {},
                    "contracts": {},
                    "member_states": {},
                    "dissents": [],
                    "trace_text": "",
                    "error": live.get("error"),
                }
            raise UIError(f"no runs recorded yet (no ledger at {ledger_path})")
        store = Ledger(ledger_path)
        bb_path = self.runs_dir / "blackboard.db"
        bb = Blackboard(bb_path) if bb_path.exists() else None
        try:
            events = store.events(run_id)
            if not events and run_id not in self.runs:
                raise UIError(f"no such run: {run_id!r}")
            state = store.reconstruct(run_id)
            reports = (
                [_blackboard_entry_to_report(e) for e in bb.list_for_run(run_id)]
                if bb is not None else []
            )
            return {
                "run_id": run_id,
                "status": self.runs.get(run_id, {}).get("status", "done"),
                "events": events,
                "reports": reports,
                "cost_by_actor": state["cost_by_actor"],
                "contracts": state["contracts"],
                "member_states": state["member_states"],
                "dissents": state["dissents"],
                "trace_text": render_trace(store, run_id, blackboard=bb) if events else "",
                "error": self.runs.get(run_id, {}).get("error"),
            }
        finally:
            if bb is not None:
                bb.close()
            store.close()

    def start_run(self, team: str, goal: str, mock: bool = True) -> str:
        run_id = new_run_id()
        self.runs[run_id] = {"run_id": run_id, "team": team, "goal": goal,
                             "status": "running", "error": None}

        def _work() -> None:
            try:
                config = self.load_config()
                if mock:
                    config = _mockify(config)
                run_dir = self.runs_dir
                run_dir.mkdir(parents=True, exist_ok=True)
                ledger = Ledger(run_dir / "ledger.db")
                blackboard = Blackboard(run_dir / "blackboard.db")
                budget = BudgetGovernor()
                budget.set_cap(f"run:{run_id}", config.main_brain.budget)
                runtime = TeamRuntime(
                    config=config, team_name=team, run_id=run_id,
                    ledger=ledger, blackboard=blackboard, budget=budget,
                    workdir=str(run_dir / "artifacts"),
                    files_root=str(self.files_root),
                )
                reports = runtime.run_team(goal)
                self.runs[run_id]["status"] = "done"
                self.runs[run_id]["reports"] = [
                    {"member_id": r.member_id, "verdict": r.verdict_self,
                     "claims": len(r.claims), "cost": r.cost} for r in reports
                ]
                ledger.close()
                blackboard.close()
            except Exception as exc:  # recorded on the run, not raised
                self.runs[run_id]["status"] = "failed"
                self.runs[run_id]["error"] = str(exc)

        threading.Thread(target=_work, daemon=True).start()
        return run_id


def _mockify(config: AirlanggaConfig) -> AirlanggaConfig:
    """Offline demo mode: every endpoint becomes the mock provider."""
    config.main_brain.provider = "mock"
    config.main_brain.wire_format = "mock"
    config.main_brain.auth_ref = "none"
    for team in config.teams.values():
        for member in team.members:
            member.provider = "mock"
            member.wire_format = "mock"
            member.auth_ref = "none"
            member.endpoint = None
            member.fallback = []
    return config


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

def _public_config(config: AirlanggaConfig) -> dict:
    return config.model_dump(mode="json")


class UIHandler(BaseHTTPRequestHandler):
    store: UIStore
    token: str | None = None
    # mtime of the token file the last time it was re-read; the auth
    # check re-reads the file whenever it changes, so a token changed
    # in the UI takes effect immediately, without a server restart.
    _token_lock = threading.Lock()
    _token_file_mtime: float | None = None

    def log_message(self, *args: Any) -> None:
        return None

    @classmethod
    def _current_token(cls) -> str | None:
        """Live UI token: the token file wins when it exists and has
        changed since the last read; otherwise the token the server
        started with (env var / explicit argument)."""
        try:
            mtime = cls.store.token_file.stat().st_mtime
        except OSError:
            return cls.token
        with cls._token_lock:
            if cls._token_file_mtime != mtime:
                value = cls.store.read_ui_token()
                if value:
                    cls.token = value
                cls._token_file_mtime = mtime
            return cls.token

    # -- helpers -------------------------------------------------------------
    def _send(self, status: int, payload: Any, content_type: str = "application/json") -> None:
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        self._send(status, payload)

    def _send_uierror(self, exc: UIError) -> None:
        body: dict[str, Any] = {"error": str(exc)}
        body.update(getattr(exc, "payload", {}) or {})
        self._send_json(400, body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError as exc:
            raise UIError(f"invalid JSON body: {exc}") from exc
        if not isinstance(data, dict):
            raise UIError("JSON body must be an object")
        return data

    def _authorized(self) -> bool:
        token = type(self)._current_token()
        if not token:
            return True
        supplied = self.headers.get("X-Airlangga-Token") or ""
        if not supplied:
            supplied = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return secrets.compare_digest(supplied, token)

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._send_json(401, {"error": "unauthorized: set the X-Airlangga-Token header"})
        return False

    # -- routing ---------------------------------------------------------------
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/health":
                self._send_json(200, {"status": "ok", "token_required": bool(type(self)._current_token())})
                return
            if path in ("/", "/ui", "/ui.html"):
                # The HTML page is served WITHOUT an auth check: it
                # carries the login form. Gating the page itself with a
                # 401 JSON would make a browser unable to ever log in
                # (the login form lives in this page). The page validates
                # the entered token against /api/state and stores it in
                # sessionStorage; the API below still requires the token.
                self._send(200, (PACKAGE_DIR / "ui.html").read_bytes(), "text/html; charset=utf-8")
                return
            if not self._require_auth():
                return
            if path == "/api/state":
                config = self.store.load_config()
                self._send_json(200, {
                    "config": _public_config(config),
                    "graph": self.store.load_graph(),
                    "files": self.store.file_tree(),
                    "settings": self.store.load_settings(),
                    "providers": _all_providers(self.store),
                    "toolsets": TOOLSETS,
                    "runs": self.store.list_runs(),
                })
                return
            if path == "/api/graph":
                self._send_json(200, self.store.load_graph())
                return
            if path == "/api/providers":
                self._send_json(200, {"providers": _all_providers(self.store), "toolsets": TOOLSETS})
                return
            if path == "/api/files":
                rel = query.get("path", [""])[0]
                if rel:
                    self._send_json(200, {"path": rel, "content": self.store.read_file(rel)})
                else:
                    self._send_json(200, {"files": self.store.file_tree()})
                return
            if path == "/api/settings":
                self._send_json(200, self.store.load_settings())
                return
            if path == "/api/skills":
                name = query.get("name", [""])[0]
                if name:
                    if "/" in name or ".." in name:
                        raise UIError("skill name must be a plain filename, e.g. 'research.yaml'")
                    target = self.store.root / "airlangga" / "skills" / name
                    if not target.is_file():
                        raise UIError(f"no such skill: {name!r}")
                    self._send_json(200, {"name": name, "content": target.read_text(encoding="utf-8")})
                    return
                skills_dir = self.store.root / "airlangga" / "skills"
                out = []
                if skills_dir.exists():
                    for p in sorted(skills_dir.glob("*.yaml")):
                        out.append({"name": p.name, "path": str(p.relative_to(self.store.root))})
                self._send_json(200, {"skills": out})
                return
            if path == "/api/runs":
                self._send_json(200, {"runs": self.store.list_runs()})
                return
            if path.startswith("/api/runs/"):
                run_id = path.removeprefix("/api/runs/")
                self._send_json(200, self.store.run_detail(run_id))
                return
            self._send_json(404, {"error": "not found"})
        except UIError as exc:
            self._send_uierror(exc)
        except Exception as exc:  # never leak a stack trace to the browser
            self._send_json(500, {"error": f"server error: {exc}"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if not self._require_auth():
                return
            if path == "/api/graph":
                incoming = self._read_json()
                _config, canonical = self.store.apply_graph_to_config(incoming)
                self.store.save_graph(canonical)
                self._send_json(200, {"ok": True, "graph": canonical})
                return
            if path == "/api/teams":
                body = self._read_json()
                name = str(body.get("name", "")).strip()
                if not name:
                    raise UIError("team name is required")
                config = self.store.load_config()
                if name in config.teams:
                    raise UIError(f"team {name!r} already exists")
                budget_in = body.get("team_budget", {}) or {}
                if isinstance(budget_in, (int, float)):
                    budget_in = {"usd": budget_in}
                team = TeamConfig.model_validate({
                    "template": body.get("template", "research"),
                    "goal": body.get("goal", ""),
                    "team_budget": budget_in,
                    "team_brain_mode": body.get("team_brain_mode", "lead_member"),
                    "lead_member": body.get("lead_member"),
                    "members": body.get("members", []) or [],
                })
                if body.get("seed_members"):
                    for seed in TEAM_SEEDS.get(team.template, []):
                        if any(m.id == seed["id"] for m in team.members):
                            continue
                        team.members.append(MemberConfig.model_validate({
                            "id": seed["id"], "role": seed["role"],
                            "provider": "mock", "model": "mock",
                            "endpoint": None, "auth_ref": "none",
                            "wire_format": "mock",
                            "capabilities": ["tool_calling", "structured_json"],
                            "toolsets": seed.get("toolsets", ["web"]),
                            "skills": [], "approval": "smart",
                            "budget": {"usd": 5.0},
                        }))
                if team.team_brain_mode == "lead_member" and not team.lead_member and team.members:
                    team.lead_member = team.members[0].id
                config.teams[name] = team
                self.store.save_config(config)
                self._send_json(201, {"ok": True, "team": name, "config": _public_config(config)})
                return
            if path.startswith("/api/teams/") and path.endswith("/members"):
                team_name = path.split("/")[3]
                body = self._read_json()
                member = MemberConfig.model_validate(body)
                config = self.store.load_config()
                team = config.team(team_name)
                if any(m.id == member.id for m in team.members):
                    raise UIError(f"member {member.id!r} already exists in team {team_name!r}")
                team.members.append(member)
                if team.team_brain_mode == "lead_member" and not team.lead_member:
                    team.lead_member = member.id
                self.store.save_config(config)
                self._send_json(201, {"ok": True, "member": member.id})
                return
            if path == "/api/files":
                body = self._read_json()
                rel = str(body.get("path", "")).strip()
                content = str(body.get("content", ""))
                if not rel:
                    raise UIError("file path is required")
                if body.get("mkdir"):
                    target = self.store.resolve_file(rel)
                    target.mkdir(parents=True, exist_ok=True)
                    self._send_json(201, {"ok": True, "path": rel})
                    return
                self.store.write_file(rel, content)
                self._send_json(201, {"ok": True, "path": rel})
                return
            if path == "/api/files/import-zip":
                length = int(self.headers.get("Content-Length") or 0)
                if length > ZIP_MAX_UPLOAD_BYTES:
                    # Refuse without reading the body; close the
                    # connection so the unread bytes cannot corrupt
                    # the next request on a keep-alive socket.
                    self.close_connection = True
                    self._send_json(413, {"error": "ZIP file exceeds the 10 MB upload limit.",
                                          "code": "zip_too_large", "max_bytes": ZIP_MAX_UPLOAD_BYTES})
                    return
                raw = self.rfile.read(length) if length else b""
                dest = parse_qs(urlparse(self.path).query).get("dest", [""])[0]
                overwrite = parse_qs(urlparse(self.path).query).get("overwrite", ["0"])[0] == "1"
                try:
                    result = self.store.import_zip(raw, dest=dest, overwrite=overwrite)
                except UIError as exc:
                    code = (exc.payload or {}).get("code")
                    status = 413 if code in ("zip_too_large", "uncompressed_too_large") else 415 if code == "not_a_zip" else 400
                    body: dict[str, Any] = {"error": str(exc)}
                    body.update(exc.payload or {})
                    self._send_json(status, body)
                    return
                self._send_json(200, result)
                return
            if path == "/api/runs":
                body = self._read_json()
                team = str(body.get("team", "")).strip()
                goal = str(body.get("goal", "")).strip()
                if not team or not goal:
                    raise UIError("team and goal are required")
                self.store.load_config().team(team)  # KeyError -> 400 below
                run_id = self.store.start_run(team, goal, mock=bool(body.get("mock", True)))
                self._send_json(202, {"ok": True, "run_id": run_id, "status": "running"})
                return
            if path == "/api/cron/tick":
                settings = self.store.load_settings()
                due = [j for j in settings.get("cron", []) if j.get("enabled", True)]
                started = []
                for job in due:
                    started.append(self.store.start_run(job["team"], job["goal"], mock=True))
                self._send_json(200, {"ok": True, "started_runs": started})
                return
            if path == "/api/settings/ui-token":
                body = self._read_json()
                current = type(self)._current_token() or ""
                supplied_current = body.get("current_token", "")
                if not isinstance(supplied_current, str) or not secrets.compare_digest(supplied_current, current):
                    raise UIError("current token is incorrect")
                new_token = validate_new_ui_token(body.get("new_token"))
                self.store.write_ui_token(new_token)
                # Pick the new token up immediately (the next auth check
                # would re-read the changed file anyway); the old token
                # stops working from this response onward.
                with type(self)._token_lock:
                    type(self).token = new_token
                    try:
                        type(self)._token_file_mtime = self.store.token_file.stat().st_mtime
                    except OSError:
                        type(self)._token_file_mtime = None
                self._send_json(200, {"ok": True})
                return
            self._send_json(404, {"error": "not found"})
        except UIError as exc:
            self._send_uierror(exc)
        except KeyError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"server error: {exc}"})

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if not self._require_auth():
                return
            if path == "/api/main-brain":
                body = self._read_json()
                config = self.store.load_config()
                config.main_brain = MainBrainConfig.model_validate({**config.main_brain.model_dump(), **body})
                self.store.save_config(config)
                self._send_json(200, {"ok": True, "main_brain": config.main_brain.model_dump(mode="json")})
                return
            if path.startswith("/api/teams/") and "/members/" in path:
                parts = path.split("/")
                team_name, member_id = parts[3], parts[5]
                body = self._read_json()
                config = self.store.load_config()
                team = config.team(team_name)
                member = next((m for m in team.members if m.id == member_id), None)
                if member is None:
                    raise UIError(f"no member {member_id!r} in team {team_name!r}")
                merged = {**member.model_dump(), **body}
                team.members = [MemberConfig.model_validate(merged) if m.id == member_id else m for m in team.members]
                self.store.save_config(config)
                self._send_json(200, {"ok": True, "member": member_id})
                return
            if path.startswith("/api/teams/"):
                team_name = path.split("/")[3]
                body = self._read_json()
                config = self.store.load_config()
                team = config.team(team_name)
                merged = {**team.model_dump(), **body}
                config.teams[team_name] = TeamConfig.model_validate(merged)
                self.store.save_config(config)
                self._send_json(200, {"ok": True, "team": team_name})
                return
            if path == "/api/files":
                body = self._read_json()
                rel = str(body.get("path", "")).strip()
                self.store.write_file(rel, str(body.get("content", "")))
                self._send_json(200, {"ok": True, "path": rel})
                return
            if path == "/api/settings":
                settings = self.store.save_settings(self._read_json())
                self._send_json(200, {"ok": True, "settings": settings})
                return
            if path == "/api/skills":
                body = self._read_json()
                name = str(body.get("name", "")).strip()
                content = str(body.get("content", ""))
                if not name or "/" in name or ".." in name:
                    raise UIError("skill name must be a plain filename, e.g. 'research.yaml'")
                from .skills import Skill, load_skill_file, scan_skill_text  # validate before writing
                findings = scan_skill_text(content)
                if findings:
                    raise UIError("skill blocked: " + "; ".join(findings))
                try:
                    Skill.model_validate(yaml.safe_load(content) or {})
                except Exception as exc:
                    raise UIError(f"invalid skill YAML: {exc}") from exc
                target = self.store.root / "airlangga" / "skills" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                load_skill_file(target)
                self._send_json(201, {"ok": True, "skill": name})
                return
            self._send_json(404, {"error": "not found"})
        except UIError as exc:
            self._send_uierror(exc)
        except KeyError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"server error: {exc}"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if not self._require_auth():
                return
            if path.startswith("/api/teams/") and "/members/" in path:
                parts = path.split("/")
                team_name, member_id = parts[3], parts[5]
                config = self.store.load_config()
                team = config.team(team_name)
                before = len(team.members)
                team.members = [m for m in team.members if m.id != member_id]
                if len(team.members) == before:
                    raise UIError(f"no member {member_id!r} in team {team_name!r}")
                if team.lead_member == member_id:
                    team.lead_member = team.members[0].id if team.members else None
                self.store.save_config(config)
                self.store._prune_graph_nodes(team_name, member_id)
                self._send_json(200, {"ok": True})
                return
            if path.startswith("/api/teams/"):
                team_name = path.split("/")[3]
                config = self.store.load_config()
                if team_name not in config.teams:
                    raise UIError(f"no team {team_name!r}")
                del config.teams[team_name]
                self.store.save_config(config)
                self.store._prune_graph_nodes(team_name)
                self._send_json(200, {"ok": True})
                return
            if path == "/api/files":
                rel = query.get("path", [""])[0]
                if not rel:
                    raise UIError("file path is required (?path=...)")
                self.store.delete_file(rel)
                self._send_json(200, {"ok": True, "path": rel})
                return
            self._send_json(404, {"error": "not found"})
        except UIError as exc:
            self._send_uierror(exc)
        except KeyError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"server error: {exc}"})


def make_handler(store: UIStore, token: str | None) -> type[BaseHTTPRequestHandler]:
    class Handler(UIHandler):
        pass
    Handler.store = store
    Handler.token = token
    # Per-server token cache: each server re-reads its own token file.
    Handler._token_lock = threading.Lock()
    Handler._token_file_mtime = None
    return Handler


def run_ui_server(
    project_root: str | Path,
    host: str = "127.0.0.1",
    port: int = UI_DEFAULT_PORT,
    token: str | None = None,
    config_name: str = "airlangga.yaml",
) -> ThreadingHTTPServer:
    """Start the Web UI server. Binding a non-localhost address without a
    UI token is refused: the UI can edit teams, files and settings."""
    token = token if token is not None else os.environ.get("AIRLANGGA_UI_TOKEN")
    if host not in ("127.0.0.1", "localhost", "::1") and not token:
        raise ValueError(
            "refusing to bind a public address without AIRLANGGA_UI_TOKEN set; "
            "set a token or bind 127.0.0.1"
        )
    store = UIStore(project_root, config_name=config_name)
    server = ThreadingHTTPServer((host, port), make_handler(store, token))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
