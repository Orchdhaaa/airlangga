# Airlangga end-user test — Gemini report

**Status: BLOCKED — Gemini never ran. No Gemini output exists in this file. Nothing below is presented as Gemini's words.**

## What happened

The task was to run Gemini 4 Neon XHigh (via Antigravity CLI `agy` v1.5.13) as a first-time end user: read the repo, use the CLI, use the live web UI, and deliver a user-perspective report.

The `agy` call failed on authentication before Gemini did any work:

```
error: UNAUTHENTICATED (code 401): Request had invalid authentication credentials.
Expected OAuth 2 access token, login cookie or other valid authentication credential.
AGY_ERROR: {"short_error":"UNAUTHENTICATED (code 401) ...","status":"UNAUTHENTICATED",
"error_code":401,"code_kind":"http","retryable":false,
"error_id":"7c2aa3c6-cb2a-4179-9bdf-2aa61f543617-57"}
```

Full error saved in `uiux-gemini-user-test-err.log`. Raw output file `uiux-gemini-user-test-raw.md` is **0 bytes** — Gemini produced nothing.

## Diagnosis (verified, not guessed)

- The failure is at the `agy` Google OAuth layer, not the model: even the lightweight `agy models` probe fails with the same `UNAUTHENTICATED (code 401)`.
- The Antigravity remote-control daemon is `active` (instance `vm`), so the service itself is up — only the credential is invalid.
- The OAuth token file (`~/.gemini/antigravity-cli/antigravity-oauth-token`) was last written 2026-11-20 12:00:45 UTC (19:00:45 WIB) — the same window the previous agent's successful Gemini run was happening. The token was good at ~19:00 WIB and invalid by ~19:31 WIB, when this run failed. Two independent 401s (the prompt run + the `agy models` probe) confirm it is persistent, not transient.
- The daemon log contains old "Authenticated as [the user's Google account]" lines (last log write 18:16 WIB) and an older "No valid authentication found (Your current account is not eligible for Antigravity...)" line. Re-authentication requires an interactive Google OAuth flow (visit a Google auth URL, paste an authorization code) — that is a **user action** and cannot be done non-interactively from this VM.
- A first backgrounded attempt of the same command was killed by me after the runtime reported it `pending_user_confirmation` with no visible prompt; the foreground re-run then failed with the 401 above. The kill did not cause the auth failure — the 401 was confirmed independently afterwards.

## What is needed to unblock the re-run

1. The user re-authenticates Antigravity on this VM (Google sign-in for the `[the user's Google account]` account, or another eligible personal Google account) — the `agy` login flow.
2. Verify with `agy models` (it must list models instead of 401).
3. Re-run exactly: `cd ~/workspace/airlangga && /home/hatch/.local/bin/agy --model gemini-4-neon-xhigh --dangerously-skip-permissions --add-dir ~/workspace/airlangga -p "$(cat uiux-gemini-user-test-prompt.md)" > uiux-gemini-user-test-raw.md 2> uiux-gemini-user-test-err.log`
4. No fallback model would help: every model in this `agy` build authenticates through the same Google OAuth session, so Claude/Sonnet/GPT entries would hit the same 401.

## Step 1 finding — GitHub repo: DOES NOT EXIST

Verified by the tester (me), not by Gemini:

- `~/workspace/airlangga/` is **not a git repository** (`git remote -v` / `git rev-parse` → "fatal: not a git repository").
- `gh repo list --limit 100` shows no `airlangga` repo under `Orchdhaaa`.
- `gh api repos/Orchdhaaa/airlangga` → HTTP **404 Not Found**.

So there is no GitHub repo to read. Per the task, no repo was created. Gemini (on re-run) reviews the local code at `~/workspace/airlangga/` instead: `README.md`, `SPEC.md`, `airlangga/*.py`, `airlangga/ui.html`, `airlangga.yaml`.

## Groundwork verified by the tester (NOT Gemini — labelled so it is never mistaken for Gemini's findings)

To confirm the product is ready for the re-run, I smoke-checked both surfaces myself:

- **CLI works:** `.venv/bin/python -m airlangga.cli --help` lists commands: `demo`, `init`, `replay`, `run`, `schedule`, `serve`, `telegram`, `trace`, `ui`, `validate`.
- **Live web UI is up:** `http://162.35.32.92:8100` — `/health` → 200, `/` (no token) → 200 HTML login page, `/api/state` (no token) → 401 as designed, `airlangga-ui.service` → active.
- I did NOT run a team, mutate anything, or read the UI token. The live project data is untouched.

## Files for the re-run

- Prompt (ready, 6,046 bytes): `uiux-gemini-user-test-prompt.md`
- Raw Gemini output (0 bytes — empty, run failed): `uiux-gemini-user-test-raw.md`
- Error log (the 401 above): `uiux-gemini-user-test-err.log`

## Synthesis (tester, max 15 lines)

- Gemini tested nothing: no CLI commands run by Gemini, no live endpoints hit by Gemini, no scratch mutations, no report. Top P0 finding is therefore the blocker itself: `agy` auth is broken (UNAUTHENTICATED 401), and the user-test cannot proceed until the user re-authenticates Antigravity.
- GitHub repo does not exist; the re-run must use the local code, as the prompt already instructs.
- The product itself is ready to be tested: CLI help works, live UI answers 200 on `/health` and serves the login page, API correctly 401s without a token, service is active.
- I dispute nothing from Gemini — there is nothing to dispute. The one thing to note for the re-run: the prompt file is complete and reusable as-is; do not re-write it, just re-run the command after auth is fixed.
