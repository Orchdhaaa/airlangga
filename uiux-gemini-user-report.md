# Airlangga — Gemini End-User Test Report

**Date:** 2026-11-21 (WIB)
**Tester:** Gemini 4 Neon XHigh (`gemini-4-neon-xhigh`), acting as a first-time end user
**Runs:** (1) functional end-user test — `uiux-gemini-user-test-raw.md` (52,961 bytes);
(2) dedicated UI/UX design critique — `uiux-gemini-critique-raw.md` (43,656 bytes)
**Live site:** http://162.35.32.92:8100 (read-only `GET`s only: `/`, `/health`, `/api/state`,
`/api/graph`, `/api/files`, `/api/runs`)
**Scratch:** all create/edit/delete/upload/ZIP/run tests ran against isolated temporary
servers on `127.0.0.1` ephemeral ports with a disposable test token, deleted afterwards.
**CLI:** run in a scratch directory via `.venv/bin/python -m airlangga.cli`.
**Auth note:** this test was blocked on 2026-11-20 by expired Antigravity credentials; it ran
on 2026-11-21 after re-authentication. No product code was edited in this round.

**Verification labels:** **[verified by running it]** = real CLI command, live read-only GET,
scratch-server API call, or Node.js execution. **[verified by reading code]** = inspected in
`airlangga/ui.html`, `airlangga/web_ui.py`, `airlangga/cli.py`, etc.
**[needs a real browser]** = DOM clicks, pointer drags, visual rendering, or touch gestures
that were NOT executed in a browser engine — no headless Chromium/Playwright exists in this
environment, so every visual claim is code-derived and marked as such.

---

## Verdict (one paragraph)

The core idea works and the honest parts are genuinely good — login security, ZIP-import
safety, and the Teams/Files → graph sync all behave correctly when you use the intended
tabs. But a first-time user cannot yet do the actual job end-to-end without hitting traps:
**team outputs are never shown anywhere** (the whole point of running a team), the Run
Detail Contracts tab renders every finished contract as "open", saving a member silently
wipes its fallbacks, Graph edits are silently discarded, and a team named with a space
becomes a zombie you can never edit or delete. On design, the verdict is harsher: the UI
does **not** clear the premium-playful agency-grade bar — it reads as a generic dark
dev-tool scaffold wearing a warm obsidian/gold stylesheet, with a desktop CSS bug that
leaks the entire Settings page underneath every tab, broken gold discipline on the Graph,
and a 390px phone experience where graph labels shrink to ~3px. Fix the P0s first, then do
the Graph + visual-hierarchy pass in the critique's top-5 list.

---

## 1. First impressions (first 5 minutes)

- **Getting in works cleanly, but the login copy speaks to a developer, not a user.**
  `GET /` without credentials returns `HTTP 200` (160,616 bytes, identical to local
  `ui.html`) with a dark obsidian/gold login card titled "Airlangga / Agentic Team Studio"
  and the prompt *"Enter your UI token to log in."* **[verified by running it + reading code]**.
  The helper note underneath references the `AIRLANGGA_UI_TOKEN` environment variable — a
  new user handed a link does not know what that means, and nothing on the screen explains
  what Airlangga does before login.
- **Wrong-token feedback is sensible.** A bad token to `GET /api/state` returns `HTTP 401`,
  which `ui.html` translates into *"Wrong token — try again."*
  **[verified by running it; visual display needs a real browser]**.
- **After login, you are dropped straight into a dense 13-node, 14-edge Graph with no
  orientation and no "Run" button.** The live site already has one pre-loaded team
  (`research-01`: `researcher`, `fact_checker`, `writer`), four model nodes, three tool
  nodes, and one skill node (`research.yaml`), while `files` and `runs` are empty (`[]`)
  **[verified by running it]**. Because `graph.nodes.length > 0`, the friendly onboarding
  card (*"Build your first Agentic Team"*) is hidden **[verified by reading code]**.
- **Two nodes on the default landing screen sit directly on top of each other.**
  `tool:web` and `skill:research` (`research.yaml`) both have coordinates `(1340, 60)`
  **[verified by running it]**.
- **It is not obvious what to do first or where things live.** Six tabs: `Graph`, `Teams`,
  `Models`, `Files`, `Runs`, `Settings`. Immediate confusions:
  1. **Where do I actually build a team?** There is a `+ Add` button on the Graph AND a
     `+ New team` button in `Teams`, and they create different subsets of fields.
  2. **What do these jargon labels mean?** `Auth ref`, `Team brain mode` (`lead member` vs
     `separate`), `Capabilities`, `Routing — required capabilities`, `Routing — prefer`
     (`cheapest_above_quality_floor`), `Wire format`, and `Approval` (`smart` / `approve` /
     `off`) appear without tooltips or plain-English explanations.
  3. **Where did the sample charter go?** `README.md` says `files/personas/superagent.md` is
     seeded and the empty-graph card mentions `superagent.md`, yet on the live site
     `GET /api/files` returned `[]` and `GET /api/files?path=superagent.md` returned
     `HTTP 400` (`no such file`). On a fresh local scratch server, `files/superagent.md`
     *is* seeded — at the root, not under `personas/` **[verified by running it]**.
  4. **How do I test-run what I see?** There is no "Run" button on the Graph tab; you have
     to discover the `Runs` tab (or click `Run team →` inside `Teams`).
- **Transport note:** from this test environment (behind an outbound HTTP proxy), larger
  responses from the live site intermittently truncated mid-stream. The same server checked
  on VPS localhost returned full, intact payloads every time (`GET /` = 160,616 bytes,
  sha256 `a271f757db33cf18`, matching local `ui.html`).

## 2. Step-by-step log (condensed)

### Step 1 — Live Web UI (read-only GETs)
- `GET /health` → `200 {"status": "ok", "token_required": true}`; `GET /` → `200` HTML;
  `GET /api/state` without/wrong token → `401` **[verified by running it]**.
- Authenticated inspection: `main_brain` `anthropic/claude-opus-4-6` (`auth_ref:
  env:ANTHROPIC_API_KEY`, cost $15.00/MTok); team `research-01` (`template: research`,
  `team_brain_mode: lead_member`, budget $15.00) with `researcher`
  (`anthropic/claude-sonnet-4-5`, 2 fallbacks), `fact_checker` (`custom/deepseek-chat`,
  1 fallback), `writer` (`ollama/llama3.1:8b`, 0 fallbacks); graph 13 nodes / 14 edges;
  `GET /api/settings` shows Telegram allowlist empty, bot token not set, budgets
  run $20.00 / team $15.00, no cron jobs **[verified by running it]**.

### Step 2 — Build an Agentic Team from scratch (scratch server)
- **Fresh directory without `airlangga.yaml`:** `GET /api/state` → **`HTTP 500`**
  `{"error": "server error: [Errno 2] No such file or directory: '.../airlangga.yaml'"}`
  **[verified by running it, 2x]** (see Bug 14).
- **Path A — Teams tab flow works:** `POST /api/teams` (`launch-ops`, blank, lead_member,
  goal "Prepare Q4 launch readiness brief", $10 budget) → `201`; add `scout`
  (`anthropic/claude-sonnet-4-5`, tools web + file_read) → `201`; add `auditor`
  (`deepseek/deepseek-chat`, custom endpoint) → `201`; `POST /api/files`
  (`personas/scout.md`) → `201`; attach charter via `PUT` member → `200`;
  `GET /api/graph` auto-generated all 9 expected edges (`assigns`, `has_member`,
  `uses_model`, `uses_tool`, `has_charter`) **[verified by running it]**.
- **Path B — Graph tab pitfalls (all reproduced 2x):**
  - Team name with a space (`"My Team 1"`): create → `201`, but `PUT`, add-member, and
    `DELETE` on the URL-encoded name all → **`400`** `"no team named 'My%20Team%201' in
    config"` (see Bug 3).
  - Building purely on the canvas (draft team/member/model + edges) persisted cleanly back
    to `airlangga.yaml` via `POST /api/graph` → `200`.
  - Connecting a charter File → Member with edge kind `charter` saved `HTTP 200`, kept the
    edge visually, and **silently left `charter_file: None`** (see Bug 8).
  - Editing a Member's `Capabilities` / `Cost per M tokens` / `Context limit` in the Graph
    inspector saved `HTTP 200` but was **silently discarded** on reload; those fields are
    also blank initially because `default_graph()` never populates them (see Bug 5).
    `Budget USD`, `Attached files`, `Routing policy`, and `Fallback chain` do not exist in
    the Graph member inspector at all.

### Step 3 — Configure a model, provider, and fallback (scratch server)
- **Editing `Main Brain` on the Graph silently fails:** changed provider/model to
  `openai/gpt-5`, saved `200`, reload showed `config.main_brain` still
  `anthropic/claude-opus-4-6` — the `powers` edge overwrote the edit (see Bug 4).
- **Editing `Main Brain` in the Models tab (`PUT /api/main-brain`) works but accepts
  dangerous values:** empty model `""` → `200`; a raw API key in `auth_ref` → `200`
  (only a JS regex blocks it in the browser — the backend does not) **[verified by running it]**.
- **Member creation accepts invalid input:** empty `model`/`role`, `provider: "custom"`
  with empty `endpoint`, raw API key in `auth_ref`, negative cost (`-10.0`) and negative
  budget (`-5.0`) all → `201`; invalid `wire_format` → **`HTTP 500`** (uncaught Pydantic
  `ValidationError`) (see Bug 15).
- **Custom provider (`PUT /api/settings`):** `my-vllm` added → `200`, appears in
  `GET /api/providers`, but the UI list/dropdowns do not refresh until a manual page
  reload (`btnAddCustomProvider` has no callback/`loadState()`)
  **[verified by running it + reading code; visual confirmation needs a real browser]**.
- **Fallback trap (major):** the Member modal's *Fallback chain* only lists **other members
  in the same team** — you cannot configure an arbitrary fallback model unless another
  member already uses it. Opening bundled `researcher` (fallbacks `openai/gpt-5-mini` and
  `ollama/qwen3:8b` in `airlangga.yaml`) and clicking **Save member** sends `fallback: []`
  and **wipes both fallbacks** (see Bug 6). The eligibility badge (`ELIGIBLE` vs
  `WILL SKIP`) compares against the member's own `Capabilities` instead of
  `Routing — required capabilities`, so it flags `fact_checker` as
  `WILL SKIP — missing long_context` even though the router would use it (see Bug 7).

### Step 4 — Import a ZIP with nested folders/files (scratch server)
- ZIP with `kit/charters/lead.md`, `kit/docs/sub/spec.txt`, `kit/empty-folder/`, binary
  `kit/logo.png`, macOS `__MACOSX/kit/._lead.md` → `200`, extracted 3 files, ignored 1
  metadata entry. Nested folders survived; `__MACOSX` stripped; **`kit/empty-folder/`
  silently dropped** (no note in the result).
- `GET /api/files?path=kit/logo.png` → `400` (`Binary file cannot be edited as text`,
  `"binary": true`) — handled by a dedicated "Binary file" card in the UI
  **[verified by running it + reading code]**.
- Re-import `overwrite=0` → `200`, extracted `[]`, skipped all 3; `dest=packs/v1&overwrite=1`
  → extracted under `packs/v1/kit/...` **[verified by running it]**.
- Security: `../escape.txt` → `400` (`path_traversal`); `.env` + `safe.txt` → `400`
  (`credential_path`, atomic rollback — `safe.txt` not written); non-ZIP bytes → `415`
  (`not_a_zip`) **[verified by running it]**.
- UI aftermath: modal shows *"Imported N files"* + list + `Done` button, but the bottom
  action bar (`Upload & extract` stuck disabled as `"Uploading…"` + `Cancel`) is never
  hidden when the result appears **[verified by reading code; visual layout needs a real browser]**.

### Step 5 — Run the team in mock mode and find the result (scratch server)
- Mock run of `launch-ops`: `POST /api/runs` (`mock: true`) → `202`
  (`run-4d8fad1e`, `running`); then `status: "done"`, 15 events, both members `DONE`,
  charter attachment recorded in the ledger **[verified by running it]**.
- **Where is the actual output?!** `GET /api/runs/<id>` returns only `run_id`, `status`,
  `events`, `cost_by_actor`, `contracts`, `member_states`, `dissents`, `trace_text`,
  `error` — **not a single claim, answer, or report body**. Inspecting `runs/blackboard.db`
  directly via SQLite proved the reports *were* written there, but there is NO endpoint or
  UI tab to read them (see Bug 1) **[verified by running it, 2x]**.
- **Mock runs report fake non-zero USD costs:** mock run showed `scout: $0.000591`,
  `auditor: $0.000078` (`_mockify` does not zero `cost_per_mtok_usd`) (see Bug 11).
- **Contracts tab is broken:** API returns `contracts: {"contract-...": "done"}` (strings);
  the UI spreads the string in JS, so `c.status` is `undefined` and every completed
  contract renders as **`open`** with empty member and goal (see Bug 2).
- **Failure & edge cases:**
  - Real providers without API keys (`mock: false`): run → `failed` with a clean humanized
    error — **but after a simulated server restart the failed run silently flipped to
    `"done"` and its error vanished** (see Bug 10) **[verified by running it, 2x]**.
  - 0-member team: run → `done` with 1 event, 0 contracts, no warning.
  - Capability gate works: `require: ["vision"]` failed cleanly with `NoCapableModel`.
  - Settings budget cap ignored: set run/team budget to $0.00001, mock run completed
    `done` with $0.000649 spend (65× over the saved limit) — Settings budgets are never
    read by `start_run()`.
  - Change UI password (scratch only): wrong current token → `400`; <8 chars → `400`;
    valid change → `200`, old token immediately `401`, new token `200`, token file written
    mode `0600`.
  - Scheduled jobs `Run due jobs now`: added a job with `interval_min: 9999`, called
    `POST /api/cron/tick` twice → started two runs immediately, ignoring `interval_min`
    and hardcoding `mock=True`.

### Step 6 — Try the CLI for the same job (scratch dir)
All commands via `.venv/bin/python -m airlangga.cli` (bare `airlangga` is not on `PATH`
unless `.venv/bin` is activated).
- `--help` (exit `0`): 10 commands (`demo`, `init`, `replay`, `run`, `schedule`, `serve`,
  `telegram`, `trace`, `ui`, `validate`).
- `init` + `validate` (exit `0`): `init` writes example config, refuses to overwrite;
  `validate` → `Config OK: 1 team(s): research-01 (3 members)`.
- `demo` (exit `0`): mock run, 3 member reports, 22 events, under a second, zero API keys.
  But again the actual claim text is never printed — only `verdict=pass claims=1
  cost_usd=$0.0006`. Files created under `runs/`: `blackboard.db`, `ledger.db` (NOT
  `runs/<run>/ledger.db`).
- **`trace` using the documented path (`runs/<run>/ledger.db`) — got stuck:** exit `0`,
  `Run … — 0 events`, silently creating an empty SQLite DB. Real path is `runs/ledger.db`
  (see Bug 12).
- **`run` in mock mode — got stuck:** `run --team research-01 --goal "…" --mock` → exit `2`,
  `Error: No such option '--mock'`. Every other runtime command has `--mock`. Running `run`
  without keys crashed with a 19-line Python traceback ending in `ValueError: auth_ref
  'env:ANTHROPIC_API_KEY': environment variable is not set` (exit `1`).
- **Custom team in mock mode via CLI:** required hand-authoring `custom.yaml` setting
  `provider: mock`, `wire_format: mock`, `auth_ref: none` on every member and Main Brain.
  Then `validate` and `run` exited `0`.
- **`replay` on the custom team — crashed:** exit `1`, `KeyError: "no team named
  'research-01' in config"` (`cli.py` hardcodes `"research-01"`) (see Bug 13).
- **`ui --host 0.0.0.0` without token & `telegram` without token:** both exited `1` as
  expected, but dumped raw Python tracebacks despite `README.md` promising `telegram`
  *"fails cleanly"* (28-line traceback ending in `TelegramNotConfigured`).
- **CLI vs Web UI verdict:** the Web UI is much easier for building teams, picking provider
  presets, creating/importing files, and running any team in mock mode with one dropdown.
  The CLI is harder for a first-time user: no team-creation command, no `--mock` on `run`,
  hand-editing YAML is error-prone, `trace` docs point to the wrong DB path, and `replay`
  breaks on any team not named `research-01`.

### What was NOT TESTED
- Visual rendering, pointer dragging, port-to-port drag, pinch-zoom, mobile bottom-sheet
  swipe, file drag-and-drop, clipboard copy — no real browser / headless Chromium or
  Playwright installed in this environment; all frontend findings are labelled
  **[verified by reading code]** or **[needs a real browser]**.
- Real paid LLM provider calls (Anthropic, OpenAI, DeepSeek, Gemini, OpenRouter, Ollama) —
  no paid API keys or local Ollama daemon used in this mock-mode test.
- Live Telegram bot polling and webhook notifications — no Telegram bot token configured.
- Live VPS mutations (including changing the live VPS UI password) — not tested on the live
  VPS per the strict read-only rule; tested on scratch server instead.

---

## 3. Bugs found

Every backend/CLI bug below was **reproduced twice** unless noted otherwise.

### P0 — Blocks a user from doing the job
1. **Team output (claims/reports) is never shown anywhere in the Web UI or CLI.**
   `GET /api/runs/<id>` omits all claim text stored in `blackboard.db`; CLI prints only
   `claims=1`. Without seeing what the agents produced, a user cannot tell whether the
   team answered their goal.
2. **Run Detail → "Contracts" tab misreads API strings as objects.** API returns
   `{"contract-…": "done"}`; UI code `Object.entries(d.contracts || {}).map(([id, c]) =>
   ({ id, ...(c || {}) }))` spreads the string `"done"` into `{"0":"d",…}`, so `c.status`
   is `undefined` and every completed contract renders as `"open"` with blank member/goal.
   (Node.js execution of the exact UI code confirmed.)
3. **Creating a team with a space in its name breaks Edit, Add Member, and Delete.**
   `"My Team 1"` → create `201`, then `PUT` / add-member / `DELETE` on the URL-encoded
   name all → `400 "no team named 'My%20Team%201' in config"`. Cause: `web_ui.py` splits
   the path without `urllib.parse.unquote`.
4. **Editing `Main Brain` on the Graph and pressing "Save graph" silently reverts changes.**
   Save → `200`, reload shows `config.main_brain` still `anthropic/claude-opus-4-6`:
   `apply_graph_to_config()` applies main_brain node edits first, then overwrites them
   with the connected `powers` model node.
5. **Editing a Member's `Capabilities`, `Cost per M tokens`, or `Context limit` in the Graph
   inspector is silently discarded on Save.** Save → `200`, values revert; `default_graph()`
   never populates those fields on member nodes, so the inspector shows them empty even
   when configured.
6. **Opening and saving an existing Member wipes out any fallbacks not belonging to another
   team member.** The Member Editor builds the fallback list exclusively from other members
   of the same team; saving `researcher` wiped its `openai/gpt-5-mini` + `ollama/qwen3:8b`
   fallbacks to `[]`. Users also cannot configure an arbitrary fallback model without
   creating a dummy member first.
7. **Fallback eligibility badges (`ELIGIBLE` / `WILL SKIP`) check the wrong field.**
   The UI compares against the member's own `Capabilities` instead of `Routing — required
   capabilities` (`router.py` checks `routing_policy.require`). `fact_checker` satisfies
   `researcher`'s requirement yet shows `WILL SKIP — missing long_context`.
8. **Connecting File → Member with edge kind `charter` on the Graph silently fails.**
   Save → `200`, edge stays visible, `charter_file` stays `None`. (`ui.html` preserves
   click order for non-`auto` edge kinds; `web_ui.py` only reads edges with
   `from == member_id`.)
9. **Default graph layout stacks `skill:research` directly on top of `tool:web` at
   `(1340, 60)`.** Confirmed on live VPS and scratch. `default_graph()` also places every
   charter file at fixed `(1340, 420)` and every attached file at `(1340, 480)`.
10. **Failed runs silently turn into `"done"` (green) after a server restart.** A failed
    no-key run became `'done'` with error `None` in a fresh `UIStore`, because `web_ui.py`
    defaults any ledger run absent from in-memory `self.runs` to `"done"`.
11. **Mock runs report fake non-zero USD costs.** CLI `demo` printed `$0.0006`/`$0.0001`;
    scratch UI mock runs reported `$0.000498`/`$0.000078`. `_mockify()` does not zero
    `cost_per_mtok_usd`.
12. **CLI `trace` docs and `--help` give the wrong ledger path, and running it silently
    creates an empty DB and exits `0`.** Documented `runs/<run>/ledger.db`; actual path is
    `runs/ledger.db`. A nonexistent path exits `0` with `0 events`.
13. **CLI `replay` crashes with `KeyError` on any config whose team is not named
    `research-01`.** `cli.py` hardcodes `"research-01"`.
14. **Starting the Web UI in a fresh directory without `airlangga.yaml` crashes
    `/api/state` with `HTTP 500`** (`FileNotFoundError`). The browser then shows
    *"Cannot reach server — check the UI is running, then reload this page."*
15. **Missing server-side input validation & `HTTP 500` on invalid `wire_format`.**
    `wire_format: "invalid_wire"` → `500` instead of `400`; empty model/role, custom
    provider with empty endpoint, raw API keys in `auth_ref`, negative budget/cost all
    accepted with `200`/`201`.
16. **UI wiring & CSS bugs in `ui.html` (verified by reading code — needs a real browser to
    visually observe):**
    - Custom providers don't update after Add/Remove (no callback/`loadState()`).
    - All four `Show` password buttons in Settings do nothing (zero JS listeners; only the
      login page toggle is wired).
    - Changing `Provider` in the Graph inspector does not update Model/Endpoint/Auth inputs
      and keeps stale values like `auth_ref: "none"` when switching from Mock to Anthropic.
    - Undefined CSS variable `--ochre` (used in 4 places, never defined in `:root`).
    - Mobile bottom-sheet scroll-lock class mismatch: CSS styles `body.sheet-open`, JS
      toggles `body.sheet-lock`.
    - Dead counter/indicator DOM: `#countTeams`, `#countFiles`, `#countRuns`,
      `#graphDirtyChip` ("Unsaved changes") never populated/toggled.
    - ZIP modal leaves disabled `"Uploading…"` + `Cancel` bar visible below `Done`.
    - Model node badge `×N` ignores `powers` edges to Main Brain (filters `e.to === n.id`,
      but `powers` is directed `model -> main_brain`).

### P1 — Confusing or misleading
- **Settings controls that silently do nothing at runtime:** `Approvals & budgets` are
  persisted but never read by `start_run()`/`TeamRuntime` ($0.00001 cap allowed a $0.000649
  run to finish `done`); `Team brain mode: separate` is offered in dropdowns yet `team.py`
  never inspects `team_brain_mode`; `Skills` looks under `<project-root>/airlangga/skills`
  and neither `team.py` nor `brain.py` ever loads/injects `member.skills` into a run;
  `Scheduled jobs → Run due jobs now` ignores `interval_min` and hardcodes `mock=True`.
- **Cannot configure external fallback models in the UI** (see Bug 6).
- **Connecting a File to a Member in Graph `Connect` mode defaults to `attaches file`, not
  `charter`:** a new user attaching a charter gets a dashed `attaches file` edge (appends a
  filename list to the prompt) instead of a `charter` edge (loads the persona text).
- **Two conflicting places to edit members with different capabilities:** the Graph
  inspector exposes Capabilities/Cost/Context (none of which save!) and hides Budget/
  Fallbacks/Routing; `Teams → Edit` has the real form; `Main Brain` appears in both Graph
  (broken on save) and Models (works).
- **Empty folders inside a ZIP are silently skipped** (no note in the import result).
- **Running a 0-member team reports green `done`** with 0 contracts and no warning.
- **Documentation drift vs reality:** `README.md` cites `files/personas/superagent.md`
  (code seeds `files/superagent.md`, live VPS currently has `files: []`); cites
  `runs/<run>/ledger.db` (code writes `runs/ledger.db`); claims `telegram` without a token
  "fails cleanly" (actually dumps a 28-line traceback); shows bare `airlangga` commands
  without reminding users to activate `.venv`.

---

## 4. What works well

- **Login & token security model:** `GET /` serves `200` with a clean login form rather
  than a raw `401` JSON wall; `GET /api/*` fails closed with `401` without the token;
  `POST /api/settings/ui-token` rotates the UI password immediately (old token `401` on
  the next call, token file saved mode `0600`, no restart required); binding `0.0.0.0`
  without a token is refused **[verified by running it]**.
- **ZIP import safety and nested-file extraction:** nested hierarchies extract intact to
  root and to a `dest` subfolder; `__MACOSX` junk ignored; `overwrite=0` safely skips and
  reports `"skipped": [...]`; `../` traversal (`400`), `.env` credential paths (`400`,
  atomic rollback), and non-ZIP files (`415`) all cleanly blocked; binary PNGs detected
  (`"binary": true`) instead of corrupting the text editor **[verified by running it]**.
- **Live config ↔ graph sync (when using the Teams & Files tabs):** creating `launch-ops`,
  adding `scout` + `auditor`, writing `personas/scout.md`, and attaching it as charter
  immediately produced the full 9-edge graph; building a team + member + model directly on
  the canvas persisted cleanly back to `airlangga.yaml` **[verified by running it]**.
- **Charter injection into runs:** attaching `personas/scout.md` was visibly recorded in
  the run ledger (`{"state": "WORKING", "charter_file": "personas/scout.md"}`).
- **Capability-gated routing catches mismatches loudly:** requiring `vision` failed cleanly
  with `NoCapableModel` instead of silently downgrading, and `humanizeRunError()` turns it
  into plain English: *"No model in this team can handle the task — check each member's
  capabilities and fallback chain."* **[verified by running it + reading code]**.
- **Fast, zero-dependency offline CLI demo:** `init`, `validate`, and `demo` run end-to-end
  in under a second with zero API keys or network, and `init` refuses to overwrite an
  existing `airlangga.yaml` **[verified by running it]**.

---

## 5. UI/UX critique (dedicated design review)

*Source: dedicated critique run against `uiux-gemini-design.md` ("Candi Obsidian & Lontar
Studio"), `airlangga/ui.html` (160,616 bytes, SHA-256 identical to live), and live
read-only `GET /health`, `/api/state`, `/api/graph`. No real browser was available; all
judgments are derived from CSS/HTML/JS source, WCAG contrast math, and live graph
coordinate geometry. Anything needing live pixels is marked **[needs a real browser]**.*

### 5.1 Premium feel vs. the design direction — and the gold-discipline audit

**It reads as a generic dark dev-tool scaffold wearing a warm brown-black & gold
stylesheet — nowhere close to the premium-playful agency-grade bar**
(`tehtariknation.com`, `sweet-tape.com`, `bikebear.com.my`).

- **The "Candi & Lontar" brand concept dies after line 296.** The entire cultural/studio
  identity is a single 20×20 geometric diamond SVG (`brand-mark`) and one 20px serif
  `<h1>Airlangga</h1>`. Inside `<main>`, `--font-display` is never used again — every card
  title, section heading, node, modal, and empty state falls back to default OS
  sans-serif. No Lontar/ivory contrast moments, no playful craft, no bespoke icons (even
  the 5 utility SVGs specified in the design doc were dropped in favor of raw text `×`,
  `−`, `+`), and virtually zero motion choreography (one `@keyframes pulse` on a 6px dot).
- **Part of the problem starts in the spec itself:** the design doc prescribed utilitarian
  restraint ("zero blur", "zero shadows on static panels", uniform 4px radius, pure system
  fonts, strict tabular CRUD), which pulls toward *austere enterprise console*, not playful
  SE-Asian agency craft. Then `ui.html` cut corners *below* even that austere spec.

**Gold discipline — the rule is one primary `#D4AF37` gold action per screen:**

| Screen | Solid gold buttons at rest | Verdict |
|---|---|---|
| Login | 1 (`Enter Studio`) | **Holds** |
| Graph | **2 at rest → 3 when a Team/Member is selected** — the Select/Connect mode segment uses solid gold fill identically to a primary CTA; `#btnSaveGraph` stays gold **even when clean**; `#btnMemberAttach`/`#btnTeamAddMember` add a third gold button in the inspector. Plus gold badge spam: hardcoded gold `#panelType` pill, spurious gold `×1` model badges, `LEAD` gold badge, double gold frame on Main Brain, gold `assigns`/`powers` edges, gold connect banner | **Severely broken** |
| Teams | 1 at rest, **2–3 when editing** (`#btnNewTeam` stays gold above `#btnCreateTeam` / inline `#btnEtSave`); duplicate `LEAD researcher` + `LEAD` gold pills on the same card | **Breaks** on create/inline edit |
| Models | 1 (`Save Main Brain`) | **Holds** |
| Files | 0 when no file open; 1 once opened — but stays gold **even when clean** | **Half-broken** |
| Runs | 1 (`Run team`) | **Holds** |
| Settings | **0 at rest, still 0 when dirty** — editing Telegram or Budgets shows an "unsaved" pill, but JS never promotes the save buttons to gold | **Broken** (under-uses gold; dirty state has no CTA) |

### 5.2 Palette, typography & spacing

- **Warm obsidian base works; token hygiene is broken.** The `#0D0C0A` / `#161411` /
  `#1F1C17` warm stone ladder genuinely avoids cold Tailwind slate — the strongest visual
  choice here. But `--ochre` is **completely undefined** in `:root` while referenced in 4
  places (ochre pills, node badges, warn toasts, approval warning) — all silently lose
  their color. `--btn-sec`, `--danger-border`, `--nav-bg` are declared and never used,
  while `#242019`, `#6E2D28`, `#12100D` are hardcoded elsewhere.
- **Measured contrast failures (WCAG 2.1):** `--border-ctrl` `#524B3E` on `--surface`
  `#161411` is **2.13:1** — fails SC 1.4.11 (≥ 3:1 non-text UI contrast) despite the design
  doc claiming ≥ 3:1. `--subtle` `#8C8375` on `--surface-3` `#29251E` is **4.08:1** (fails
  AA 4.5:1). Canvas dot grid (`1.32:1`) and card dividers (`1.37:1`) are borderline
  invisible on non-OLED monitors **[needs a real browser]**.
- **Inverted & flat typographic hierarchy:** `body` is `14px`, but `input, select, textarea`
  is `15px` and `h2` is `16px` — input text is larger than body copy and within 1px of
  section headings, collapsing page scanning hierarchy **[needs a real browser]**.
  `--font-display` is trapped on `h1` alone, giving zero editorial authority to workspace
  tabs.
- **Unconstrained full-bleed spacing on wide screens:** `<main>` has **no `max-width`**.
  On a 1440–1920px desktop, forms and tables stretch across the entire screen into thin
  horizontal strips with cavernous whitespace between table columns
  **[needs a real browser]**.
- **Ad-hoc inline spacing:** 40+ inline `style="…"` margin/padding overrides fight `.card`
  padding and label margins.

### 5.3 Navigation & information architecture

- **Catastrophic desktop CSS leak — Settings renders below every tab at ≥1024px.**
  `.tab { display:none; } .tab.active { display:block; }` (specificity 0,1,0 / 0,2,0) vs
  `@media (min-width: 1024px) { #tab-settings { display:grid; … } }` (specificity 1,0,0 —
  **no `.active`!**). Because the ID selector overrides `.tab { display: none; }`, all 5
  Settings cards (Telegram, Change UI Password, Approvals & Budgets, Scheduled Jobs,
  Skills) are **permanently rendered below Graph, Teams, Models, Files, and Runs on every
  desktop viewport**. **[verified by reading code; visual confirmation needs a real browser]**
- **Where a first-time user looks first — and why it fails:** after login, the user lands
  on Graph facing a clipped 1496px-wide wiring diagram, two competing gold buttons, an
  empty 300px right inspector (*"Select a node to edit it."*), and a dev-telemetry badge
  (`TOKEN ACTIVE`) in the top right. Nothing guides the first-time mental model
  (*Configure Models → Build Team → Attach Charter → Run*). Even the `#graphEmptyCard`
  onboarding card is dead: the guard checks `graph().nodes.length`, which is always
  truthy because `main_brain` exists.
- **Confusing 3-way ownership split & redundancies:**
  - Member editing exists in **3 places with 3 different UIs**: Graph inspector
    (comma-separated text for Capabilities, hides Fallbacks/Skills) vs Teams/Models modal
    (checkboxes for Capabilities, text for Skills, broken member-checkbox list for
    Fallbacks).
  - Main Brain splits across Graph and Models: `Max tokens per call` and `Budget` only
    exist on Models, not in the Graph inspector.
  - **Inverted Models hierarchy:** `Custom providers` (actionable user config) is buried at
    the bottom of Models *underneath* a collapsed `Provider reference` table.
  - **Split authoring:** charter Markdown files live in `Files`, while Skill YAML playbooks
    live buried in card #5 of `Settings` — yet the Graph inspector wrongly claims
    `"Skill file (under files/)"`.
  - Duplicate Sign Out (header + Settings → Change UI password); empty nav counters
    (`#countTeams`, `#countFiles`, `#countRuns` never populated by JS).

### 5.4 The N8N-like graph canvas

**Verdict: looks and behaves like an internal debug view, not a designed studio canvas.**

- **Verified live coordinate collisions & wire spaghetti (from live `GET /api/graph`):**
  - **100% node collision:** `tool:web` and `skill:research` at the exact same pixel
    coordinates — `skill:research` completely buries `tool:web`.
  - **7 of 14 edges slice straight through unrelated node cards:** `e-powers-main` runs
    backwards from `model:claude-opus-4-6` to `main_brain`, cutting through
    `team:research-01` and `member:researcher`; its `powers` label pill directly collides
    with the `member` label pill. All 6 `uses_tool`/`uses_skill` edges fly across the
    entire `model` column; two share the exact midpoint `(1122, 93)`, colliding both
    curves and label pills.
- **Node design (8 types) feels flat and buggy:** zero type icons on any node — every type
  is just 3 lines of text inside a left-bordered box. `tool` and `skill` keep 6px radius
  and full padding rather than compact 3px chips. `.node .badge` is absolutely positioned
  with no padding on the text to prevent overlap **[needs a real browser]**.
  `main_brain` checks `S.config.main_brain.sovereign` — a key that **does not exist** in
  live `/api/state` — so `SOVEREIGN` never renders. Model nodes only count `e.to === n.id`
  (missing `powers` on Opus) and stamp a gold `×1` badge on single-use models instead of
  ≥ 2. `.badge.ochre` is broken (undefined `--ochre`).
- **9 edge kinds & fake port-dragging:** `uses_tool` and `uses_skill` are **visually
  identical**; `assigns` and `powers` are **visually identical**. Edge label box width uses
  hardcoded `label.length * 6 + 10` without monospace font, risking cropped/lopsided
  pills **[needs a real browser]**. **Fake port-drag:** `.port.out` shows
  `cursor: crosshair`, but `startPortDrag()` draws **no live Bezier drag wire** — it just
  toggles Connect mode and toasts *"Connect mode: click the target node."*
  Auto-infer maps `member → file` to `has_file`, never `has_charter`.
- **Inspector, legend & zoom/pan affordances:** `#panelType` is permanently gold regardless
  of node type. Selecting an edge renders **two Close buttons**. `Main Brain` gets a
  `"Delete node"` danger button. `#graphLegend` omits `Folder`, `Skill`, and all edge kinds,
  and shows desktop mouse hints even on phones. **Desktop initial clipping & dead black
  void on pan:** live graph spans `x=[60, 1496]` (1436px), yet `fitGraph()` only fires
  below 768px width — on a 1280px desktop (~936px canvas viewport), **560px of the graph
  is clipped off the right edge** with `overflow: hidden`, no pan cursor, no minimap.
  Because the dot grid lives on the finite translated `#canvas` instead of
  `#canvasViewport`, panning past `(0,0)` exposes flat blank void
  **[needs a real browser]**.

### 5.5 Forms critique

**Main Brain form (Models tab):** unstructured 9-field grid soup in one undifferentiated
`.row` — at 1280px a ragged 5+4 grid with a missing right slot; at 1024px, 4+4+1 with
`Budget (USD)` stranded alone on row 3. Capabilities is a raw comma-separated text field
here, yet the member modal directly below uses checkboxes for the same field. Labels say
`Endpoint / base_url` and `Auth ref` with no inline helper explaining `env:VAR_NAME`
until an error occurs; `wire_format` is hidden.

**Edit-member modal:** the `×` close button has **no JS event listener** — clicking it does
nothing. No sticky header or footer: one scrolling wall of ~18 controls; scrolling down
loses who you're editing and hides `Save member` / `Cancel` at the bottom. The modal card
has `box-shadow: none` on desktop. In `MODEL & COST`, `Approval` (raw lowercase enums
`smart` / `approve` / `off`) is misplaced instead of Policy/Identity; label phrasing
drifts across sibling forms (`Budget USD` vs `Budget (USD)` vs `Cost per M tokens (USD)`).
In `WIRING`, `Routing — prefer` is a raw text input pre-filled with
`"cheapest_above_quality_floor"` — not a dropdown.

**Fallback chain & `ELIGIBLE` / `WILL SKIP` pills — visually misleading & functionally wrong:**
1. **Hides real fallbacks:** `#fbList` only lists other members in the same team. For live
   `researcher`, its actual configured fallbacks are completely invisible in the modal
   (and clicking Save silently overwrites them). No ordering UI despite copy saying
   *"tries the checked fallbacks in order"*.
2. **Lies about `WILL SKIP`:** eligibility compares against the member's own capabilities
   instead of `Routing — required capabilities`, and nothing listens to the required-cap
   checkboxes. On live `researcher`, both `fact_checker` and `writer` falsely scream
   `WILL SKIP — missing long_context`.
3. **Pill crush / overflow:** `.conn-row` lacks `flex-wrap: wrap` while `.pill` has
   `white-space: nowrap` — long `WILL SKIP — missing …` pills squeeze the member label or
   blow out modal width on narrow screens **[needs a real browser]**.

### 5.6 Mobile ~390px critique

- **Graph is microscopically unreadable (25% zoom floor):** live graph bounds 1436×456px
  inside a 366px-wide viewport → `fitGraph()` clamps zoom to **0.25**. A 204×66px node
  shrinks to **51×16.5px** (2.7× smaller than a 44px tap target) and 13px labels shrink
  to **3.2px** — unreadable specks **[needs a real browser]**. Breakpoint thresholds
  conflict: sheet CSS `<= 820px`, phone CSS `<= 640px`, `fitGraph()` `< 768px`.
- **Bottom-sheet inspector has 4 concrete bugs:** (1) class mismatch kills scroll-lock &
  toast dodge (CSS `body.sheet-open` vs JS `body.sheet-lock`) — page scroll bleeds
  through; (2) **tapping an edge NEVER opens the sheet** (edge click handler never calls
  `openSheet()`), so edges cannot be edited or deleted on mobile; (3) grabber drag is
  broken & sticky-tall — `.sheet-grabber` is only 22px tall, has no live drag tracking,
  and `closePanel()` never removes `.sheet-tall`, so once expanded the sheet is stuck at
  92dvh forever; (4) no `visualViewport` keyboard lift — focusing lower inputs can be
  covered by the virtual keyboard **[needs a real browser]**.
- **Tap targets < 44px at ≤ 640px:** icon-only `×` buttons (~28–32px), `details summary`
  (~28px tall across Provider ref, Custom providers, Cron, Skills, Timeline `raw`,
  Dissents), `.sheet-grabber` (22px), password toggle buttons (34px min-height), and
  25%-scaled graph nodes (16.5px tall).
- **Crushed / overflowing layouts at 390px:** Run Detail Timeline, Run Detail Cost
  Breakdown, and Settings Scheduled Jobs tables forgot `.stacked` (no `data-label`
  attributes) — cramped multi-column horizontal scroll; even stacked tables have no card
  background/padding separation and no wrapping for long Goals or URLs
  **[needs a real browser]**. Graph toolbar never shortens `"Save graph *"` and Connect
  mode exposes a 130px-min edge-kind dropdown inside the toolbar (94px two-row wrap);
  the floating zoom pill is 4 separate bordered 44px buttons (~196px wide — over half the
  366px canvas) with no pill frame or shadow. `<nav>` clips `Runs`/`Settings` off the
  right edge with no gradient fade and no active-tab `scrollIntoView`. On Files, opening a
  file never collapses the file-tree drawer, pushing the editor below the fold. Login
  screen lacks `overflow-y: auto` — an open mobile keyboard can clip the card and the
  `Enter Studio` button **[needs a real browser]**.
- **Contextual Add sheet — one of the better mobile patterns:** bottom-docked, 56px-tall
  semantic-rail option cards, contextual to the selected node. But: close button lacks
  44px min-size; toggling a tool wipes and rebuilds the entire modal DOM (losing
  scroll/focus) and renders `"Attached"` in muted grey instead of jade; and reaching
  member-only attachments requires tapping a 16.5px-tall node on the 25%-zoomed canvas.

### 5.7 AI-slop / generated-scaffold tells

1. **Five completely dead buttons (zero JS listeners):** member-modal `×` close + all four
   Settings password `Show` buttons.
2. **Dead placeholder counters & phantom DOM IDs:** `#countTeams`, `#countFiles`,
   `#countRuns`; `#graphDirtyChip`; `#fileDirtyStar`; unreachable `#graphEmptyCard`;
   dead CSS selectors `.gold-word`, `tbody tr.selected-row`, `.is-invalid`.
3. **Mismatched & broken half-migrations:** undefined `var(--ochre)`; unused
   `--btn-sec`, `--danger-border`, `--nav-bg`; `body.sheet-open` in CSS vs
   `body.sheet-lock` in JS; `#tab-settings` specificity leak; **`#zipProgress` writes text
   (`"Uploading foo.zip…"`) into a `height: 2px; width: 0;` bar**; literal no-op ternary
   left in a template string: `class="clickable ${r.status === "done" ? "" : ""}"`.
4. **Unstyled browser-default controls & sloppy elevation:** unstyled native checkboxes
   (browser-default blue ticks on warm obsidian — not even `accent-color: var(--gold)`),
   default OS `<select>` arrows, unstyled `<details><summary>` triangles, inline
   `<details><summary>raw</summary>` inside table cells, raw `JSON.stringify(x).slice(0,
   120)` in Dissents summaries, 8 native `window.confirm()` dialogs. Desktop modal card
   has **no `box-shadow`**, while `#btnSaveGraph.dirty` slaps on a gold ring that looks
   like a stuck focus outline.
5. **Copy that speaks to backend engineers, not studio operators:** `"Endpoint / base_url"`,
   `"+ Add custom base_url provider"`, octal Unix permissions in UI copy (`"stored locally,
   0600, never shown back"`), internal schema/filenames everywhere (`"rewires the
   has_charter edge"`, `"written back to airlangga.yaml"`, `AIRLANGGA_UI_TOKEN` on Login,
   raw `"cheapest_above_quality_floor"`, raw `tool_calling`, `structured_json`,
   `openai_chat`, `anthropic_messages`, `"auth: checking…"`, `"Node gone."`, factually
   wrong `"Skill file (under files/)"`).

### 5.8 Top 5 highest-impact design fixes

1. **Fix the desktop Settings leak, undefined tokens, contrast floor, and page measure:**
   `#tab-settings` → `#tab-settings.active`; add `--ochre`/`--pewter` to `:root`, raise
   `--border-ctrl` to ≥ 3.2:1, wire the unused tokens, set `accent-color: var(--gold)` on
   `:root`; add `main > .tab:not(#tab-graph) { max-width: 1180px; margin: 0 auto; }`;
   change `sheet-lock` to `sheet-open` to match CSS.
2. **Enforce strict "One Gold CTA Per Screen" & deliver the "Candi Obsidian & Lontar Studio"
   editorial voice:** replace solid-gold mode segment with surface + gold underline; make
   `#btnSaveGraph`/`#btnSaveFile`/`#btnSaveTelegram`/`#btnSaveBudgets` gold **only when
   dirty** (remove the stuck dirty ring); demote `#btnMemberAttach`/`#btnTeamAddMember` to
   secondary; tint `#panelType` per node type; restrict model badges to count ≥ 2 in
   jade/neutral. Restore typographic drama: `font-family: var(--font-display)` on `h2`
   (22px, hero 26px), inputs/selects 15px → 14px, warm ivory accents + small geometric
   SVGs on node types and primary toolbar buttons, strip developer jargon from all
   visible labels.
3. **Fix Graph layout collisions, real port-dragging, and mobile zoom/sheet usability:**
   place Main Brain's model node directly beneath `main_brain` so `powers` never slices
   across team/member; put `skill` nodes on a distinct Y row below `tool` nodes; arrange
   tool/skill chips in a dedicated lane so zero edges cross model cards. Move the dot grid
   onto `#canvasViewport`, add `grab`/`grabbing` cursors, run `fitGraph()` on desktop
   initial load too (clamped 0.65–1.0), and on ≤ 640px clamp initial zoom to ≥ 0.55
   centered on `main_brain` + first team. Open the sheet on edge tap on mobile; remove the
   duplicate edge Close button and `"Delete node"` from `main_brain`; add badge padding;
   draw a real dashed drag wire in `startPortDrag()`.
4. **Rebuild `#memberModal` and `#mainBrainForm` into structured, accurate, human-readable
   forms:** wire the dead `×` and all 4 Settings `Show` buttons; make the modal a flex
   column (`max-height: 86vh`, real shadow) with sticky header/footer; split
   `#mainBrainForm` into two 2-column groups (`Model & Connection` + `Capabilities &
   Limits`) using the same human-labeled Capability checkboxes as the member modal;
   rewrite the fallback list to show/reorder/add/remove the member's **actual** `m.fallback`
   model configs, evaluate eligibility against required capabilities (with listeners),
   replace the routing-prefer text input with a `<select>` (human labels), move `Approval`
   (with human descriptions) out of `MODEL & COST`, add `flex-wrap: wrap` to `.conn-row`.
5. **Eliminate scaffold defects & finish the 390px mobile pass:** populate the nav counters,
   wire `#graphDirtyChip`, fix the `#graphEmptyCard` guard (check team count, not node
   count), fix `#zipProgress` so text isn't written inside a 2px bar, remove the dead
   ternary. Add `.stacked` + `data-label` to Run Detail Timeline, Cost Breakdown, and
   Settings Cron tables (with card framing); enforce 44px min tap targets on all `×`
   buttons and `details summary` at ≤ 640px; reset `.sheet-tall` in `closePanel()`;
   auto-collapse the file-tree drawer on open at ≤ 820px; frame the zoom pill; add a
   right-edge gradient overflow hint on `<nav>`.

### 5.9 Design verdict

**No.** Today, the Airlangga web UI does not clear the premium-playful agency-grade
bar — not even close. Beneath a promising warm obsidian/gold color palette, it ships
with a desktop CSS specificity bug that leaks the entire Settings page beneath every tab,
an undefined `--ochre` token, five completely dead buttons, an inverted heading-vs-input
type scale, broken gold discipline on Graph, a live canvas where nodes stack pixel-for-pixel
on top of each other and half the edges cut through model cards, a Fallback modal that
hides real fallbacks and lies about `WILL SKIP`, and a 390px phone experience where the
graph shrinks to 3.2px text and edges cannot open the bottom sheet. **The single change
that would move it most** is a disciplined visual-and-structural pass on the **Graph
canvas + visual hierarchy** — fixing the `#tab-settings` desktop leak and node/edge
auto-layout collisions while bringing real `--font-display` editorial typography,
iconography, tactile Lontar contrast accents, and strict single-gold-CTA discipline across
the workspace — because right now the very first screen an operator sees after login
immediately signals "unfinished internal debug tool" instead of a crafted studio.

---

## 6. Prioritised fix list (merged)

### P0 — Blocks a user from doing the job
1. Surface actual team outputs (reports/claims from `blackboard.db`) in
   `GET /api/runs/<id>`, the Web UI Run Detail, and CLI `demo`/`run`/`trace`.
2. Fix the Run Detail "Contracts" tab string-spread bug (`ui.html` L2118).
3. URL-decode team and member names in `web_ui.py` (`unquote`) or slugify/validate on
   creation.
4. Stop the Member Editor from wiping non-member fallbacks and let users add any
   provider/model as a fallback.
5. Fix `Main Brain` and `Member` edits on the Graph being silently discarded on "Save graph".
6. Add `--mock` to CLI `airlangga run` and read the recorded team name in `replay`.
7. Auto-initialize or handle missing `airlangga.yaml` gracefully on `airlangga ui` startup.
8. **Fix the desktop Settings leak** (`#tab-settings` → `#tab-settings.active`) — the
   entire Settings page currently renders below every tab at ≥1024px.

### P1 — Confusing or misleading
1. Persist run failure status & error message in `ledger.db` (e.g. `run_failed` event).
2. Fix `refreshFallbackPills()` to check required capabilities instead of the member's own.
3. Zero `cost_per_mtok_usd` in `_mockify()` (or clearly label mock cost as "Estimated").
4. Fix `README.md` / `trace --help` path (`runs/ledger.db`, not `runs/<run>/ledger.db`)
   and fail with an error if `--ledger` doesn't exist.
5. Fix `default_graph()` layout collisions — non-overlapping Y offsets/columns for `tool`,
   `skill`, charter, and attached files.
6. Wire or remove non-functional Settings controls (Approvals & budgets, `separate` Team
   Brain mode, Skills injection, Cron interval check).
7. Accept either direction for `has_charter` edges in `apply_graph_to_config()` (or
   normalize direction in `ui.html`) and clarify `charter` vs `attaches file` in Connect mode.
8. Refresh UI state after adding/removing a Custom Provider and update Graph inspector
   inputs when changing `Provider`.
9. Validate `model`, `endpoint`, `auth_ref`, and non-negative budgets/costs on the server,
   returning `HTTP 400` instead of `500`/`201`.
10. Warn or block launching a run on a 0-member team, and fix CLI error handling to raise
    `click.ClickException` instead of dumping Python tracebacks.
11. Enforce one-gold-CTA-per-screen (dirty-only gold on Save buttons; demote inspector
    attach buttons; fix the gold mode segment).
12. Fix the Graph's desktop initial clipping (run `fitGraph()` on desktop too), dot-grid
    void on pan, and fake port-drag (draw a real drag wire).

### P2 — Polish
1. Define `--ochre` in `:root`; fix contrast floor (`--border-ctrl` ≥ 3:1, `--subtle` ≥ 4.5:1).
2. Wire up the four Settings `Show`/`Hide` password buttons and the member-modal `×`.
3. Populate `#countTeams`, `#countFiles`, `#countRuns`, toggle `#graphDirtyChip`, hide the
   disabled `"Uploading…"` / `Cancel` bar when the ZIP result is shown; fix the
   `#graphEmptyCard` guard (check team count, not node count).
4. Fix mobile bottom-sheet class mismatch (`sheet-lock` vs `sheet-open`), model badge `×N`
   count for `powers` edges, edge-tap-to-open-sheet, sticky-tall sheet reset, 44px tap
   targets, and the three unstacked tables.
5. Preserve empty folders on ZIP import (or note skipped empty dirs in the summary) and
   align README's `files/personas/superagent.md` vs seeded `files/superagent.md`.
6. Add plain-English login copy, a "Run" shortcut on the Graph toolbar, and short field
   hints for `Auth ref`, `Capabilities`, and `Routing — prefer`.
7. Restore editorial typography (`--font-display` on `h2`, inputs 15px → 14px), add a
   `max-width` to non-graph tabs, replace developer jargon in visible copy, and add real
   node-type icons.
