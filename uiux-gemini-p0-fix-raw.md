Waiting for the test suite and verification script to complete.
### Summary — P0 Fix (Run Output Displayed End-to-End)

#### Root cause
`TeamRuntime.commit_report()` persisted each member's full `Report` JSON (claims, confidence, `evidence_refs`, `diff`, `open_questions`, `verdict_self`) into `runs/blackboard.db`, while `runs/ledger.db` only logged a `blackboard_committed` pointer (`entry_id`, `member_id`). All three read paths ignored `blackboard.db` or dropped report bodies:
- `GET /api/runs/<id>` only read `ledger.db` and omitted `reports`/claim text altogether (reproduced on pre-fix `HEAD` `447974d` on a scratch team: `blackboard.db` had 1 row with the claim, API payload had none).
- `airlangga/ui.html` Run Detail had no Outputs view and never rendered member reports.
- CLI `_run_team` (`run`/`demo`) only printed `claims=1`, and CLI `trace` (`render_trace`) only read `ledger.db`, omitting claim content.

#### Files changed
- [blackboard.py](file:///home/hatch/workspace/airlangga/airlangga/blackboard.py) — Added `Blackboard.list_for_run(run_id, status=None)`, `Blackboard.count_by_run()`, and `entry_to_report(entry)` to decode committed `Report` JSON (with safe fallbacks for non-JSON entries).
- [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py) — Updated `UIStore.run_detail()` and added `UIStore.run_reports()` to return `reports` (full claims, confidence, `evidence_refs`, `diff`, `open_questions`, `verdict`) and include `Outputs:` in `trace_text` from `runs/blackboard.db` (survives restarts; never creates `blackboard.db` on read). Updated `list_runs()` to report accurate total claim counts.
- [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html) — Added an `Outputs (N)` subtab as the default Run Detail tab, rendering each member's verdict, status, claims (preserving line breaks, HTML-escaped), confidence, `evidence_refs`, `diff`, and `open_questions`.
- [trace.py](file:///home/hatch/workspace/airlangga/airlangga/trace.py) — Extended `render_trace(ledger, run_id, blackboard=None)` to append an `Outputs:` section with member verdicts, claims, confidence, `evidence_refs`, `diff`, and `open_questions` when a blackboard is provided.
- [cli.py](file:///home/hatch/workspace/airlangga/airlangga/cli.py) — Printed claim text, confidence, `evidence_refs`, `diff`, and `open_questions` in `_run_team()` (`run`/`demo`), and passed the sibling `blackboard.db` (if present) into `render_trace()` in `trace`.
- [test_blackboard.py](file:///home/hatch/workspace/airlangga/tests/test_blackboard.py), [test_cli.py](file:///home/hatch/workspace/airlangga/tests/test_cli.py), [test_web_ui.py](file:///home/hatch/workspace/airlangga/tests/test_web_ui.py) — Added regression tests covering `Blackboard` run queries + `entry_to_report`, CLI `demo`/`run`/`trace`, `GET /api/runs/<id>` + restart persistence + multi-claim counting, and `ui.html` Outputs tab rendering.

#### Test results
- `.venv/bin/pytest -v`: **78/78 passed** (up from 71/71 baseline; 7 new/expanded regression tests).
- Node.js verification of `airlangga/ui.html`: inline `<script>` syntax valid and `outputs` template rendered claims, `evidence_refs`, `diff`, and `open_questions` with HTML/XSS escaping intact.

#### Live VPS verification (`http://162.35.32.92:8100`)
- Deployed via `rsync` with all required excludes; verified `/root/airlangga/.ui-token` SHA-256 unchanged (`832b9c75bf45c3358e548939744ef4843cd7a8de519e6ec19f3761590a007d5a`, mode `600`).
- Restarted `airlangga-ui.service` (`active`) and verified from the VPS over `http://162.35.32.92:8100`:
  - `GET /health` → `{"status": "ok", "token_required": true}`
  - `GET /` → serves updated `ui.html` (`runDetailTab = "outputs"`, `Outputs (${reports.length})`)
  - `POST /api/runs` (`team: "research-01"`, `goal: "P0 live verification brief"`, `mock: true`) → `run-bd021fa8`
  - `GET /api/runs/run-bd021fa8` → `status=done`, `events=22`, `reports=3` (`researcher`, `fact_checker`, `writer` — each with verbatim claim text) and `trace_text` containing `Outputs:` + claim text.
  - `GET /api/runs` → `run-bd021fa8` listed with `claims=3`.
  - Live CLI `trace` on `/root/airlangga/runs/ledger.db --run-id run-bd021fa8` printed the `Outputs:` section with all 3 member claims.

#### Pushed commit
- **`0cc6d73601caa2fddbddb6619ce12c43fd4fad99`** (`0cc6d73`) on `origin/main` (audited `git ls-files` and diff for secrets/DB/venv/token/PII prior to push).
