# P0 FIX — Airlangga run output is never displayed

You are the coding agent. Fix P0 and only P0. Work in `/home/hatch/workspace/airlangga`.

## 0. Background — read first if anything is unclear

- **Airlangga** is an Agentic Team system built **FROM SCRATCH** (clean IP, NOT a fork or copy of Hermes). Core: run ledger, task contracts, blackboard, router, budget governor, policy engine, team runtime, providers. Web UI: stdlib `http.server` (`airlangga/web_ui.py`) + single self-contained `airlangga/ui.html`. CLI: `airlangga` package.
- Read in this order: `SPEC.md`, then the P0 section of `uiux-gemini-user-report.md`, then the code (`airlangga/` ledger/blackboard/api_server, `ui.html`, CLI run/trace).
- **If the architecture is still unclear, study the Hermes teardown FIRST:** read `teardown-hermes.md` in this repo (read-only teardown of Hermes Agent v0.23.2, done for learning only). Hermes source lives on the VPS at `/root/.hermes/hermes-agent` — read-only reference, reachable via SSH (see §4 for the SSH command). NEVER edit anything under it, NEVER copy Hermes code into Airlangga. Teardown is learning only; the fix itself must be written fresh against Airlangga's own design.
- Repo: https://github.com/Orchdhaaa/airlangga (private, branch `main`). Live UI: http://162.35.32.92:8100.

## 1. The P0 bug (from the Gemini user-test report)

**Team output is never displayed anywhere.** A run's reports/claims land in `blackboard.db`, but `GET /api/runs/<id>`, the UI Run Detail view, and the CLI only show `claims=1` — the user can never see what the team actually answered. Reproduce this first (mock run on a scratch team) and confirm the output is invisible via API + UI + CLI, so the fix is verified against the real failure.

## 2. The fix

Fix it end-to-end, minimal and consistent with the existing ledger/blackboard design (do NOT invent a new storage scheme):
- `GET /api/runs/<id>` must return the run's actual output/claims content (not just counts).
- The UI Run Detail view must render that content.
- The CLI (run/trace output) must show it.
- Add regression tests for the fix. Run the full test suite — it must stay green (baseline 71/71).

## 3. Deploy to the VPS (after tests pass)

- SSH (always): `ssh -i /home/hatch/.ssh/id_ed25519 -o UserKnownHostsFile=/home/hatch/.ssh/known_hosts root@162.35.32.92`
- rsync from this repo to `/root/airlangga` with excludes: `.venv, runs, __pycache__, .pytest_cache, *.db, .airlangga-secrets.json, .airlangga-ui.json, .ui-token` — NEVER overwrite the VPS token file.
- Restart `airlangga-ui.service` on the VPS, then verify live FROM THE VPS itself via its public IP (`curl http://162.35.32.92:8100/...`) — curl from this VM to port 8100 fails (egress proxy), so verify on the VPS.
- Verify the fix live: run a mock run, then confirm its output is visible via the live API.

## 4. Push to GitHub

- Verify `git ls-files` contains no db/venv/token/secrets files and no personal data (no emails, real names, passwords, tokens) before pushing. Commit with a clear message, push to `main`.

## 5. Constraints

- **P0 ONLY** — do not fix the other 15 bugs or any UI/UX critique items.
- Do not change auth/token behaviour. No real LLM keys, no live Telegram, no mutations to live VPS data beyond the deploy.
- If anything blocks, say so in your final summary instead of working around it silently.

## 6. Deliverable

End your run with a short summary: root cause, files changed, test results, live verification evidence, pushed commit hash.
