# Airlangga

**Airlangga is a persistent, accountable Agentic Team runtime, built from scratch.**

A user gives one goal to a Main Brain. The Main Brain decomposes it into
signed task contracts and delegates them to named, persistent team members —
each running a different AI model of the user's choosing, official API or
custom endpoint — and the team returns structured, verifiable results under
a hard budget, a durable run ledger, and human approval for anything risky.

The name honours **Airlangga, the 11th-century Javanese king who reunified
a fragmented East Java and founded the kingdom of Kahuripan** — the
product's job is the same in miniature: hold a fragmented, multi-model,
multi-member effort together under one accountable rule, with every
decision recorded and every member's track record surviving the run.

See [SPEC.md](SPEC.md) for the full design. All project content is in
English; prices in USD; times in UTC; numbers in en-US format.

## What makes an Agentic Team different

An Agentic Team is **not** a swarm, **not** one-shot subagents, and **not**
a plain orchestrator/router. Its five mechanics:

1. **Contracts, not conversations** — work crosses layers only as a signed
   task contract (goal, artifact refs, output schema, acceptance check,
   budget, deadline, idempotency key) and returns only as a structured report.
2. **Persistent identity** — team and member records (charter, role, model
   policy, track record) persist across runs; each activation rebuilds a
   fresh, budgeted context from that record. Persistent *state*, not
   persistent processes.
3. **A blackboard with commit rules** — typed, versioned shared memory
   (`fact | decision | open_question | artifact | risk`). Members propose;
   only the Team Brain (or lead member in v1) commits.
4. **Budget as a delegated resource** — caps on tokens, USD, wall-clock,
   and tool calls, enforced by a runtime governor outside any LLM.
5. **Explicit dissent and merge** — bounded debate (propose → critique →
   revise → decide, max 2 rounds), verifier-first, dissent always recorded.

## Install

Requires Python 3.12+.

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Dependencies are generic public libraries only: `httpx`, `pydantic`,
`PyYAML`, `click` (+ `pytest` for development). No agent-framework
dependencies. License: Apache-2.0 (see `LICENSE`).

## Quickstart — demo with no API key

The demo runs the whole team pipeline end to end with a deterministic
offline mock provider. No paid API key, no network.

```bash
.venv/bin/python -m airlangga.cli demo
```

Expected output: a run with 3 member reports (researcher, fact_checker,
writer), a trace of ledger events, and cost per actor.

## Useful features in v1

The small core also ships the useful features a team actually needs,
each rebuilt from scratch in our own code:

- **Telegram gateway** (`airlangga/gateway_telegram.py`) — connect a bot
  (token from `TELEGRAM_BOT_TOKEN`, never in the repo), send it
  `/goal <your goal>`, get the run result back. Only user IDs on the
  allowlist are admitted; approvals (plan / spend / risky tools) wait for
  an explicit YES from an allowed user.
- **Browser access** (`airlangga/tools_browser.py`, `airlangga/tools.py`)
  — members with the `web` toolset can `fetch_url` a public page and
  `search_web` via a pluggable hook. Fetches are SSRF-guarded (private /
  loopback / link-local / metadata addresses blocked); on a host behind
  an egress proxy the proxy is the fetch boundary for domain names.
- **File + terminal tools** — scoped to the run workspace, writes to
  credential paths denied, commands run as argv lists (no shell) and are
  checked against the hardline denylist; all gated by the Policy Engine.
- **Scheduler** (`airlangga/scheduler.py`) — tick loop with a file lock;
  team-targeted jobs run on the same code path as interactive runs.
- **Long-term memory** (`airlangga/memory.py`) — SQLite-backed, separate
  from the blackboard; promotion needs Main Brain approval.
- **Skills** (`airlangga/skills.py`) — load a skill from a YAML/Markdown
  file in our own format; skills are scanned before loading and never
  execute code on load. Example: `airlangga/skills/research.yaml`.
- **API server** (`airlangga/api_server.py`) — OpenAI-compatible stub:
  `GET /v1/models` lists `airlangga/<team>/<member>` aliases,
  `POST /v1/chat/completions` answers through that member's provider.
  Local bind only by default; model-routes aliasing to team members
  beyond this stub is a v2 item.

### Telegram + browser demo (offline / mock)

No bot token and no network are needed for the offline demo:

```bash
# Full team run with the mock provider (no API key):
.venv/bin/python -m airlangga.cli demo

# Browser fetch against the live web (needs network + egress proxy):
.venv/bin/python -c "from airlangga.tools_browser import fetch_url; print(fetch_url('https://example.com')[:200])"

# Telegram gateway (needs a real bot token + allowlisted user id):
export TELEGRAM_BOT_TOKEN=...
.venv/bin/python -m airlangga.cli telegram --allow-user 123456789
# then in Telegram: /goal Produce a sourced brief on <topic>.
# Without a token the command fails cleanly: TELEGRAM_BOT_TOKEN is not set.

# API server stub (mock provider, localhost only):
.venv/bin/python -m airlangga.cli serve --port 8765
curl http://127.0.0.1:8765/v1/models
```

## Web UI — Agentic Team Studio

A full web UI for building teams visually, served at `IP:port`
(default port **8100**).

```bash
# Locally (localhost only, no token needed):
airlangga ui
# → http://127.0.0.1:8100

# On the VPS (public bind requires a token — no default password):
export AIRLANGGA_UI_TOKEN=$(openssl rand -hex 24)
airlangga ui --host 0.0.0.0 --port 8100
# → http://162.35.32.92:8100
# Opening the URL shows a login page (never a 401 JSON): enter the
# token, and the page stores it in sessionStorage (this tab only) and
# loads the app. A wrong token shows "Wrong token — try again" on the
# login page. ?token=<token> also works: the page stores it and then
# cleans the token out of the address bar.
```

What the UI does:

- **Node graph** (n8n-style in idea only — original code): drag nodes,
  draw connections *between brains*: Model A powers which brains,
  which files/folders attach to a member, which members belong to
  which team, which tools a member can use. Saving the graph writes
  back to `airlangga.yaml` (member moves, model changes, charter
  attachments). Node types: Main Brain, team, member, model, file,
  folder, tool, skill.
- **Teaming editor**: create/edit/delete teams and members, change
  anything yourself — models, providers, toolsets, budgets, approval
  mode, charter file.
- **Files as first-class nodes**: create/edit files and folders under
  `files/` in the built-in editor. A user can write their own persona
  file (e.g. `files/personas/superagent.md`, seeded as an example) and
  attach it as a member's charter — in the graph or in the member
  editor. Writes are scoped to `files/`; `..` escapes and credential
  paths (`.env`, `.ssh`, keys) are refused.
- **Models**: Main Brain editor, per-member model table, provider
  presets (Anthropic / OpenAI / DeepSeek / OpenRouter / Gemini /
  Ollama local / custom base_url / mock). Credentials are references
  only (`env:VAR`), never stored in the config.
- **Runs**: launch a team on a goal (mock or real providers), watch
  progress, open any run's trace — plan tree, events, cost per actor,
  dissents, ledger replay.
- **Settings**: Telegram (bot token stored locally, mode 0600, never
  returned by the API; allowlist), approval default, run/team budgets,
  cron jobs (add + run due jobs), skills (create/validate).

**Changing the UI password:** log in, go to Settings → *Change UI
password*, enter the current token and the new one (at least 8
characters). It takes effect immediately — the old token stops working
at once, no restart needed — and it is stored in the token file
(`AIRLANGGA_UI_TOKEN_FILE`, or `<project-root>/.ui-token` by default,
mode 0600), so a server restart keeps the new token. The token value
is never returned by any API response. The same endpoint is available
as `POST /api/settings/ui-token` with
`{"current_token": "...", "new_token": "..."}` (authenticated with the
current token).

Backend: `airlangga/web_ui.py` (stdlib `http.server`, no new
dependencies) + one self-contained page `airlangga/ui.html` (inline
CSS/JS, no build step, no copied front-end code). Auth is the
`AIRLANGGA_UI_TOKEN` env var (or the token file it is loaded from);
without a token the server binds localhost only and a public bind is
refused.

```bash
.venv/bin/python -m pytest tests/test_web_ui.py -q   # 16 UI tests
```

## Configure a real team

```bash
airlangga init            # writes an example airlangga.yaml
airlangga validate        # validates the config
```

Edit `airlangga.yaml`: each member pins its own provider/model/endpoint.
Three members on three different providers is the intended shape, for
example Anthropic (official API), DeepSeek (OpenAI-compatible custom
endpoint), and Ollama (local, `http://localhost:11434/v1`). Credentials
are references only — `auth_ref: env:ANTHROPIC_API_KEY` — never a literal
secret in the file.

```bash
export ANTHROPIC_API_KEY=...
export DEEPSEEK_API_KEY=...
airlangga run --team research-01 --goal "Produce a sourced brief on <topic>."
```

## CLI

| Command | What it does |
|---|---|
| `airlangga init` | Write an example `airlangga.yaml` |
| `airlangga validate --config airlangga.yaml` | Validate a config file |
| `airlangga run --team research-01 --goal "..."` | Run a team against a goal |
| `airlangga demo` | Offline demo with the mock provider |
| `airlangga trace --ledger runs/<run>/ledger.db --run-id <id>` | Show a run's trace |
| `airlangga replay --ledger ... --run-id ...` | Replay a run (mock) + single-agent baseline comparison |
| `airlangga telegram --allow-user <id>` | Telegram gateway: `/goal` in, run result out (token from env) |
| `airlangga serve --port 8765` | OpenAI-compatible API stub (localhost only by default) |
| `airlangga schedule --goal "..." --interval-min 60` | Run one scheduler tick for a team job |
| `airlangga ui [--host 0.0.0.0 --port 8100]` | Web UI: node-graph team editor, files, runs, settings |

Run state lives under `runs/<run-id>/`: `ledger.db` (append-only SQLite
WAL event log), `blackboard.db`, `artifacts/`.

## Architecture

```
airlangga/
├── cli.py            # CLI: init / validate / run / demo / trace / replay
├── config.py         # airlangga.yaml loading + validation (roster schema)
├── team.py           # Team Runtime: roster, lifecycle, Main Brain planning
├── brain.py          # Main Brain + Team Brain as one turn loop, two configs
├── turn.py           # Turn loop: model call → tool dispatch → results
├── providers/        # Provider abstraction (openai_chat, anthropic_messages,
│                     #   gemini, mock) + factory; vendors are endpoint records
├── contracts.py      # Task Contract schema, validation, acceptance checks
├── ledger.py         # Run Ledger: append-only SQLite WAL, replay/resume
├── blackboard.py     # Typed versioned entries, propose/commit, FTS search
├── context.py        # Context Builder: per-role token budgets, by-reference
├── router.py         # Capability-tagged routing, capability-gated fallbacks
├── budget.py         # Budget Governor: hard caps, pre-flight, circuit breaker
├── policy.py         # Policy Engine: per-role tool allowlists, at the boundary
├── guardrails.py     # Hardline denylist, file-write safety, secret redaction
├── artifacts.py      # Artifact Store: per-run workspace, hashes, versions
├── debate.py         # Bounded debate, max 2 rounds, verifier-first, dissent
├── memory.py         # Long-term memory, Main-Brain-approved promotion only
├── scheduler.py      # Small job runner (tick loop, file lock)
├── notify.py         # Human-in-the-loop notifier (webhook + CLI fallback)
├── trace.py          # Trace viewer + replay + single-agent baseline
├── gateway_telegram.py # Telegram bot gateway (env token, user allowlist)
├── tools_browser.py  # Browser fetch (SSRF guard) + pluggable search
├── tools.py          # Member tools: file / terminal / browser, policy-gated
├── skills.py         # Skills loader (own YAML/Markdown format, scanned)
├── api_server.py     # OpenAI-compatible API stub (/v1/models, /v1/chat/completions)
├── web_ui.py         # Web UI backend: graph/config/files/runs/settings JSON API + auth
├── ui.html           # Web UI frontend: node graph, editors, runs, settings (self-contained)
├── http_client.py    # Shared HTTP client (explicit egress proxy, system CA)
└── templates/        # research.yaml, code-review.yaml, content.yaml
└── skills/           # example skills (research.yaml)
```

## Safety

Enforcement lives in the runtime, at the action boundary — never only in
a prompt. The hardline denylist (destructive commands, credential
exfiltration, pipe-to-shell, and similar) can never be overridden by any
mode, Brain, or member. Default approval mode for tool-using members is
`smart`; `off` is permitted only behind an explicit disposable-host flag.
Inter-agent messages are treated as untrusted input. Approvals go to a
human, never to a Brain.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

## IP

Airlangga is written from scratch for clean commercial ownership. No code
from any other agent project is copied, forked, imported, or vendored.
The design was informed by a read-only teardown of another agent system
and by a design review with Antigravity; both are learning input only —
every implementation here is original. See `SPEC.md` §9.
