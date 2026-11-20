"""Member tools: file + terminal + browser, wired through the Policy Engine.

Every tool here is small and scoped: file writes land only inside the
run workspace, terminal commands run without a shell (argv list only)
and are checked against the hardline denylist, and browser fetches go
through the SSRF guard in tools_browser. The TurnLoop's PolicyEngine
call is what enforces per-role allowlists — a tool not in a member's
allowlist is never dispatched, whatever the model asks for.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import tools_browser
from .guardrails import is_hardline, is_write_denied

ToolFn = Callable[[dict[str, Any]], str]


def _scoped_path(workdir: str, path: str) -> Path:
    root = Path(workdir).resolve()
    candidate = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError(f"path {path!r} is outside the run workspace {workdir!r}")
    return candidate


def make_file_tools(workdir: str) -> dict[str, ToolFn]:
    def read_file(args: dict[str, Any]) -> str:
        path = _scoped_path(workdir, str(args["path"]))
        return path.read_text(encoding="utf-8", errors="replace")[:200_000]

    def write_file(args: dict[str, Any]) -> str:
        path_str = str(args["path"])
        if is_write_denied(path_str):
            raise ValueError(f"write to denied path: {path_str}")
        path = _scoped_path(workdir, path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(args.get("content", "")), encoding="utf-8")
        return f"wrote {len(str(args.get('content', '')))} chars to {path}"

    def list_files(args: dict[str, Any]) -> str:
        root = Path(workdir).resolve()
        names = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        return json.dumps(names)

    return {"file_read": read_file, "file_write": write_file, "list_files": list_files}


def make_terminal_tools(timeout_s: int = 30) -> dict[str, ToolFn]:
    def run_command(args: dict[str, Any]) -> str:
        argv = args.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
            raise ValueError("run_command requires argv: a list of strings (no shell)")
        matched = is_hardline(" ".join(argv))
        if matched:
            raise ValueError(f"hardline denylist matched: {matched}")
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s)
        out = (proc.stdout or "") + (proc.stderr or "")
        return f"exit={proc.returncode}\n{out[:50_000]}"

    return {"run_command": run_command}


def make_browser_tools() -> dict[str, ToolFn]:
    def fetch_url(args: dict[str, Any]) -> str:
        return tools_browser.fetch_url(str(args["url"]))

    def search_web(args: dict[str, Any]) -> str:
        results = tools_browser.search_web(str(args["query"]), int(args.get("limit", 5)))
        return json.dumps(results)

    return {"fetch_url": fetch_url, "search_web": search_web}


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "file_read": {
        "name": "file_read",
        "description": "Read a file inside the run workspace.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    "file_write": {
        "name": "file_write",
        "description": "Write a file inside the run workspace.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    },
    "list_files": {
        "name": "list_files",
        "description": "List files in the run workspace.",
        "parameters": {"type": "object", "properties": {}},
    },
    "run_command": {
        "name": "run_command",
        "description": "Run a command (argv list, no shell) with a timeout.",
        "parameters": {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}}}, "required": ["argv"]},
    },
    "fetch_url": {
        "name": "fetch_url",
        "description": "Fetch a public URL and return its page text.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    },
    "search_web": {
        "name": "search_web",
        "description": "Search the web via the registered search provider.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
    },
}


def build_member_tools(toolsets: list[str], workdir: str) -> tuple[dict[str, ToolFn], list[dict[str, Any]]]:
    """Build the tool functions + schemas for a member from its toolsets.

    Toolset names: file_read, file_write, list_files, shell, web.
    Only the requested toolsets are built; the Policy Engine allowlist
    (the built tool names) is the second, enforcing layer.
    """
    file_tools = make_file_tools(workdir)
    terminal_tools = make_terminal_tools()
    browser_tools = make_browser_tools()
    wanted: dict[str, ToolFn] = {}
    for name in toolsets:
        if name in file_tools:
            wanted[name] = file_tools[name]
        elif name == "shell":
            wanted.update(terminal_tools)
        elif name == "web":
            wanted.update(browser_tools)
    schemas = [TOOL_SCHEMAS[name] for name in wanted if name in TOOL_SCHEMAS]
    return wanted, schemas
