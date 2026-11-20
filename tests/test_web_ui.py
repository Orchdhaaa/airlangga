"""Web UI tests: pages, auth, CRUD round-trips, graph save/load,
scoped file editing (traversal + credential paths blocked), runs."""

import json
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from airlangga.web_ui import UI_DEFAULT_PORT, UIError, UIStore, run_ui_server

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _req(base, path, method="GET", body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Airlangga-Token"] = token
    req = urllib.request.Request(
        base + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


@pytest.fixture()
def project(tmp_path):
    """A throwaway project copy: example config + empty runs/files."""
    shutil.copy(PROJECT_ROOT / "airlangga.yaml", tmp_path / "airlangga.yaml")
    return tmp_path


@pytest.fixture()
def server(project):
    srv = run_ui_server(project, host="127.0.0.1", port=0, token="test-token-123")
    port = srv.server_address[1]
    yield f"http://127.0.0.1:{port}", project
    srv.shutdown()
    srv.server_close()


@pytest.fixture()
def open_server(project):
    srv = run_ui_server(project, host="127.0.0.1", port=0, token=None)
    port = srv.server_address[1]
    yield f"http://127.0.0.1:{port}", project
    srv.shutdown()
    srv.server_close()


def test_default_port_is_8100():
    assert UI_DEFAULT_PORT == 8100


def test_health_and_main_page(open_server):
    base, _ = open_server
    status, body = _req(base, "/health")
    assert status == 200 and json.loads(body)["status"] == "ok"
    status, body = _req(base, "/")
    assert status == 200
    assert b"Airlangga" in body and b"Graph" in body
    assert b"node" in body.lower()


def test_token_required_when_set(server):
    base, _ = server
    # The HTML page is served WITHOUT auth: it carries the login form,
    # never a 401 JSON — a browser opening the bare URL must be able
    # to reach the login page (regression: GET / used to 401, so a
    # browser could never log in at all).
    status, body = _req(base, "/")
    assert status == 200, body
    assert body.lstrip().startswith(b"<!DOCTYPE html")
    assert b'id="loginScreen"' in body and b'id="loginForm"' in body
    # It is an HTML page, not the old 401 JSON error body.
    assert not body.lstrip().startswith(b'{"error"')
    # With a valid token the same URL serves the app.
    status, body = _req(base, "/", token="test-token-123")
    assert status == 200
    assert b"Agentic Team Studio" in body
    # The API still requires the token.
    status, _ = _req(base, "/api/state")
    assert status == 401
    status, body = _req(base, "/api/state", token="test-token-123")
    assert status == 200
    state = json.loads(body)
    assert "research-01" in state["config"]["teams"]
    assert state["graph"]["nodes"] and state["graph"]["edges"]
    assert any(p["provider"] == "ollama" for p in state["providers"])


def test_login_page_flow(server):
    base, _ = server
    # 1. No token: login page, 200 HTML with the form, never JSON.
    status, body = _req(base, "/")
    assert status == 200
    assert body.lstrip().startswith(b"<!DOCTYPE html")
    assert not body.lstrip().startswith(b"{")
    assert b'id="loginScreen"' in body
    assert b'id="loginToken"' in body
    # Login submit button (labelled "Enter Studio" in the redesign).
    assert b'Enter Studio' in body
    assert b'id="btnLogin"' in body
    # The client-side wrong-token message exists in the page.
    assert b"Wrong token" in body
    # The token is kept in sessionStorage only — never localStorage,
    # and the login form never puts it in the URL.
    assert b"localStorage" not in body
    # /ui and /ui.html behave the same.
    for p in ("/ui", "/ui.html"):
        status, body = _req(base, p)
        assert status == 200 and b'id="loginScreen"' in body, p
    # 2. ?token= convenience still serves the page (the JS stores the
    # token for the tab and cleans the URL; the server just serves HTML).
    status, body = _req(base, "/?token=test-token-123")
    assert status == 200 and b'id="loginScreen"' in body
    # 3. Login validation is /api/state: a wrong token 401s (the login
    # page shows "Wrong token" on this), the right token 200s.
    status, body = _req(base, "/api/state", token="wrong-token")
    assert status == 401
    assert json.loads(body)["error"].startswith("unauthorized")
    status, _ = _req(base, "/api/state", token="test-token-123")
    assert status == 200
    # 4. API without a token is still 401 JSON — only HTML routes changed.
    status, body = _req(base, "/api/state")
    assert status == 401 and b"unauthorized" in body


def test_public_bind_without_token_refused(project):
    with pytest.raises(ValueError, match="AIRLANGGA_UI_TOKEN"):
        run_ui_server(project, host="0.0.0.0", port=0, token=None)


def test_team_member_crud_round_trip(open_server):
    base, project = open_server
    status, body = _req(base, "/api/teams", method="POST",
                        body={"name": "code-01", "template": "code-review", "goal": "Review this diff."})
    assert status == 201, body
    status, body = _req(base, "/api/teams/code-01/members", method="POST", body={
        "id": "reviewer", "role": "critic", "provider": "deepseek", "model": "deepseek-chat",
        "endpoint": "https://api.deepseek.com/v1", "auth_ref": "env:DEEPSEEK_API_KEY",
        "wire_format": "openai_chat", "capabilities": ["tool_calling", "structured_json"],
        "toolsets": ["web", "file_read"], "budget": {"usd": 3.0}, "approval": "smart",
    })
    assert status == 201, body
    # Persisted in airlangga.yaml.
    text = (project / "airlangga.yaml").read_text(encoding="utf-8")
    assert "code-01" in text and "reviewer" in text and "deepseek-chat" in text
    # Update the member's model.
    status, _ = _req(base, "/api/teams/code-01/members/reviewer", method="PUT",
                    body={"model": "deepseek-reasoner"})
    assert status == 200
    assert "deepseek-reasoner" in (project / "airlangga.yaml").read_text(encoding="utf-8")
    # Duplicate member is refused.
    status, _ = _req(base, "/api/teams/code-01/members", method="POST", body={
        "id": "reviewer", "role": "critic", "provider": "mock", "model": "mock"})
    assert status == 400
    # Delete member, then team.
    status, _ = _req(base, "/api/teams/code-01/members/reviewer", method="DELETE")
    assert status == 200
    status, _ = _req(base, "/api/teams/code-01", method="DELETE")
    assert status == 200
    assert "code-01" not in (project / "airlangga.yaml").read_text(encoding="utf-8")


def test_main_brain_update(open_server):
    base, project = open_server
    status, _ = _req(base, "/api/main-brain", method="PUT",
                    body={"provider": "ollama", "model": "llama3.1:8b",
                          "endpoint": "http://localhost:11434/v1", "wire_format": "openai_chat"})
    assert status == 200
    text = (project / "airlangga.yaml").read_text(encoding="utf-8")
    assert "llama3.1:8b" in text


def test_graph_save_load_and_validation(open_server):
    base, _ = open_server
    status, body = _req(base, "/api/graph")
    assert status == 200
    graph = json.loads(body)
    assert any(n["type"] == "main_brain" for n in graph["nodes"])
    assert any(n["type"] == "model" for n in graph["nodes"])
    # Move a node and save; reload shows the new position.
    node = graph["nodes"][0]
    node["x"], node["y"] = 500, 500
    status, _ = _req(base, "/api/graph", method="POST", body=graph)
    assert status == 200, body
    status, body = _req(base, "/api/graph")
    reloaded = json.loads(body)
    assert next(n for n in reloaded["nodes"] if n["id"] == node["id"])["x"] == 500
    # Edge to an unknown node is refused.
    bad = json.loads(json.dumps(graph))
    bad["edges"].append({"id": "e-bad", "from": "main_brain", "to": "no-such-node", "kind": "assigns"})
    status, _ = _req(base, "/api/graph", method="POST", body=bad)
    assert status == 400
    # Unknown edge kind is refused.
    bad["edges"][-1] = {"id": "e-bad", "from": "main_brain", "to": "main_brain", "kind": "teleport"}
    status, _ = _req(base, "/api/graph", method="POST", body=bad)
    assert status == 400


def test_graph_charter_attach_persists_to_config(open_server):
    base, project = open_server
    # Create a SUPERAGENT-style charter file, then attach it in the graph.
    status, _ = _req(base, "/api/files", method="POST",
                    body={"path": "personas/superagent.md", "content": "# SUPERAGENT\nWork from evidence.\n"})
    assert status == 201, body
    status, body = _req(base, "/api/graph")
    graph = json.loads(body)
    graph["nodes"].append({"id": "file:personas/superagent.md", "type": "file",
                           "label": "personas/superagent.md", "x": 1300, "y": 600,
                           "data": {"path": "personas/superagent.md"}})
    member_node = next(n for n in graph["nodes"] if n["type"] == "member")
    graph["edges"].append({"id": "e-charter-test", "from": member_node["id"],
                           "to": "file:personas/superagent.md", "kind": "has_charter"})
    status, _ = _req(base, "/api/graph", method="POST", body=graph)
    assert status == 200, body
    text = (project / "airlangga.yaml").read_text(encoding="utf-8")
    assert "personas/superagent.md" in text


def test_file_crud_and_scope_guards(open_server):
    base, project = open_server
    # Create + read + edit + delete round-trip.
    status, _ = _req(base, "/api/files", method="POST",
                    body={"path": "notes/brief.md", "content": "hello"})
    assert status == 201
    status, body = _req(base, "/api/files?path=notes/brief.md")
    assert status == 200 and json.loads(body)["content"] == "hello"
    status, _ = _req(base, "/api/files", method="PUT",
                    body={"path": "notes/brief.md", "content": "hello v2"})
    assert status == 200
    status, body = _req(base, "/api/files?path=notes/brief.md")
    assert json.loads(body)["content"] == "hello v2"
    # Traversal escapes are blocked.
    for evil in ("../escape.md", "../../etc/passwd", "/etc/passwd", "a/../../escape.md"):
        status, body = _req(base, "/api/files", method="POST", body={"path": evil, "content": "x"})
        assert status == 400, (evil, body)
    assert not (project / "escape.md").exists()
    # Credential paths are denied.
    for evil in (".env", "keys/id_ed25519", ".ssh/config", "credentials.json"):
        status, _ = _req(base, "/api/files", method="POST", body={"path": evil, "content": "x"})
        assert status == 400, evil
    # Delete.
    status, _ = _req(base, "/api/files?path=notes/brief.md", method="DELETE")
    assert status == 200
    status, _ = _req(base, "/api/files?path=notes/brief.md")
    assert status == 400


def test_settings_round_trip_and_token_never_returned(open_server):
    base, _ = open_server
    status, _ = _req(base, "/api/settings", method="PUT", body={
        "telegram": {"allowlist": [111, 222], "bot_token": "123456:SECRET-TOKEN"},
        "approval_default": "approve",
        "budgets": {"run_usd": 10.0, "team_usd": 8.0},
        "cron": [{"name": "morning", "team": "research-01", "goal": "Brief me.", "interval_min": 60, "enabled": True}],
    })
    assert status == 200, body
    status, body = _req(base, "/api/settings")
    settings = json.loads(body)
    assert settings["telegram"]["allowlist"] == [111, 222]
    assert settings["telegram"]["bot_token_set"] is True
    assert settings["approval_default"] == "approve"
    assert len(settings["cron"]) == 1
    # The token value itself is never returned anywhere.
    assert "SECRET-TOKEN" not in json.dumps(settings)


def test_run_flow_mock_and_trace(open_server):
    base, _ = open_server
    status, body = _req(base, "/api/runs", method="POST",
                        body={"team": "research-01", "goal": "Produce a sourced brief on the Airlangga kingdom.", "mock": True})
    assert status == 202, body
    run_id = json.loads(body)["run_id"]
    # Poll until the background run finishes.
    detail = None
    for _ in range(40):
        status, body = _req(base, f"/api/runs/{run_id}")
        assert status == 200, body
        detail = json.loads(body)
        if detail["status"] in ("done", "failed"):
            break
        time.sleep(0.25)
    assert detail is not None and detail["status"] == "done", detail
    assert detail["events"], "trace must contain ledger events"
    assert "plan_created" in {e["type"] for e in detail["events"]}
    assert detail["cost_by_actor"], "cost per actor must be recorded"
    assert detail["trace_text"] and "Run " in detail["trace_text"]
    # P0 regression: team output must be visible, not just counted.
    # Each member report carries its claim text verbatim.
    assert detail["reports"], "run detail must surface member reports"
    assert len(detail["reports"]) == 3
    for report in detail["reports"]:
        assert report["member_id"] and report["claims"]
        assert any("Mock" in c["claim"] for c in report["claims"]), report
    assert "Outputs:" in detail["trace_text"]
    assert "Mock researcher completed its assigned work" in detail["trace_text"]
    # Runs list includes it.
    status, body = _req(base, "/api/runs")
    assert any(r["run_id"] == run_id for r in json.loads(body)["runs"])
    listed = [r for r in json.loads(body)["runs"] if r["run_id"] == run_id][0]
    assert listed["claims"] == 3
    # Unknown team / empty goal are refused.
    status, _ = _req(base, "/api/runs", method="POST", body={"team": "nope", "goal": "x", "mock": True})
    assert status == 400
    status, _ = _req(base, "/api/runs", method="POST", body={"team": "research-01", "goal": "", "mock": True})
    assert status == 400


def test_run_detail_known_run_without_ledger(project):
    # Regression test for the VPS-only failure: a run registered in
    # self.runs whose background thread has not created runs/ledger.db
    # yet must report "running", not 400. Deterministic: no thread is
    # started, the ledger simply does not exist.
    store = UIStore(project)
    assert not (project / "runs" / "ledger.db").exists()
    store.runs["run-test123"] = {"run_id": "run-test123", "team": "research-01",
                                 "goal": "Brief.", "status": "running", "error": None}
    detail = store.run_detail("run-test123")
    assert detail["status"] == "running"
    assert detail["events"] == []
    assert detail["reports"] == []
    # A failed-before-ledger run surfaces its error instead of a 400.
    store.runs["run-test123"]["status"] = "failed"
    store.runs["run-test123"]["error"] = "boom"
    detail = store.run_detail("run-test123")
    assert detail["status"] == "failed" and detail["error"] == "boom"
    # An unknown run with no ledger at all is still an error.
    with pytest.raises(UIError, match="no runs recorded yet"):
        store.run_detail("run-nope")


@pytest.fixture()
def token_server(project, monkeypatch):
    """Server whose token lives in <project>/.ui-token, like the VPS
    systemd unit (EnvironmentFile). Initial token: initial-token-123."""
    token_file = project / ".ui-token"
    token_file.write_text("AIRLANGGA_UI_TOKEN=initial-token-123\n", encoding="utf-8")
    import os
    os.chmod(token_file, 0o600)
    monkeypatch.setenv("AIRLANGGA_UI_TOKEN_FILE", str(token_file))
    srv = run_ui_server(project, host="127.0.0.1", port=0, token="initial-token-123")
    port = srv.server_address[1]
    yield f"http://127.0.0.1:{port}", project
    srv.shutdown()
    srv.server_close()


def test_ui_token_change_flow(token_server, monkeypatch):
    base, project = token_server
    token_file = project / ".ui-token"
    # No header at all -> 401.
    status, _ = _req(base, "/api/settings/ui-token", method="POST",
                     body={"current_token": "initial-token-123", "new_token": "new-token-456"})
    assert status == 401
    # Wrong current token -> 400, old token still works.
    status, _ = _req(base, "/api/settings/ui-token", method="POST", token="initial-token-123",
                     body={"current_token": "wrong-token", "new_token": "new-token-456"})
    assert status == 400
    status, _ = _req(base, "/api/state", token="initial-token-123")
    assert status == 200
    # Too-short new token -> 400, old token still works.
    status, _ = _req(base, "/api/settings/ui-token", method="POST", token="initial-token-123",
                     body={"current_token": "initial-token-123", "new_token": "short"})
    assert status == 400
    # New token with whitespace -> 400.
    status, _ = _req(base, "/api/settings/ui-token", method="POST", token="initial-token-123",
                     body={"current_token": "initial-token-123", "new_token": "has space-123"})
    assert status == 400
    # Successful change: 200, and neither token value leaks in the body.
    status, body = _req(base, "/api/settings/ui-token", method="POST", token="initial-token-123",
                        body={"current_token": "initial-token-123", "new_token": "new-token-456"})
    assert status == 200, body
    assert "new-token-456" not in body.decode() and "initial-token-123" not in body.decode()
    # Old token is dead immediately, new token works.
    status, _ = _req(base, "/api/state", token="initial-token-123")
    assert status == 401
    status, _ = _req(base, "/api/state", token="new-token-456")
    assert status == 200
    # The token file holds the new token (0600) — so a restart keeps it.
    assert token_file.read_text(encoding="utf-8").strip() == "AIRLANGGA_UI_TOKEN=new-token-456"
    assert token_file.stat().st_mode & 0o777 == 0o600
    # Restart simulation: fresh server, env token as the systemd
    # EnvironmentFile would provide it, file still on disk.
    monkeypatch.setenv("AIRLANGGA_UI_TOKEN", "new-token-456")
    srv = run_ui_server(project, host="127.0.0.1", port=0, token=None)
    try:
        base2 = f"http://127.0.0.1:{srv.server_address[1]}"
        status, _ = _req(base2, "/api/state", token="new-token-456")
        assert status == 200
        status, _ = _req(base2, "/api/state", token="initial-token-123")
        assert status == 401
    finally:
        srv.shutdown()
        srv.server_close()


def test_ui_token_picks_up_external_file_change(token_server):
    # A token file edited outside the server (e.g. by an operator) is
    # picked up on the next auth check, no restart needed.
    base, project = token_server
    status, _ = _req(base, "/api/state", token="initial-token-123")
    assert status == 200
    (project / ".ui-token").write_text("AIRLANGGA_UI_TOKEN=extern-token-789\n", encoding="utf-8")
    status, _ = _req(base, "/api/state", token="initial-token-123")
    assert status == 401
    status, _ = _req(base, "/api/state", token="extern-token-789")
    assert status == 200


def test_cron_tick_starts_runs(open_server):
    base, _ = open_server
    _req(base, "/api/settings", method="PUT", body={
        "telegram": {"allowlist": []}, "approval_default": "smart",
        "budgets": {"run_usd": 20.0, "team_usd": 15.0},
        "cron": [{"name": "tick-test", "team": "research-01", "goal": "Tick brief.", "interval_min": 60, "enabled": True}],
    })
    status, body = _req(base, "/api/cron/tick", method="POST", body={})
    assert status == 200, body
    assert len(json.loads(body)["started_runs"]) == 1


def test_skills_create_validates(open_server):
    base, _ = open_server
    status, body = _req(base, "/api/skills", method="PUT", body={
        "name": "ui-test-skill.yaml",
        "content": "name: ui-test-skill\ndescription: Created from the UI test.\nversion: \"1\"\ninstructions: |\n  Be careful.\ntools: [web]\n",
    })
    assert status == 201, body
    status, body = _req(base, "/api/skills")
    assert any(s["name"] == "ui-test-skill.yaml" for s in json.loads(body)["skills"])

# ---------------------------------------------------------------------------
# Gemini-design P0.10: ZIP import, binary guard, graph persistence,
# per-section settings, charter injection.
# ---------------------------------------------------------------------------

import http.client
import io
import os
import struct
import zipfile
from urllib.parse import urlparse


def _make_zip(entries):
    """entries: list of (name | ZipInfo, bytes). Returns the zip bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return buf.getvalue()


def _req_zip(base, path, raw, token=None):
    headers = {"Content-Type": "application/zip"}
    if token:
        headers["X-Airlangga-Token"] = token
    req = urllib.request.Request(base + path, method="POST", data=raw, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _encrypted_zip_bytes(name="secret.md"):
    """Minimal stored zip whose single entry has the encrypted flag set.
    stdlib writestr() resets flag_bits, so the headers are built by hand."""
    name_b = name.encode()
    local = struct.pack("<IHHHHHIIIHH",
                        0x04034B50, 20, 0x0001, 0, 0, 0, 0, 0, 0,
                        len(name_b), 0) + name_b
    central = struct.pack("<IHHHHHHIIIHHHHHII",
                          0x02014B50, 20, 20, 0x0001, 0, 0, 0, 0, 0, 0,
                          len(name_b), 0, 0, 0, 0, 0, 0) + name_b
    end = struct.pack("<IHHHHIIH",
                      0x06054B50, 0, 0, 1, 1, len(central), len(local), 0)
    return local + central + end


def test_zip_import_valid_dest_and_metadata_ignored(open_server):
    base, _ = open_server
    raw = _make_zip([
        ("a.md", b"# A\n"), ("sub/b.md", b"# B\n"),
        ("__MACOSX/._a.md", b"meta"), (".DS_Store", b"x"),
        ("sub/Thumbs.db", b"x"),
    ])
    status, body = _req_zip(base, "/api/files/import-zip?dest=packs/demo&overwrite=0", raw)
    assert status == 200, body
    data = json.loads(body)
    assert [f["path"] for f in data["extracted"]] == ["packs/demo/a.md", "packs/demo/sub/b.md"]
    assert data["ignored_metadata"] == 3
    status, body = _req(base, "/api/files?path=packs/demo/sub/b.md")
    assert status == 200 and json.loads(body)["content"] == "# B\n"


def test_zip_import_overwrite_skip_vs_overwrite(open_server):
    base, _ = open_server
    status, _ = _req(base, "/api/files", method="POST",
                     body={"path": "keep.md", "content": "original"})
    assert status == 201
    raw = _make_zip([("keep.md", b"new"), ("fresh.md", b"fresh")])
    status, body = _req_zip(base, "/api/files/import-zip?overwrite=0", raw)
    assert status == 200, body
    data = json.loads(body)
    assert data["skipped"] == ["keep.md"]
    assert [f["path"] for f in data["extracted"]] == ["fresh.md"]
    _, body = _req(base, "/api/files?path=keep.md")
    assert json.loads(body)["content"] == "original"
    status, body = _req_zip(base, "/api/files/import-zip?overwrite=1", raw)
    assert status == 200, body
    _, body = _req(base, "/api/files?path=keep.md")
    assert json.loads(body)["content"] == "new"


def test_zip_import_rejects_unsafe_entries_atomically(open_server):
    base, project = open_server
    # Traversal entry in the same archive as a valid file: nothing is written.
    raw = _make_zip([("ok.md", b"ok"), ("../evil.md", b"evil")])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 400, body
    assert json.loads(body)["code"] == "path_traversal"
    status, _ = _req(base, "/api/files?path=ok.md")
    assert status == 400
    assert not (project / "evil.md").exists()
    assert not (project / "files" / "ok.md").exists()
    # Absolute path.
    raw = _make_zip([("/tmp/abs.md", b"x")])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 400 and json.loads(body)["code"] == "path_traversal"
    # Credential path.
    raw = _make_zip([(".env", b"SECRET=1")])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 400, body
    assert json.loads(body)["code"] == "credential_path"
    # Symlink entry.
    info = zipfile.ZipInfo("link.md")
    info.external_attr = 0o120777 << 16
    raw = _make_zip([(info, b"target")])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 400, body
    assert json.loads(body)["code"] == "symlink_entry"
    # Encrypted entry.
    status, body = _req_zip(base, "/api/files/import-zip", _encrypted_zip_bytes())
    assert status == 400, body
    assert json.loads(body)["code"] == "encrypted_entry"


def test_zip_import_rejects_non_zip_too_many_and_oversized(open_server):
    base, _ = open_server
    status, body = _req_zip(base, "/api/files/import-zip", b"hello, not a zip")
    assert status == 415, body
    assert json.loads(body)["code"] == "not_a_zip"
    # 201 files.
    raw = _make_zip([(f"f{i:03d}.md", b"x") for i in range(201)])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 400, body
    assert json.loads(body)["code"] == "too_many_files"
    # Zip bomb ratio: 2 MB of zeros compresses to ~2 KB (ratio ~1000:1).
    raw = _make_zip([("zeros.bin", b"\x00" * (2 * 1024 * 1024))])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 400, body
    assert json.loads(body)["code"] == "zip_bomb_ratio"
    # Uncompressed over 25 MB with a ~3:1 ratio (2-bit entropy data), so the
    # upload stays under the 10 MB limit while the total still exceeds it.
    table = bytes([i % 4 for i in range(256)])
    big = os.urandom(26 * 1024 * 1024).translate(table)
    raw = _make_zip([("rand.bin", big)])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 413, body
    assert json.loads(body)["code"] == "uncompressed_too_large"


def test_zip_import_too_large_is_413_without_reading_body(server):
    # The route refuses on Content-Length alone and closes the connection,
    # so the body is never sent: headers only, then read the 413.
    base, _ = server
    u = urlparse(base)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=10)
    conn.putrequest("POST", "/api/files/import-zip")
    conn.putheader("Content-Type", "application/zip")
    conn.putheader("X-Airlangga-Token", "test-token-123")
    conn.putheader("Content-Length", str(11 * 1024 * 1024))
    conn.endheaders()
    resp = conn.getresponse()
    assert resp.status == 413, resp.status
    assert json.loads(resp.read())["code"] == "zip_too_large"
    conn.close()


def test_zip_import_requires_auth(server):
    base, _ = server
    raw = _make_zip([("a.md", b"x")])
    status, body = _req_zip(base, "/api/files/import-zip", raw)
    assert status == 401, body
    status, body = _req_zip(base, "/api/files/import-zip", raw, token="test-token-123")
    assert status == 200, body


def test_binary_file_get_returns_400(open_server):
    base, project = open_server
    files_dir = project / "files"
    files_dir.mkdir(exist_ok=True)
    (files_dir / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    status, body = _req(base, "/api/files?path=pic.png")
    assert status == 400, body
    data = json.loads(body)
    assert data.get("binary") is True
    assert data.get("size") == 72


def test_graph_added_team_member_and_wiring_persists(open_server):
    base, project = open_server
    status, _ = _req(base, "/api/files", method="POST",
                     body={"path": "personas/scout.md", "content": "# SCOUT\n"})
    assert status == 201
    status, body = _req(base, "/api/graph")
    graph = json.loads(body)
    graph["nodes"] += [
        {"id": "team:tmp1", "type": "team", "label": "graphteam", "x": 380, "y": 700,
         "data": {"template": "blank", "team_budget": {"usd": 7}, "team_brain_mode": "lead_member"}},
        {"id": "member:tmp1", "type": "member", "label": "scout", "x": 700, "y": 700,
         "data": {"role": "scout", "approval": "smart"}},
        {"id": "model:graph-model", "type": "model", "label": "mock/mock", "x": 1020, "y": 700,
         "data": {"provider": "mock", "model": "mock", "auth_ref": "none",
                  "wire_format": "mock", "capabilities": ["tool_calling"],
                  "cost_per_mtok_usd": 0}},
        {"id": "file:personas/scout.md", "type": "file", "label": "personas/scout.md",
         "x": 1340, "y": 700, "data": {"path": "personas/scout.md"}},
        {"id": "tool:web", "type": "tool", "label": "web", "x": 1340, "y": 800,
         "data": {"toolset": "web"}},
        {"id": "skill:research", "type": "skill", "label": "research.yaml", "x": 1340, "y": 900,
         "data": {"path": "research.yaml"}},
    ]
    graph["edges"] += [
        {"id": "e-g-assigns", "from": "main_brain", "to": "team:tmp1", "kind": "assigns"},
        {"id": "e-g-member", "from": "team:tmp1", "to": "member:tmp1", "kind": "has_member"},
        {"id": "e-g-model", "from": "member:tmp1", "to": "model:graph-model", "kind": "uses_model"},
        {"id": "e-g-powers", "from": "model:graph-model", "to": "main_brain", "kind": "powers"},
        {"id": "e-g-charter", "from": "member:tmp1", "to": "file:personas/scout.md", "kind": "has_charter"},
        {"id": "e-g-tool", "from": "member:tmp1", "to": "tool:web", "kind": "uses_tool"},
        {"id": "e-g-skill", "from": "member:tmp1", "to": "skill:research", "kind": "uses_skill"},
    ]
    status, body = _req(base, "/api/graph", method="POST", body=graph)
    assert status == 200, body
    text = (project / "airlangga.yaml").read_text(encoding="utf-8")
    assert "graphteam" in text
    assert "personas/scout.md" in text
    # Reload: canonical ids + wiring survive the round-trip.
    status, body = _req(base, "/api/graph")
    reloaded = json.loads(body)
    member_node = next(n for n in reloaded["nodes"] if n["type"] == "member" and n["label"] == "scout")
    assert member_node["id"] == "member:graphteam:scout"
    kinds = {(e["from"], e["to"], e["kind"]) for e in reloaded["edges"]}
    assert ("member:graphteam:scout", "model:graph-model", "uses_model") in kinds
    assert ("model:graph-model", "main_brain", "powers") in kinds
    assert ("member:graphteam:scout", "file:personas/scout.md", "has_charter") in kinds
    assert ("member:graphteam:scout", "tool:web", "uses_tool") in kinds
    assert ("member:graphteam:scout", "skill:research", "uses_skill") in kinds
    # Deleting the charter + tool edges removes them from the config —
    # no resurrection on the next save.
    reloaded["edges"] = [e for e in reloaded["edges"]
                         if e["id"] not in ("e-g-charter", "e-g-tool")]
    status, body = _req(base, "/api/graph", method="POST", body=reloaded)
    assert status == 200, body
    status, body = _req(base, "/api/state")
    cfg = json.loads(body)["config"]
    scout = next(m for m in cfg["teams"]["graphteam"]["members"] if m["id"] == "scout")
    assert scout["charter_file"] is None
    assert scout["toolsets"] == []
    assert scout["skills"] == ["research"]  # untouched edge stays wired
    assert scout["provider"] == "mock" and scout["model"] == "mock"


def test_settings_per_section_save_preserves_other_sections(open_server):
    base, _ = open_server
    status, body = _req(base, "/api/settings")
    assert status == 200
    before = json.loads(body)
    # Telegram-only write (full merged body, as the UI sends it).
    after_tg = json.loads(json.dumps(before))
    after_tg["telegram"]["allowlist"] = [123456]
    status, body = _req(base, "/api/settings", method="PUT", body=after_tg)
    assert status == 200, body
    status, body = _req(base, "/api/settings")
    got = json.loads(body)
    assert got["telegram"]["allowlist"] == [123456]
    assert got["budgets"] == before["budgets"]
    assert got["cron"] == before["cron"]
    # Budgets-only write leaves Telegram untouched.
    after_budgets = json.loads(json.dumps(got))
    after_budgets["budgets"] = {"run_usd": 42.0, "team_usd": 9.0}
    status, body = _req(base, "/api/settings", method="PUT", body=after_budgets)
    assert status == 200, body
    status, body = _req(base, "/api/settings")
    got = json.loads(body)
    assert got["budgets"] == {"run_usd": 42.0, "team_usd": 9.0}
    assert got["telegram"]["allowlist"] == [123456]


def test_member_prompt_injects_charter_and_blocks_traversal(tmp_path):
    from airlangga.brain import member_prompt
    from airlangga.config import MemberConfig

    files_root = tmp_path / "files"
    files_root.mkdir()
    (files_root / "superagent.md").write_text("BE THE AGENT. Work from evidence.\n")
    member = MemberConfig.model_validate(
        {"id": "scout", "role": "scout", "provider": "mock", "model": "mock",
         "charter_file": "superagent.md"})
    prompt = member_prompt(member, "Do the thing", files_root=files_root)
    assert "--- PERSONA CHARTER (superagent.md) ---" in prompt
    assert "BE THE AGENT" in prompt
    (tmp_path / "escape.md").write_text("SECRET")
    sneaky = MemberConfig.model_validate(
        {"id": "scout", "role": "scout", "provider": "mock", "model": "mock",
         "charter_file": "../escape.md"})
    prompt2 = member_prompt(sneaky, "Do the thing", files_root=files_root)
    assert "SECRET" not in prompt2
    assert "PERSONA CHARTER" not in prompt2


def test_mobile_form_grids_stack_single_column(server):
    # Regression test for the phone screenshots (390px): the Main Brain
    # form and the member modal "Model & cost" section crushed into
    # overlapping columns because `@media (max-width: 640px)` set
    # `.row > * { min-width: 0; }`, removing the 220px floor that made
    # the flex row wrap — with flex-basis 0% all 9 fields fit one row.
    base, _ = server
    status, body = _req(base, "/", token="test-token-123")
    assert status == 200
    text = body.decode("utf-8")
    # .row is now a grid that auto-fits 220px columns on desktop...
    assert ".row { display:grid; grid-template-columns:repeat(auto-fit, minmax(min(220px, 100%), 1fr))" in text
    # ...and collapses to one explicit column on phones.
    assert ".row { grid-template-columns:minmax(0, 1fr); gap:10px; }" in text
    # The old crushing rule must be gone from the 640px block (the base
    # grid rule legitimately keeps `.row > * { min-width:0; }` at 2-space
    # indent; the 4-space-indented media-query copy must not exist).
    assert "\n    .row > * { min-width:0; }\n" not in text
    # 44px touch targets on phone inputs/selects; spacer label hidden.
    assert 'input:not([type="checkbox"]):not([type="radio"]), select { min-height:44px; }' in text
    assert ".row .spacer-label { display:none; }" in text
    # The select+buttons exception uses .row-inline, the Runs bar stacks.
    assert ".row-inline { display:flex;" in text
    assert ".launchbar { flex-direction:column; align-items:stretch; gap:10px; }" in text
    assert ".launchbar #btnRun { width:100%; }" in text
    assert 'class="field team-field"' in text
    assert 'style="width:180px"' not in text


def test_add_node_picker_is_contextual_sheet_not_bare_select(server):
    # The Graph "+ Add node" control was a native <select> with 7 bare
    # types (file/folder/model/team/member/tool/skill) — on Android it
    # opens as an unexplained radio list. It is now one "+ Add" button
    # opening a contextual sheet with one-line purposes per choice.
    base, _ = server
    status, body = _req(base, "/", token="test-token-123")
    assert status == 200
    text = body.decode("utf-8")
    assert "addNodeType" not in text
    assert 'id="btnAddNode" class="ghost">+ Add</button>' in text
    assert 'id="addNodeModal"' in text
    assert "function openAddSheet(" in text
    assert "function createGraphNode(" in text
    assert "function attachFileToMember(" in text
    assert "function attachSkillToMember(" in text
    assert "function syncToolEdges(" in text
    # Canvas sheet: only the 3 building blocks, each with a purpose.
    assert '"Add to graph"' in text
    assert '"A group of agents sharing one goal and budget."' in text
    assert '"One AI agent with a specific role inside a team."' in text
    assert '"An AI provider & model that can power one or more agents."' in text
    assert 'To attach a file, folder, tool, or skill, tap any <b>Member</b> on the graph.' in text
    # Member context: file+folder merged, tool + skill attachable.
    assert '"Attach to "' in text
    assert '"File or folder"' in text
    assert '"Attach a charter (e.g. superagent.md), note, or folder from Files."' in text
    assert '"Add to team "' in text
    assert '"Add to Main Brain"' in text
    # Inspector entry points for the contextual flows.
    assert 'id="btnMemberAttach"' in text
    assert 'id="btnTeamAddMember"' in text
    assert 'id="btnMbAdd"' in text
    # Member -> folder edges are inferable in Connect mode too.
    assert '["member", "folder", "has_file"]' in text


def test_graph_member_folder_edge_persists(open_server):
    # The simplified Add flow attaches folders to members via a
    # member -> folder has_file edge; it must survive save -> reload
    # like the file charter edge does.
    base, _ = open_server
    status, body = _req(base, "/api/files", method="POST",
                        body={"path": "docs/guide.md", "content": "# Guide\n"})
    assert status == 201, body
    status, body = _req(base, "/api/graph")
    graph = json.loads(body)
    graph["nodes"].append({"id": "folder:docs", "type": "folder",
                           "label": "docs", "x": 1300, "y": 700,
                           "data": {"path": "docs"}})
    member_node = next(n for n in graph["nodes"] if n["type"] == "member")
    graph["edges"].append({"id": "e-folder-test", "from": member_node["id"],
                           "to": "folder:docs", "kind": "has_file"})
    status, _ = _req(base, "/api/graph", method="POST", body=graph)
    assert status == 200, body
    status, body = _req(base, "/api/graph")
    reloaded = json.loads(body)
    assert any(n["id"] == "folder:docs" for n in reloaded["nodes"])
    assert any(e["kind"] == "has_file" and e["to"] == "folder:docs"
               for e in reloaded["edges"])
    # No duplicate file:docs node/edge for the same attachment.
    assert not any(n["id"] == "file:docs" for n in reloaded["nodes"])
    assert not any(e["kind"] == "has_file" and e["to"] == "file:docs"
                   for e in reloaded["edges"])
    text = (open_server[1] / "airlangga.yaml").read_text(encoding="utf-8")
    assert "docs" in text


def test_graph_viewport_no_scrollbars_zoom_pan(server):
    # The graph canvas used to live in an overflow:auto box, so desktop
    # showed a horizontal + vertical scrollbar and the legend said
    # "Scroll to pan". It is now an overflow:hidden viewport: wheel
    # zooms in/out inside the box (cursor-centred), dragging empty
    # space pans, pinch zooms on touch.
    base, _ = server
    status, body = _req(base, "/", token="test-token-123")
    assert status == 200
    text = body.decode("utf-8")
    # Viewport element, overflow hidden, no browser panning.
    assert 'id="canvasViewport"' in text
    assert "#canvasViewport { flex:1; min-width:0; overflow:hidden;" in text
    assert "touch-action:none; overscroll-behavior:none;" in text
    # The old scrollable container and all scroll-offset reads are gone.
    assert 'id="canvasScroll"' not in text
    assert "scrollLeft" not in text and "scrollTop" not in text
    # Legend describes the new gestures, never the old one.
    assert "Scroll to pan" not in text
    assert "Scroll to zoom" in text
    assert "Drag empty space to pan" in text
    # Zoom state: translate+scale view transform, 25%-200% range.
    assert "function applyView()" in text
    assert "translate(${panX}px, ${panY}px) scale(${zoom})" in text
    assert "const ZOOM_MIN = 0.25, ZOOM_MAX = 2;" in text
    assert "function setZoom(z, cx, cy)" in text
    assert "function fitGraph()" in text
    assert "function viewCenterWorld()" in text
    # Wheel zoom (cursor-centred) + drag pan + pinch zoom handlers.
    assert 'addEventListener("wheel"' in text
    assert "Math.exp(-dy * 0.0012)" in text
    assert "deltaY" in text
    assert "pinchActive" in text
    assert "setPointerCapture" in text
    # Node placement + file-to-graph use view coords, not scroll offsets.
    assert "viewCenterWorld()" in text
    assert "viewPointAt(120, 120)" in text
    # Toolbar zoom buttons still drive the same zoom state.
    assert 'id="btnZoomOut"' in text and 'id="btnZoomIn"' in text
    assert 'id="btnFit"' in text


def test_run_reports_survive_restart_and_count_claims(project):
    # P0 regression: reports live in runs/blackboard.db, so a fresh UIStore
    # (simulated server restart with empty in-memory self.runs) must still
    # return full claim content, evidence_refs, diff, open_questions, and
    # accurate total claim counts across multi-claim reports.
    from airlangga.blackboard import Blackboard
    from airlangga.ledger import Ledger

    runs_dir = project / "runs"
    ledger = Ledger(runs_dir / "ledger.db")
    ledger.append("run-persist", "plan_created", "main_brain", {"goal": "Verify persistence", "contracts": ["c1"]})
    ledger.append("run-persist", "blackboard_committed", "lead", {"entry_id": 1, "member_id": "researcher"})
    ledger.close()

    board = Blackboard(runs_dir / "blackboard.db")
    eid = board.propose(
        "run-persist",
        "research-01",
        "fact",
        "Report from researcher (c1)",
        json.dumps({
            "contract_id": "c1",
            "member_id": "researcher",
            "claims": [
                {"claim": "First durable claim", "evidence_refs": ["artifact://a1"], "confidence": 0.9},
                {"claim": "Second durable claim", "evidence_refs": [], "confidence": 0.75},
            ],
            "diff": "artifact://d1",
            "open_questions": ["Is anything missing?"],
            "cost": {"tokens": 50.0, "usd": 0.001, "tool_calls": 0.0},
            "verdict_self": "pass",
        }),
        author="researcher",
    )
    board.commit(eid, by_role="lead")
    board.close()

    # Fresh UIStore simulates server restart (empty self.runs).
    restarted = UIStore(project)
    assert restarted.runs == {}
    detail = restarted.run_detail("run-persist")
    assert len(detail["reports"]) == 1
    rep = detail["reports"][0]
    assert rep["member_id"] == "researcher"
    assert rep["verdict"] == "pass"
    assert rep["diff"] == "artifact://d1"
    assert rep["open_questions"] == ["Is anything missing?"]
    assert [c["claim"] for c in rep["claims"]] == ["First durable claim", "Second durable claim"]
    assert rep["claims"][0]["evidence_refs"] == ["artifact://a1"]
    assert "First durable claim" in detail["trace_text"]

    # list_runs reports total claim count (2), not entry count (1).
    listed = next(r for r in restarted.list_runs() if r["run_id"] == "run-persist")
    assert listed["claims"] == 2


def test_run_detail_ui_renders_outputs_tab(server):
    base, _ = server
    status, body = _req(base, "/", token="test-token-123")
    assert status == 200
    text = body.decode("utf-8")
    assert 'runDetailTab = "outputs"' in text
    assert '["outputs", `Outputs (${reports.length})`]' in text
    assert 'if (runDetailTab === "outputs")' in text
    assert "c.claim" in text
    assert "c.evidence_refs" in text
    assert "r.open_questions" in text
    assert "r.diff" in text
