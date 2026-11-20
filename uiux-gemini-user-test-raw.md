# Airlangga — First-Time End-User Report

> **Verification labels used throughout:** **[verified by running it]** (real CLI command, live read-only GET, scratch server API call, or Node.js execution), **[verified by reading code]** (inspected in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html), [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py), [cli.py](file:///home/hatch/workspace/airlangga/airlangga/cli.py), etc.), **[needs a real browser]** (DOM clicks, pointer drags, visual rendering, or touch gestures not executed in a browser engine).
>
> **Scope & safety:** All calls against the live site (`http://162.35.32.92:8100`) were strictly read-only `GET` requests. All create/edit/delete/upload/ZIP/run tests ran against isolated temporary scratch servers on `127.0.0.1` ephemeral ports with a disposable test token and were deleted afterwards.

---

## 1. First impressions (first 5 minutes)

Opening `http://162.35.32.92:8100` for the first time:

- **Getting in works cleanly, but the login copy speaks to a developer, not a user.** Fetching `GET /` without credentials returns `HTTP 200` (160,616 bytes, identical to local [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html)) with a dark obsidian/gold login card titled **"Airlangga / Agentic Team Studio"** and the prompt *"Enter your UI token to log in."* **[verified by running it + reading code]**. However, the helper note underneath says: *"On a public server the token is the one set as AIRLANGGA_UI_TOKEN."* As a new user who was handed a link, I do not know what `AIRLANGGA_UI_TOKEN` means, nor does the screen explain what Airlangga does before I log in.
- **Wrong-token feedback is sensible.** Sending a bad token to `GET /api/state` returns `HTTP 401` (`{"error": "unauthorized: set the X-Airlangga-Token header"}`) **[verified by running it]**, which [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2395-L2396) translates into *"Wrong token — try again."* **[verified by reading code; visual display needs a real browser]**.
- **After login, I am dropped straight into a dense 13-node, 14-edge Graph with no orientation and no "Run" button.** On the live site (`GET /api/state`), there is already one pre-loaded team (`research-01` with `researcher`, `fact_checker`, `writer`), four model nodes, three tool nodes, and one skill node (`research.yaml`), while `files` is completely empty (`[]`) and `runs` is empty (`[]`) **[verified by running it]**. Because `graph.nodes.length > 0`, the friendly onboarding card (*"Build your first Agentic Team"*) is hidden **[verified by reading code]**.
- **Two nodes on the default landing screen sit directly on top of each other.** On the live site's `GET /api/state`, both `tool:web` and `skill:research` (`research.yaml`) have coordinates `(1340, 60)` **[verified by running it]**.
- **It is not obvious what to do first or where things live.** The top bar shows six tabs: `Graph`, `Teams`, `Models`, `Files`, `Runs`, `Settings`. I can tell I'm looking at an AI team map, but I immediately get confused about:
  1. **Where do I actually build a team?** There is a `+ Add` button on the Graph AND a `+ New team` button in `Teams`, and they create different subsets of fields.
  2. **What do these jargon labels mean?** `Auth ref`, `Team brain mode` (`lead member` vs `separate`), `Capabilities`, `Routing — required capabilities`, `Routing — prefer` (`cheapest_above_quality_floor`), `Wire format`, and `Approval` (`smart` / `approve` / `off`) appear without tooltips or plain-English explanations.
  3. **Where did the sample charter go?** [README.md](file:///home/hatch/workspace/airlangga/README.md#L153) tells me `files/personas/superagent.md` is seeded as an example, and the empty-graph card mentions `superagent.md`, yet on the live site `GET /api/files` returned `[]` and `GET /api/files?path=superagent.md` returned `HTTP 400` (`no such file: 'superagent.md'`) **[verified by running it]**. (On a fresh local scratch server, `files/superagent.md` *is* seeded — at the root, not under `personas/` **[verified by running it]**.)
  4. **How do I test-run what I see?** There is no "Run" button on the Graph tab; I have to discover the `Runs` tab (or click `Run team →` inside `Teams`).

---

## 2. Step-by-step log

### Step 1 — First 5 minutes: live Web UI (read-only `GET`s only)

1. **Unauthenticated endpoints on `http://162.35.32.92:8100`** **[verified by running it]**:
   - `GET /health` → `HTTP 200` `{"status": "ok", "token_required": true}`
   - `GET /` → `HTTP 200` (`text/html; charset=utf-8`, `Content-Length: 160616`)
   - `GET /api/state` (no token) → `HTTP 401` (`{"error": "unauthorized: set the X-Airlangga-Token header"}`)
   - `GET /api/state` (wrong token) → `HTTP 401` (`{"error": "unauthorized: set the X-Airlangga-Token header"}`)
   - *Transport note:* From this test environment (behind an outbound HTTP proxy), larger responses from `http://162.35.32.92:8100` (`GET /` and `GET /api/state`) intermittently truncated mid-stream (`curl: (18) transfer closed with N bytes remaining` / Python `IncompleteRead`). Checking the same live server on VPS localhost (`http://127.0.0.1:8100`) returned full, intact payloads on every call (`GET /` = 160,616 bytes, sha256 `a271f757db33cf18`, matching local [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html); `GET /api/state` = 11,044 bytes).
2. **Authenticated read-only inspection on live server (using the UI token)** **[verified by running it]**:
   - `GET /api/state` → `HTTP 200`:
     - `main_brain`: `anthropic/claude-opus-4-6`, `auth_ref: env:ANTHROPIC_API_KEY`, `cost_per_mtok_usd: 15.0`
     - `teams`: `research-01` (`template: research`, `team_brain_mode: lead_member`, `lead_member: researcher`, budget `$15.00`) with 3 members: `researcher` (`anthropic/claude-sonnet-4-5`, 2 fallbacks), `fact_checker` (`custom/deepseek-chat`, 1 fallback), `writer` (`ollama/llama3.1:8b`, 0 fallbacks)
     - `graph`: 13 nodes, 14 edges (`tool:web` and `skill:research` both at `(1340, 60)`)
   - `GET /api/graph` → `HTTP 200` (5,207 bytes)
   - `GET /api/files` → `HTTP 200` `{"files": []}`
   - `GET /api/files?path=superagent.md` → `HTTP 400` `{"error": "no such file: 'superagent.md'"}`
   - `GET /api/runs` → `HTTP 200` `{"runs": []}`
   - `GET /api/settings` → `HTTP 200` `{"telegram": {"allowlist": [], "bot_token_set": false}, "approval_default": "smart", "budgets": {"run_usd": 20.0, "team_usd": 15.0}, "cron": []}`
   - `GET /api/skills` → `HTTP 200` `{"skills": [{"name": "research.yaml", "path": "airlangga/skills/research.yaml"}]}`
   - `GET /api/providers` → `HTTP 200` (8 built-in presets + 6 toolsets)

### Step 2 — Build an Agentic Team from scratch (scratch server on ephemeral port)

Started a local scratch server with copied [airlangga.yaml](file:///home/hatch/workspace/airlangga/airlangga.yaml) and disposable test token **[verified by running it]**:

- **Fresh directory without `airlangga.yaml`:** Started scratch server in an empty temp dir → `GET /api/state` returned **`HTTP 500`** `{"error": "server error: [Errno 2] No such file or directory: '.../airlangga.yaml'"}` **[verified by running it, 2x]**.
- **Path A — Teams tab flow** **[verified by running it]**:
  1. `POST /api/teams` (`name: "launch-ops"`, `template: "blank"`, `seed_members: false`, `team_brain_mode: "lead_member"`, `goal: "Prepare Q4 launch readiness brief"`, `team_budget: {"usd": 10}`) → `HTTP 201`.
  2. `POST /api/teams/launch-ops/members` for `scout` (`anthropic/claude-sonnet-4-5`, `toolsets: ["web", "file_read"]`) → `HTTP 201`.
  3. `POST /api/teams/launch-ops/members` for `auditor` (`deepseek/deepseek-chat`, `endpoint: "https://api.deepseek.com/v1"`, `toolsets: ["file_read"]`) → `HTTP 201`.
  4. `POST /api/files` (`path: "personas/scout.md"`) → `HTTP 201`.
  5. `PUT /api/teams/launch-ops/members/scout` (`{"charter_file": "personas/scout.md"}`) → `HTTP 200`.
  6. `GET /api/graph` → `HTTP 200`: automatically generated `team:launch-ops`, `member:launch-ops:scout`, `member:launch-ops:auditor`, `file:personas/scout.md`, both shared model nodes, tool nodes, and all 9 expected edges (`assigns`, `has_member`, `uses_model`, `uses_tool`, `has_charter`).
- **Path B — Graph tab & naming pitfalls** **[verified by running it]**:
  1. **Team name with a space:** Created `"My Team 1"` via `POST /api/teams` → `HTTP 201`. Subsequent `PUT /api/teams/My%20Team%201`, `POST /api/teams/My%20Team%201/members`, and `DELETE /api/teams/My%20Team%201` (matching `encodeURIComponent` in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1563)) ALL failed with **`HTTP 400`** `"no team named 'My%20Team%201' in config"`!
  2. **Building purely on the canvas:** Appended draft nodes `team:draft1` (`canvas-team`), `member:draft1` (`planner`), `model:draft1` (`openai/gpt-5`) and edges `assigns`, `has_member`, `uses_model`, then `POST /api/graph` → `HTTP 200`. Reloading `GET /api/state` confirmed `canvas-team` and member `planner` (`openai/gpt-5`) were written to `airlangga.yaml`.
  3. **Got stuck trying to connect a charter file on the Graph:**
     - Using `Connect` mode in its default `Auto (by node types)` setting maps `member` + `file` to `has_file` (*"attaches file"*), NOT `has_charter` (*"charter"*) ([ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L565)) **[verified by reading code]**.
     - Switching the edge-kind dropdown manually to `charter` (`has_charter`) and clicking File first then Member creates `file -> member`. Saving via `POST /api/graph` returned `HTTP 200`, kept the `file -> member` edge visually on the graph, and **silently left `charter_file: None`** in `airlangga.yaml` **[verified by running it, 2x]**.
  4. **Got stuck editing Member properties in the Graph inspector:**
     - Clicking `auditor` in the Graph inspector shows fields for `Capabilities`, `Cost per M tokens (USD)`, and `Context limit (tokens)` — all initially **blank** because `default_graph()` omits them on member nodes **[verified by running it + reading code]**.
     - Setting them on `member:launch-ops:auditor` and calling `POST /api/graph` returned `HTTP 200`, but `GET /api/state` showed they were **silently discarded** (`caps`, `cost=0.28`, `ctx=64000` unchanged) **[verified by running it, 2x]**.
     - Meanwhile, `Budget USD`, `Attached files`, `Routing policy`, and `Fallback chain` do not exist in the Graph member inspector at all **[verified by reading code]**.

### Step 3 — Configure a model, provider, and fallback (scratch server)

- **Editing `Main Brain` on the Graph silently fails:** Updated `main_brain` node's `provider`/`model` to `openai/gpt-5` and saved via `POST /api/graph` → `HTTP 200`. Reloading `GET /api/state` showed `config.main_brain` was **still `anthropic/claude-opus-4-6`** because the `powers` edge from the old model node overwrote it **[verified by running it, 2x]**.
- **Editing `Main Brain` in the `Models` tab (`PUT /api/main-brain`) works**, but accepts dangerous/invalid values:
  - `{"model": ""}` (empty model) → **`HTTP 200`** (accepted!) **[verified by running it]**
  - `{"auth_ref": "sk-ant-RAWKEY999"}` (raw API key) → **`HTTP 200`** (accepted by backend — only a regex check in JS blocks it in the browser!) **[verified by running it]**
- **Configuring a Member model (`POST /api/teams/launch-ops/members`) with empty/wrong fields** **[verified by running it]**:
  - Empty `model: ""` and `role: ""` → **`HTTP 201`** (accepted!)
  - `provider: "custom"` with empty `endpoint: ""` → **`HTTP 201`** (accepted!)
  - Raw API key `auth_ref: "sk-proj-RAWSECRET12345"` → **`HTTP 201`** (accepted by backend!)
  - Negative `cost_per_mtok_usd: -10.0` and `budget: {"usd": -5.0}` → **`HTTP 201`** (accepted!)
  - Invalid `wire_format: "invalid_wire"` → **`HTTP 500`** (uncaught Pydantic `ValidationError` returned as a raw server error!)
- **Adding a Custom Provider (`PUT /api/settings`):** Adding `my-vllm` returned `HTTP 200` and appeared in `GET /api/providers` **[verified by running it]**. However, in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1955-L1963), `btnAddCustomProvider` calls `saveSettingsSection(...)` with **no callback and no `loadState()`**, so the new provider does not appear in the UI list or any provider dropdown until a manual page refresh **[verified by reading code; visual confirmation needs a real browser]**.
- **Setting a Fallback — major trap:**
  - The Member modal's *"Fallback chain"* section ([ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1585-L1613)) ONLY lists **other members in the same team**. I cannot configure an arbitrary fallback provider/model (like `openai/gpt-5-mini` or `ollama/qwen3:8b`) unless another member in the team already uses it **[verified by reading code]**.
  - Opening the bundled `researcher` member (which has `openai/gpt-5-mini` and `ollama/qwen3:8b` in `airlangga.yaml`) and clicking **Save member** sends `fallback: []` because neither fallback is in `#fbList`, **wiping both fallbacks** (`PUT /api/teams/research-01/members/researcher` → `HTTP 200`, fallbacks become `[]`) **[verified by running it, 2x]**.
  - The fallback status badge (`ELIGIBLE` vs `WILL SKIP — missing ...`) compares candidates against the member's own `Capabilities` (`.mfCap`) instead of `Routing — required capabilities` (`.mfReqCap`), whereas [router.py](file:///home/hatch/workspace/airlangga/airlangga/router.py#L33) checks `routing_policy.require`. On `research-01`, `fact_checker` satisfies `researcher`'s `routing_policy.require` (`True`), yet the UI formula flags it **`WILL SKIP — missing long_context`** **[verified by running it + reading code]**.

### Step 4 — Import a ZIP containing nested folders/files (scratch server only)

Built a ZIP containing `kit/charters/lead.md`, `kit/docs/sub/spec.txt`, `kit/empty-folder/`, binary `kit/logo.png`, and macOS metadata `__MACOSX/kit/._lead.md`:

1. `POST /api/files/import-zip?dest=&overwrite=0` → **`HTTP 200`**:
   `{"ok": true, "dest": "", "extracted": [{"path": "kit/charters/lead.md", "size": 30}, {"path": "kit/docs/sub/spec.txt", "size": 21}, {"path": "kit/logo.png", "size": 18}], "skipped": [], "ignored_metadata": 1, "total_bytes": 69}` **[verified by running it]**.
2. `GET /api/files` confirmed nested folders containing files survived (`kit`, `kit/charters`, `kit/docs`, `kit/docs/sub` plus all 3 files), `__MACOSX` was cleanly stripped, **but `kit/empty-folder/` was silently dropped** (`web_ui.py` skips `info.is_dir()`) **[verified by running it]**.
3. `GET /api/files?path=kit/logo.png` → `HTTP 400` `{"error": "Binary file cannot be edited as text.", "binary": true, "size": 18}`, which [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1852-L1867) handles with a dedicated "Binary file" card **[verified by running it + reading code]**.
4. Re-importing with `overwrite=0` → `HTTP 200`, `extracted: []`, `skipped: ["kit/charters/lead.md", "kit/docs/sub/spec.txt", "kit/logo.png"]`. Importing into `dest=packs/v1&overwrite=1` → `HTTP 200`, extracted under `packs/v1/kit/...` **[verified by running it]**.
5. Security tests: `../escape.txt` → `HTTP 400` (`path_traversal`); `.env` + `safe.txt` → `HTTP 400` (`credential_path`, and `safe.txt` was atomically rolled back / not written); non-ZIP bytes → `HTTP 415` (`not_a_zip`) **[verified by running it]**.
6. **What the UI tells you afterwards:** [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2041-L2044) shows *"Imported N files"* with a list of extracted paths, sizes, skipped files, and a `Done` button — plus a toast *"Imported N files from `<name>`."* However, the modal's bottom action bar (`Upload & extract` stuck disabled as `"Uploading…"` + `Cancel`) is never hidden when `#zipResult` appears **[verified by reading code; visual layout needs a real browser]**.

### Step 5 — Run the team in mock mode and find the result (scratch server)

1. **Mock run of `launch-ops`:**
   - `POST /api/runs` (`{"team": "launch-ops", "goal": "Prepare Q4 launch readiness brief", "mock": true}`) → `HTTP 202` `{"ok": true, "run_id": "run-4d8fad1e", "status": "running"}` **[verified by running it]**.
   - `GET /api/runs/run-4d8fad1e` → `HTTP 200`, `status: "done"`, `15` events, `member_states: {"scout": "DONE", "auditor": "DONE"}`. The `member_state` event confirmed `charter_file: "personas/scout.md"` was attached **[verified by running it]**.
   - **Where is the actual output?!** `GET /api/runs/run-4d8fad1e` returns keys `['run_id', 'status', 'events', 'cost_by_actor', 'contracts', 'member_states', 'dissents', 'trace_text', 'error']`. **Not a single claim, answer, or report body is returned!** Inspecting `runs/blackboard.db` directly via SQLite proved the reports *were* written there (`"Mock researcher completed its assigned work for..."`), but there is NO endpoint or UI tab to read them **[verified by running it, 2x]**.
   - **Cost looks wrong for a free mock run:** Even with `"mock": true`, `cost_by_actor` reported `scout: $0.000591` and `auditor: $0.000078` (because `_mockify` does not zero `cost_per_mtok_usd`) **[verified by running it, 2x]**.
   - **Contracts tab is broken:** `GET /api/runs/run-4d8fad1e` returns `contracts: {"contract-bd50758b": "done", "contract-7c4ed915": "done"}` (string values). Running the exact JS from [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2118) in Node.js produced `[{"0":"d","1":"o","2":"n","3":"e","id":"contract-bd50758b"}, ...]` so `c.status` is `undefined` and every completed contract renders as **`open`** with empty member and empty goal **[verified by running it]**.
2. **Failure & edge-case runs on scratch** **[verified by running it]**:
   - **Real providers without API keys (`mock: false`):** `POST /api/runs` → `HTTP 202`, final status `"failed"`, `error: "auth_ref 'env:ANTHROPIC_API_KEY': environment variable is not set"` (which `humanizeRunError` translates cleanly in JS). **After a simulated server restart** (`UIStore(scratch).list_runs()`), that failed run's status silently flipped from **`"failed"`** to **`"done"`** and its error vanished! **[verified by running it, 2x]**
   - **0-member team (`empty-team`):** `POST /api/runs` → `HTTP 202`, completes as `status: "done"` with 1 event and `contracts: {}` (no warning that nobody did any work).
   - **Capability gate (`NoCapableModel`):** Setting `auditor`'s `routing_policy.require: ["vision"]` and running in mock mode failed as expected: `status: "failed"`, `error: "member auditor: no endpoint satisfies require=['vision']; pinned=mock/deepseek-chat, fallbacks=[]"`.
   - **Settings budget cap test:** Set `Settings → Approvals & budgets` to `run_usd: 0.00001, team_usd: 0.00001` (`PUT /api/settings` → `HTTP 200`), then launched a mock run → completed `status: "done"` with `$0.000649` spend (65× over the saved limit). Settings budgets are never read by `start_run()`!
   - **Settings → Change UI password (scratch only):** Wrong current token → `HTTP 400`; `<8` chars → `HTTP 400`; valid change → `HTTP 200`, old token immediately returned `HTTP 401`, new token returned `HTTP 200`, `.ui-token` written mode `0o600`.
   - **Settings → Scheduled jobs → `Run due jobs now`:** Added a job with `interval_min: 9999` and called `POST /api/cron/tick` twice back-to-back → started two runs immediately (`HTTP 200` both times), ignoring `interval_min` and hardcoding `mock=True`.

### Step 6 — Try the CLI for the same job (scratch dir, exact commands & output)

All commands ran via `/home/hatch/workspace/airlangga/.venv/bin/python -m airlangga.cli` (note: bare `airlangga` is not on `PATH` unless `.venv/bin` is activated; `.venv/bin/airlangga --help` exited `0`) **[verified by running it]**:

1. **`--help`** (exit `0`): lists 10 commands (`demo`, `init`, `replay`, `run`, `schedule`, `serve`, `telegram`, `trace`, `ui`, `validate`).
2. **`init` + `validate`** (exit `0`):
   ```text
   $ .venv/bin/python -m airlangga.cli init
   Wrote example config to airlangga.yaml
   $ .venv/bin/python -m airlangga.cli init
   Error: airlangga.yaml already exists; refusing to overwrite   # exit 1
   $ .venv/bin/python -m airlangga.cli validate
   Config OK: 1 team(s): research-01 (3 members)
   ```
3. **`demo`** (exit `0`):
   ```text
   $ .venv/bin/python -m airlangga.cli demo
   Demo run (mock provider, no API key, no network)
   Run run-26797b25: 3 member report(s)
     researcher: verdict=pass claims=1 cost_usd=$0.0006
     fact_checker: verdict=pass claims=1 cost_usd=$0.0001
     writer: verdict=pass claims=1 cost_usd=$0.0000
   Run run-26797b25 — 22 events
   ...
   Contracts: {'contract-1b6d2dae': 'done', 'contract-de6feefa': 'done', 'contract-4956d3e7': 'done'}
   Member states: {'researcher': 'DONE', 'fact_checker': 'DONE', 'writer': 'DONE'}
   ```
   Files actually created under `runs/`: `['runs/blackboard.db', 'runs/ledger.db']` (NOT `runs/run-26797b25/ledger.db`). Again, the actual claim text produced by the members is never printed!
4. **`trace` using the path documented in [README.md](file:///home/hatch/workspace/airlangga/README.md#L218) and `trace --help` (`runs/<run>/ledger.db`)** — **got stuck here!**
   ```text
   $ .venv/bin/python -m airlangga.cli trace --ledger runs/run-26797b25/ledger.db --run-id run-26797b25
   # EXIT: 0
   Run run-26797b25 — 0 events
   Cost by actor:
   Contracts: {}
   Member states: {}
   ```
   Using the real path (`--ledger runs/ledger.db`) worked and printed all 22 events (exit `0`).
5. **`run` in mock mode** — **got stuck here!**
   ```text
   $ .venv/bin/python -m airlangga.cli run --team research-01 --goal "Test mock run" --mock
   # EXIT: 2
   Error: No such option '--mock'.
   ```
   Unlike `telegram`, `serve`, and `schedule`, `run` has NO `--mock` option. Running `run` against the freshly initialized `airlangga.yaml` without API keys crashed with a 19-line Python traceback ending in `ValueError: auth_ref 'env:ANTHROPIC_API_KEY': environment variable is not set` (exit `1`).
6. **Running a custom team in mock mode via CLI:** I had to hand-author `custom.yaml` setting `provider: mock`, `wire_format: mock`, `auth_ref: none` on every member and Main Brain, plus `files/analyst-charter.md`. `validate --config custom.yaml` exited `0` (`Config OK: 1 team(s): my-custom-team (2 members)`) and `run --config custom.yaml --team my-custom-team --goal "Review Q4 release checklist"` exited `0` (`Run run-2e5f4db5: 2 member report(s)`).
7. **`replay` on my custom team** — **crashed!**
   ```text
   $ .venv/bin/python -m airlangga.cli replay --ledger runs/ledger.db --run-id run-2e5f4db5 --config custom.yaml
   # EXIT: 1
   Replaying run-2e5f4db5: recorded contracts={'contract-2fa0b0e3': 'done', 'contract-37068c8c': 'done'}
   Recorded team: passed=True cost_usd=$0.0000
   --- team replay (mock) ---
   ...
   KeyError: "no team named 'research-01' in config"
   ```
   (`replay` on `demo`'s `research-01` run exited `0` and printed `team loses on cost: passed, but more expensive than the single-agent baseline`.)
8. **`ui --host 0.0.0.0` without token & `telegram` without token:** Both exited `1` as expected for safety, but dumped raw Python tracebacks (despite [README.md](file:///home/hatch/workspace/airlangga/README.md#L111) promising `telegram` *"fails cleanly: TELEGRAM_BOT_TOKEN is not set"* — it printed a 28-line traceback ending in `TelegramNotConfigured`).
9. **CLI vs Web UI verdict:** The **Web UI is much easier** for building teams, picking provider presets, creating/importing files, and running any team in mock mode with one dropdown. The **CLI is harder** for a first-time user because there is no team-creation command, no `--mock` flag on `run`, hand-editing YAML is error-prone, `trace` docs point to the wrong DB path, and `replay` breaks on any team not named `research-01`.

### What was NOT TESTED
- **Visual rendering, pointer dragging, port-to-port drag, pinch-zoom, mobile bottom-sheet swipe, file drag-and-drop, and clipboard copy** — `NOT TESTED because no real browser / headless Chromium or Playwright is installed in this environment (checked via `which playwright chromium google-chrome`); all frontend findings below are explicitly labelled **[verified by reading code]** or **[needs a real browser]**.
- **Real paid LLM provider calls (Anthropic, OpenAI, DeepSeek, Gemini, OpenRouter, Ollama)** — `NOT TESTED because no paid API keys or local Ollama daemon are used in this mock-mode user test`.
- **Live Telegram bot polling and webhook notifications** — `NOT TESTED because no Telegram bot token was configured`.
- **Live VPS mutations (including changing the live VPS UI password)** — `NOT TESTED on live VPS because of the strict read-only safety rule against http://162.35.32.92:8100 (tested on scratch server instead)`.

---

## 3. Bugs found

Every backend/CLI bug below was **reproduced twice** unless noted otherwise.

### 1. Team output (claims / reports) is never shown anywhere in the Web UI or CLI
- **Verification:** **[verified by running it, 2x on scratch UI + 2x on CLI]**
- **Repro:** Launch any mock run (`POST /api/runs` with `mock: true`, or `.venv/bin/python -m airlangga.cli demo`), then inspect `GET /api/runs/<run_id>` or the CLI output.
- **Evidence:** `runs/blackboard.db` contains the committed JSON reports (`"Mock researcher completed its assigned work for..."`), yet `GET /api/runs/run-523a3e22` and `run-22f75145` return only `['run_id', 'status', 'events', 'cost_by_actor', 'contracts', 'member_states', 'dissents', 'trace_text', 'error']` — zero claim text (`False` in both trials). CLI prints only `researcher: verdict=pass claims=1 cost_usd=$0.0006`.

### 2. Run Detail → "Contracts" tab misreads API strings as objects, marking every completed contract `"open"` with blank details
- **Verification:** **[verified by running it (API + Node.js execution of UI code) + reading code; DOM visual needs a real browser]**
- **Repro:** Complete a run and fetch `GET /api/runs/<run_id>`; run [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2118) (`Object.entries(d.contracts || {}).map(([id, c]) => ({ id, ...(c || {}) }))`).
- **Evidence:** `GET /api/runs/run-4d8fad1e` returns `"contracts": {"contract-bd50758b": "done", "contract-7c4ed915": "done"}` (strings, confirmed 2x). Spreading `"done"` in JS yields `{"0":"d","1":"o","2":"n","3":"e","id":"contract-bd50758b"}`. Consequently `c.status` is `undefined` (renders `"open"` instead of `"done"`), `c.member_id` is `undefined`, and `c.goal` is `""`.

### 3. Creating a team with a space in its name breaks Edit, Add Member, and Delete
- **Verification:** **[verified by running it, 2x on scratch]**
- **Repro:** Create team `"My Team 1"` via `POST /api/teams`, then call `PUT /api/teams/My%20Team%201`, `POST /api/teams/My%20Team%201/members`, or `DELETE /api/teams/My%20Team%201` (exact URLs sent by `encodeURIComponent` in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1563)).
- **Evidence:** Both trials (`My Team 1`, `My Team 2`): `POST /api/teams` → `HTTP 201`; `PUT` → `HTTP 400` `{"error": "\"no team named 'My%20Team%201' in config\""}`; add member → `HTTP 400`; `DELETE` → `HTTP 400` `{"error": "no team 'My%20Team%201'"}`. Cause: [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L1376) splits `path` without `urllib.parse.unquote`.

### 4. Editing `Main Brain` on the Graph and pressing "Save graph" silently reverts your changes
- **Verification:** **[verified by running it, 2x on scratch]**
- **Repro:** Select `Main Brain` node on the graph, change `Provider` / `Model` (e.g., to `openai` / `gpt-5`), and `POST /api/graph`. Reload `GET /api/state`.
- **Evidence:** Both trials returned `HTTP 200` on save, yet `config.main_brain` remained `anthropic/claude-opus-4-6`. In [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L695-L705), `apply_graph_to_config()` applies `main_brain` node edits first, then overwrites them with the connected `powers` model node.

### 5. Editing a Member's `Capabilities`, `Cost per M tokens`, or `Context limit` in the Graph inspector is silently discarded on Save
- **Verification:** **[verified by running it, 2x on scratch]**
- **Repro:** Edit `capabilities`, `cost_per_mtok_usd`, and `context_limit` on `member:launch-ops:auditor` and `POST /api/graph`. Reload `GET /api/state`.
- **Evidence:** Both trials returned `HTTP 200`, yet `auditor` reverted to `caps=['tool_calling', 'structured_json']`, `cost=0.28`, `ctx=64000`. Additionally, `default_graph()` in [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L335-L340) never populates those three fields on member nodes, so the inspector shows them empty even when configured.

### 6. Opening and saving an existing Member in the Member Editor wipes out any fallbacks not belonging to another team member
- **Verification:** **[verified by running it (API payload matching UI logic), 2x on scratch + reading code; click flow needs a real browser]**
- **Repro:** In `Teams` (or `Models`), open `Edit` on `research-01` → `researcher` (which has fallbacks `openai/gpt-5-mini` and `ollama/qwen3:8b` in [airlangga.yaml](file:///home/hatch/workspace/airlangga/airlangga/airlangga.yaml#L39-L50)), change nothing, and click `Save member`.
- **Evidence:** [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1585-L1664) builds `#fbList` exclusively from other members of the same team and constructs `fallback` solely from `.mfFb:checked`. Sending that payload via `PUT /api/teams/research-01/members/researcher` returned `HTTP 200` and wiped `fallback` from `[('openai', 'gpt-5-mini'), ('ollama', 'qwen3:8b')]` to `[]` in both trials.

### 7. Fallback eligibility badges (`ELIGIBLE` / `WILL SKIP`) check the wrong field and contradict the Router
- **Verification:** **[verified by running it (Router check on `airlangga.yaml`) + reading code; visual pill needs a real browser]**
- **Repro:** Inspect `research-01`'s `researcher` (`capabilities: [tool_calling, structured_json, long_context]`, `routing_policy.require: [tool_calling, structured_json]`) with candidate fallback `fact_checker` (`capabilities: [tool_calling, structured_json]`).
- **Evidence:** `ModelEndpoint.satisfies(m.routing_policy.require)` returns `True` (Router will use it), whereas [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1618) checks `.mfCap:checked` instead of `.mfReqCap:checked`, computing missing `['long_context']` and showing **`WILL SKIP — missing long_context`**.

### 8. Connecting File → Member with edge kind `charter` on the Graph silently fails to attach the charter
- **Verification:** **[verified by running it, 2x on scratch]**
- **Repro:** In Connect mode, pick `charter` (`has_charter`), click a file node (`file:superagent.md`) then a member node (`member:launch-ops:auditor`), and `POST /api/graph`.
- **Evidence:** Both trials returned `HTTP 200`, kept the `file -> member` edge in the graph, and left `auditor.charter_file` as `None`. ([ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L849) preserves click order when edge kind is non-`auto`, while [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L758) only reads edges with `from == member_id`.)

### 9. Default graph layout stacks `skill:research` directly on top of `tool:web` at `(1340, 60)`
- **Verification:** **[verified by running it on live VPS AND scratch]**
- **Repro:** Open default graph (`GET /api/state`) with bundled `airlangga.yaml`.
- **Evidence:** Live VPS `GET /api/state` returns both `tool:web` and `skill:research` (`research.yaml`) at `pos=(1340, 60)`. Similarly, [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L359-L370) places every charter file at fixed `(1340, 420)` and every attached file at `(1340, 480)`, causing multiple charters/attachments to stack identically.

### 10. Failed runs silently turn into `"done"` (green) after a server restart, losing their error message
- **Verification:** **[verified by running it, 2x on scratch]**
- **Repro:** Trigger a failing run (`POST /api/runs` with `mock: false` and no API key), confirm `status: "failed"`, then instantiate a new `UIStore(scratch)` (simulating server restart) and call `list_runs()`.
- **Evidence:** Both trials: live status was `'failed'` with `error: "auth_ref 'env:ANTHROPIC_API_KEY': environment variable is not set"`; after restart, status became `'done'` and `error` became `None`, because [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L1053) defaults any ledger run absent from in-memory `self.runs` to `"done"`.

### 11. Mock runs report fake non-zero USD costs
- **Verification:** **[verified by running it, 2x on scratch Web UI + CLI `demo`]**
- **Repro:** Run `research-01` or `launch-ops` in mock mode (Web UI `mock: true` or CLI `demo`).
- **Evidence:** CLI `demo` printed `researcher: verdict=pass claims=1 cost_usd=$0.0006` and `fact_checker: cost_usd=$0.0001`. Scratch UI mock runs `run-523a3e22` and `run-22f75145` both reported `researcher: $0.000498`, `fact_checker: $0.000078`. `_mockify()` does not zero `cost_per_mtok_usd`.

### 12. CLI `trace` docs and `--help` give the wrong ledger path, and running it silently creates an empty DB and exits `0`
- **Verification:** **[verified by running it, 2x on scratch]**
- **Repro:** Run `demo`, then follow [README.md](file:///home/hatch/workspace/airlangga/README.md#L218) / `trace --help` (`Ledger database path (runs/<run>/ledger.db)`):
  `.venv/bin/python -m airlangga.cli trace --ledger runs/<run-id>/ledger.db --run-id <run-id>`.
- **Evidence:** Both `runs/run-26797b25/ledger.db` and `runs/run-nonexistent/ledger.db` exited `0` with `Run ... — 0 events`, silently creating an empty SQLite database instead of warning that the file did not exist. Actual path is `runs/ledger.db`.

### 13. CLI `replay` crashes with `KeyError` on any config whose team is not named `research-01`
- **Verification:** **[verified by running it, 2x on scratch (`custom.yaml` & `alpha.yaml`)]**
- **Repro:** Run a team named `my-custom-team` (or `alpha`) and run `replay --ledger runs/ledger.db --run-id <id> --config <file>`.
- **Evidence:** Both trials exited `1` with `KeyError: "no team named 'research-01' in config"` because [cli.py](file:///home/hatch/workspace/airlangga/airlangga/cli.py#L160-L163) hardcodes `"research-01"`.

### 14. Starting the Web UI in a fresh directory without `airlangga.yaml` crashes `/api/state` with `HTTP 500`
- **Verification:** **[verified by running it, 2x on scratch]**
- **Repro:** Start `run_ui_server` in an empty directory (without running `airlangga init` first) and request `GET /api/state`.
- **Evidence:** Both trials returned `HTTP 500` `{"error": "server error: [Errno 2] No such file or directory: '.../airlangga.yaml'"}`. In the browser, [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2380) treats any non-401 error on boot as *"Cannot reach server — check the UI is running, then reload this page."*

### 15. Missing server-side input validation & `HTTP 500` on invalid `wire_format`
- **Verification:** **[verified by running it on scratch; 1x per case]**
- **Repro:** `POST /api/teams/launch-ops/members` with invalid payloads.
- **Evidence:** `wire_format: "invalid_wire"` returned **`HTTP 500`** (`server error: 1 validation error for MemberConfig...`) instead of `400`. Meanwhile, empty `model: ""`, empty `role: ""`, `provider: "custom"` with `endpoint: ""`, raw API keys in `auth_ref` (`sk-proj-RAWSECRET12345`), and negative `budget`/`cost_per_mtok_usd` (`-5.0`, `-10.0`) all returned **`HTTP 201`/`200`**.

### 16. UI wiring & CSS bugs in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html) (verified by reading code — needs a real browser to visually observe)
- **Custom providers don't update after Add/Remove:** `btnAddCustomProvider` ([L1955-L1963](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1955-L1963)) and `removeCustomProvider` ([L1788](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1788)) save settings with no `after` callback and no `loadState()`, so neither the list nor provider dropdowns refresh until manual reload.
- **All four `Show` password buttons in `Settings` do nothing:** `#btnToggleTgToken`, `#btnToggleCurToken`, `#btnToggleNewToken`, `#btnToggleNewToken2` ([L438-L453](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L438-L453)) have zero JS listeners (only `#btnToggleToken` on the login page is wired).
- **Changing `Provider` in the Graph inspector does not update input fields:** In [L1452-L1459](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1452-L1459), switching `#nfProvider` on a model node never updates `#nfModel`, `#nfEndpoint`, or `#nfAuth` in the DOM, and keeps stale truthy values like `auth_ref: "none"` when switching from `Mock` to `Anthropic`.
- **Undefined CSS variable `--ochre`:** Used at [L114](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L114), [L135](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L135), [L198](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L198), and [L464](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L464) (`CHARTER`/`UNASSIGNED` badges, `.warn` toast, `#approvalOffWarn`), but `--ochre` is never defined in `:root` ([L11-L21](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L11-L21)).
- **Mobile bottom sheet scroll-lock class mismatch:** CSS styles `body.sheet-open` ([L257-L258](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L257-L258)) while JS toggles `body.sheet-lock` ([L1292](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1292), [L1298](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1298)).
- **Dead counter/indicator DOM elements:** `#countTeams`, `#countFiles`, `#countRuns` ([L304-L307](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L304-L307)) and `#graphDirtyChip` (*"Unsaved changes"*, [L334](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L334)) are never populated or toggled in JS.
- **ZIP modal leaves disabled `"Uploading…"` + `Cancel` bar visible below `Done`:** [L504-L505](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L504-L505) & [L2038-L2043](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2038-L2043).
- **Model node badge `×N` ignores `powers` edges to Main Brain:** [L744](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L744) filters `e.to === n.id`, but `powers` is directed `model -> main_brain` (`e.from === n.id`).

---

## 4. Broken / misleading / missing for a real user

- **CLI `run` has no `--mock` flag, and `demo` cannot run your team:** A user following `run --help` naturally tries `run --team my-team --goal "..." --mock` and gets `Error: No such option '--mock'` **[verified by running it, 2x]**. Every other runtime command (`telegram`, `serve`, `schedule`) has `--mock/--no-mock`.
- **Settings controls that silently do nothing at runtime:**
  - `Settings → Approvals & budgets` (`Default approval mode`, `Run budget (USD)`, `Team budget (USD)`) are persisted to `.airlangga-ui.json` but **never read** by `start_run()` or `TeamRuntime` — setting `$0.00001` still allowed a `$0.000649` run to finish as `done` **[verified by running it + reading code]**.
  - `Team brain mode: separate` is offered in both Graph and Teams dropdowns, yet [team.py](file:///home/hatch/workspace/airlangga/airlangga/team.py) never inspects `team_brain_mode` **[verified by reading code]**.
  - `Skills` in Settings looks under `<project-root>/airlangga/skills` (so any non-repo project starts with 0 skills, **[verified by running it]**), and neither [team.py](file:///home/hatch/workspace/airlangga/airlangga/team.py) nor [brain.py](file:///home/hatch/workspace/airlangga/airlangga/brain.py) ever loads or injects `member.skills` into a run **[verified by reading code]**.
  - `Settings → Scheduled jobs → Run due jobs now` ignores `interval_min` (re-runs every enabled job on every click) and hardcodes `mock=True` **[verified by running it]**.
- **Cannot configure external fallback models in the UI:** A user cannot set a cheap fallback model (e.g. `openai/gpt-5-mini` or `ollama/qwen3:8b`) on a member unless they create a dummy member in the same team using that model first **[verified by reading code]**.
- **Connecting a File to a Member in Graph `Connect` mode defaults to `attaches file`, not `charter`:** A new user trying to attach a charter on the graph gets a dashed `attaches file` edge (which only appends a filename list to the prompt) instead of a `charter` edge (which actually loads the persona text into the prompt) **[verified by reading code]**.
- **Two conflicting places to edit members with different capabilities:** The Graph inspector exposes `Capabilities`, `Cost per M tokens`, and `Context limit` (none of which save!) and hides `Budget USD`, `Fallbacks`, and `Routing policy`; meanwhile `Teams → Edit` has the real form, and `Main Brain` appears in both `Graph` (broken on save) and `Models` (works).
- **Empty folders inside a ZIP archive are silently skipped:** `kit/empty-folder/` disappeared on import without any note in the import result **[verified by running it]**.
- **Running a 0-member team reports green `done`:** Launching `empty-team` returned `status: "done"` with 0 contracts and no warning **[verified by running it]**.
- **Documentation drift vs reality:** [README.md](file:///home/hatch/workspace/airlangga/README.md#L153) cites `files/personas/superagent.md` (code seeds `files/superagent.md`, and live VPS currently has `files: []`); [README.md](file:///home/hatch/workspace/airlangga/README.md#L218) cites `runs/<run>/ledger.db` (code writes `runs/ledger.db`); [README.md](file:///home/hatch/workspace/airlangga/README.md#L111) claims `telegram` without a token fails cleanly without a traceback (actually dumps a 28-line traceback); [README.md](file:///home/hatch/workspace/airlangga/README.md#L193) shows bare `airlangga` commands without reminding users to activate `.venv`.

---

## 5. What works well

- **Login & token security model:** `GET /` serves `HTTP 200` with a clean login form rather than a raw `401` JSON wall; `GET /api/*` fails closed with `HTTP 401` without the token; `POST /api/settings/ui-token` rotates the UI password immediately (old token returns `401` on the very next call, `.ui-token` saved mode `0o600`, no restart required); binding `0.0.0.0` without `AIRLANGGA_UI_TOKEN` is refused **[verified by running it]**.
- **ZIP import safety and nested-file extraction:** Non-empty nested folder hierarchies (`kit/charters/lead.md`, `kit/docs/sub/spec.txt`) extract intact both to root and to a `dest` subfolder; `__MACOSX` junk is automatically ignored; `overwrite=0` safely skips existing files and reports `"skipped": [...]`; `../` path traversal (`400`), `.env` credential paths (`400`, with verified atomic rollback so `safe.txt` is not written), and non-ZIP files (`415`) are all cleanly blocked; binary files like PNGs are safely detected (`"binary": true`) instead of corrupting the text editor **[verified by running it]**.
- **Live config ↔ graph synchronization (when using the Teams & Files tabs):** Creating `launch-ops`, adding `scout` (`anthropic`) and `auditor` (`deepseek`), writing `personas/scout.md`, and attaching it as charter immediately produced the full 9-edge graph (`assigns`, `has_member`, `uses_model`, `uses_tool`, `has_charter`), and building a team + member + model directly on the canvas (`canvas-team` / `planner` / `openai/gpt-5`) persisted cleanly back to `airlangga.yaml` **[verified by running it]**.
- **Charter injection into runs:** Attaching `personas/scout.md` to `scout` was visibly recorded in the run ledger (`{"state": "WORKING", "charter_file": "personas/scout.md"}`) **[verified by running it]**.
- **Capability-gated routing catches mismatches loudly:** Requiring `vision` on `auditor` failed cleanly with `NoCapableModel` instead of silently downgrading, and `humanizeRunError()` in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2085) turns it into plain English: *"No model in this team can handle the task — check each member's capabilities and fallback chain."* **[verified by running it + reading code]**.
- **Fast, zero-dependency offline CLI demo:** `.venv/bin/python -m airlangga.cli init`, `validate`, and `demo` run end-to-end in under a second with zero API keys or network, and `init` refuses to overwrite an existing `airlangga.yaml` **[verified by running it]**.

---

## 6. Prioritised fix list

### P0 — Blocks a user from doing the job
1. **Surface actual team outputs (reports/claims from `blackboard.db`) in `GET /api/runs/<id>`, the Web UI Run Detail, and CLI `demo`/`run`/`trace`** — Without seeing what the agents produced, a user cannot tell whether the team actually answered their goal (Evidence: `GET /api/runs/run-523a3e22` & `run-22f75145` omit all claim text stored in `blackboard.db`; CLI prints only `claims=1`).
2. **Fix the Run Detail "Contracts" tab string-spread bug (`[ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L2118)`)** — Every completed contract currently renders as `"open"` with blank member and goal, making users think their run stalled (Evidence: `GET /api/runs/<id>` returns `{"contract-...": "done"}`; Node.js execution confirmed `c.status === undefined`).
3. **URL-decode team and member names in [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py) (`unquote`) or slugify/validate on creation** — Any user who names a team with a space (e.g. `"My Team 1"`) creates a zombie team they can never edit, populate, or delete from the UI (Evidence: 2x `HTTP 400 "no team named 'My%20Team%201'"`).
4. **Stop the Member Editor from wiping non-member fallbacks and let users add any provider/model as a fallback** — Editing `researcher` in the UI silently deletes `openai/gpt-5-mini` and `ollama/qwen3:8b`, and users cannot configure fallbacks without creating fake team members (Evidence: 2x `PUT` wiped `fallback` to `[]`; [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1585-L1664)).
5. **Fix `Main Brain` and `Member` edits on the Graph being silently discarded on "Save graph"** — Users editing models, capabilities, cost, or context limit on the Graph get a green *"Graph saved"* toast while their edits are thrown away (Evidence: 2x `Main Brain` reverted to `anthropic/claude-opus-4-6`; 2x `auditor` caps/cost/ctx reverted).
6. **Add `--mock` to CLI `airlangga run` and read the recorded team name in `airlangga replay`** — Users cannot test their own team in mock mode from the CLI without rewriting YAML, and `replay` crashes on any team not named `research-01` (Evidence: 2x `Error: No such option '--mock'`; 2x `KeyError: "no team named 'research-01' in config"`).
7. **Auto-initialize or handle missing `airlangga.yaml` gracefully on `airlangga ui` startup** — Launching the UI in a fresh folder breaks `/api/state` with `HTTP 500` and misleads the user into thinking the server is down (Evidence: 2x `HTTP 500 FileNotFoundError` in empty scratch dir).

### P1 — Confusing or misleading
1. **Persist run failure status & error message in `ledger.db` (e.g., `run_failed` event)** — Otherwise failed runs turn green (`"done"`) after a server restart and users trust broken runs (Evidence: 2x failed no-key run became `'done'` in fresh `UIStore`).
2. **Fix `refreshFallbackPills()` in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1618) to check `.mfReqCap` (`routing_policy.require`) instead of `.mfCap`** — Currently mislabels eligible fallbacks as `WILL SKIP — missing long_context`, contradicting [router.py](file:///home/hatch/workspace/airlangga/airlangga/router.py#L33) (Evidence: `researcher` vs `fact_checker` check).
3. **Zero `cost_per_mtok_usd` in `_mockify()` (or clearly label mock cost as "Estimated")** — Charging `$0.0006` on a "free offline mock demo" confuses users into thinking real money was spent (Evidence: 2x scratch UI runs + CLI `demo`).
4. **Fix [README.md](file:///home/hatch/workspace/airlangga/README.md#L218) / `trace --help` path (`runs/ledger.db`, not `runs/<run>/ledger.db`) and fail with an error if `--ledger` doesn't exist** — Following the docs currently exits `0` with `0 events` and silently creates an empty SQLite file (Evidence: 2x `trace` runs).
5. **Fix `default_graph()` layout collisions (`[web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L349-L370)`)** — Give `tool`, `skill`, `charter`, and `attached_files` non-overlapping Y offsets or columns so `research.yaml` no longer covers `tool:web` at `(1340, 60)` on first open (Evidence: live VPS `GET /api/state`).
6. **Wire or remove non-functional Settings controls (`Approvals & budgets`, `separate` Team Brain mode, `Skills` injection, `Cron` interval check)** — Users who set a `$0.00001` budget cap in Settings or click `Run due jobs now` expect enforcement, not a silent no-op (Evidence: scratch budget test spent `$0.000649`; cron tick ignored `interval_min: 9999`; grep showed `skills` and `team_brain_mode` unused in [team.py](file:///home/hatch/workspace/airlangga/airlangga/team.py)).
7. **Accept either direction for `has_charter` edges in `apply_graph_to_config()` (or normalize direction in `ui.html`) and clarify `charter` vs `attaches file` in Connect mode** — Users wiring a charter from File → Member get a visual edge that never updates `charter_file` (Evidence: 2x reversed-edge scratch test).
8. **Refresh UI state after adding/removing a Custom Provider and update Graph inspector inputs when changing `Provider`** — Currently both actions leave stale values on screen until reload or save broken `auth_ref: "none"` (Evidence: [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1452-L1459), [L1788](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1788), [L1955-L1963](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1955-L1963)).
9. **Validate `model`, `endpoint`, `auth_ref`, and non-negative budgets/costs on the server, returning `HTTP 400` instead of `500`/`201`** — Prevents empty models, raw API keys saved to YAML, negative budgets, and 500 tracebacks (Evidence: scratch bad-input API suite).
10. **Warn or block launching a run on a 0-member team, and fix CLI error handling to raise `click.ClickException` instead of dumping Python tracebacks** — Prevents green empty runs and matches README's "fails cleanly" claim (Evidence: `empty-team` run; `telegram`/`run`/`ui` tracebacks).

### P2 — Polish
1. **Define `--ochre` in `:root` ([ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L11-L21))** — Restores intended styling on `CHARTER`/`UNASSIGNED` badges, `.warn` toasts, and the `Approval Off` warning.
2. **Wire up the four Settings `Show`/`Hide` password buttons (`#btnToggleTgToken`, `#btnToggleCurToken`, `#btnToggleNewToken`, `#btnToggleNewToken2`)** — Currently dead buttons that frustrate users checking typed tokens (Evidence: [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L438-L453) grep).
3. **Populate `#countTeams`, `#countFiles`, `#countRuns` and toggle `#graphDirtyChip`, and hide the disabled `"Uploading…"` / `Cancel` bar when `#zipResult` is shown** — Cleans up dead UI placeholders and duplicate modal buttons (Evidence: [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L304-L334), [L505](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L505)).
4. **Fix mobile bottom-sheet class mismatch (`sheet-lock` vs `sheet-open`) and model badge `×N` count for `powers` edges** — Fixes mobile background scroll lock and makes the Main Brain's model show `×1` (Evidence: [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L257), [L744](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L744), [L1298](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1298)).
5. **Preserve empty folders on ZIP import (or note skipped empty dirs in the summary) and align README's `files/personas/superagent.md` vs seeded `files/superagent.md`** — Eliminates small "where did my folder/file go?" surprises (Evidence: scratch ZIP test + seeded file list).
6. **Add plain-English login copy, a "Run" shortcut on the Graph toolbar, and short field hints for `Auth ref`, `Capabilities`, and `Routing — prefer`** — Lowers the first-5-minute learning curve for non-developer users (Evidence: [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L530), [L1596-L1610](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1596-L1610)).
