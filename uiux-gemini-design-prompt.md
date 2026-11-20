# Airlangga Web UI — Gemini design brief (round 2)

You are the LEAD PRODUCT DESIGNER for the Airlangga Web UI. You are the designer — I implement exactly what you design. Work through the design step by step, reasoning deeply about each decision before writing it down. Output must be implementation-ready: concrete enough to implement line by line. No vague advice. If anything in the brief is ambiguous, pick the most useful interpretation and state it explicitly — do not ask questions.

## The product

Airlangga is an Agentic Team Studio: a web UI for building and managing teams of AI agents. A Main Brain assigns work to teams; each team has a Team Brain (or a lead member) and members; each member runs on a model from some provider (official API, custom base_url, or local) and carries a role, charter file, attached files, toolsets and skills. Everything is configured in `airlangga.yaml`; runs are recorded in a run ledger with a trace view.

## The user's original requirement (verbatim intent, Indonesian)

"Harus ada UI web nya yaaa. Pakai IPvps:port. Nanti disitu Lo tau N8N? Nah hampir mirip cuma bedanya ini tuh connection antar brain. Jadi misal model A mau pakein brain apa aja, terus file apa aja yang connect ke itu, dll. Jadi ini enak banget untuk teaming/pembentukan team nya. User bisa ubah-ubah sendiri isinya, bisa nambahin file or folder nya. Misal user mau pake SUPERAGENT pun bisa dengan bikin file sendiri, edit sendiri, dll. Ataupun import file Zip. Tapi UI bukan hanya itu, ada konfigurasi lain."

In plain terms: a web UI served at VPS_IP:port. N8N-like, except the connections are between brains: which brains a model powers, which files connect to a brain/member, etc. It must make team formation easy. The user can change everything themselves, add files or folders, create and edit their own files (e.g. make their own SUPERAGENT persona file), or import a ZIP. And the UI is not only the graph — it also covers other configuration.

## Current state — READ THE CODE FIRST

Repo root is the added workspace directory. Read these files before designing:

- `airlangga/ui.html` — the UI itself: ONE self-contained page (inline CSS/JS, no build step, no framework, no external fonts/CDN — it must stay offline-safe). 6 tabs: Graph, Teams, Models, Files, Runs, Settings. Token login page (token in sessionStorage only, never in the URL; `/api/*` without a token returns 401 JSON; `GET /` without a token serves the 200 HTML login page). Graph is persisted to `airlangga-graph.json` and applied back to `airlangga.yaml`. Files live under `files/` and are editable in the UI (example `files/superagent.md` is seeded).
- `airlangga/web_ui.py` — backend (Python stdlib `http.server`): JSON API for state, graph save/load, team/member CRUD, Main Brain update, provider presets, files, settings, skills, runs, cron tick.
- `uiux-gemini-review.md` — your own earlier critique of this UI (generic dark dev-tool scaffold slop; "Candi Obsidian & Lontar Studio" direction: warm obsidian `#0D0C0A`, ivory `#F4EFE6`, gold `#D4AF37` reserved for the one primary action per screen). Use it as the starting point, but this design must serve the original brief above, not just the review.
- `README.md` (UI section) and `airlangga.yaml` (example config) for context.

Important: a previous implementer ALREADY applied much of the earlier review to the current tree — warm obsidian palette, heading hierarchy, 4-tier button hierarchy, port-to-port type-coloured graph edges, per-section Settings save, and a fix so graph-added nodes persist through save/reload. Do NOT redesign those from zero: read the current `ui.html`, keep what is good, and design the gaps and the next level. Known gaps in the current tree:

1. ZIP IMPORT does not exist yet — design it end to end (see below).
2. Mobile (~390px phone browser): there are `@media` queries, but no bottom-sheet inspector — the side panel still competes with the graph canvas.
3. Verify in your design that these traps are closed: graph-added team/member nodes persist through save/reload; Settings per-section save actually persists every section; graph drag does not re-render the whole DOM per pointermove.

## What you must design (complete, implementation-ready)

1. **Information architecture** — the 6 tabs and the login page; what belongs on each tab; what the user sees first; the one primary action per screen.
2. **Node graph** (the heart of the brief) — node types (main brain, team, member, model, file, folder, tool, skill) and how they look different from each other; connections (assigns / has_member / uses_model / powers / has_charter / has_file / uses_tool / uses_skill / depends_on); drag, connect, delete, side-panel editor; adding a team/member/model/file node from the graph; how a graph edit maps back to `airlangga.yaml`; empty state for a brand-new user.
3. **Team formation UX** — the fastest path from "I have an idea" to a working team: create team, add members, pick a model per member, attach a charter file, set budgets/approvals. Make the SUPERAGENT example concrete: user creates `files/superagent.md`, attaches it as a member charter, and that member now behaves as SUPERAGENT.
4. **File manager** — create/edit/delete files and folders, the in-UI editor, and **ZIP IMPORT**: full end-to-end flow (pick a .zip, upload, extract into `files/`, show the extracted file list, handle errors). Rules the flow must respect: reject traversal entries (`../`, absolute paths), reject credential paths, reject oversized zips, reject non-zip files. State exactly what the user sees at each step and what the backend endpoint returns.
5. **Models / providers** — provider presets (Anthropic, OpenAI, DeepSeek, OpenRouter, Gemini, Ollama, custom, mock), endpoint + auth_ref + model + capabilities + cost; capability-gated fallbacks; how the user adds a custom base_url provider.
6. **Runs + trace view** — launch a run (team + goal + mock/real), live status, event trace, per-actor cost, contracts, dissents, failure display in human words (never raw JSON dumps or raw snake_case).
7. **Settings** — Telegram gateway (bot token, allowlist), approval default, budgets, cron jobs, change UI password; per-section save behaviour.
8. **Mobile layout (~390px)** — stacked layout, bottom-sheet inspector for the selected node, scrollable tab nav, tables that wrap/stack, 44px touch targets, graph auto-fit on load.
9. **Full visual system** — palette with exact hex values, type scale (families via system font stacks only — NO webfont downloads, offline-safe), spacing scale, radius, borders, shadows, component specs (buttons 4-tier, inputs, selects, tables, pills/badges, cards, modals, toasts, login page), hover/focus/disabled/selected states, and the empty/loading/error states for every tab.

## Quality bar

Premium-playful agency-grade, anti-AI-slop: NO purple-blue gradients, NO emoji as icons, NO glassmorphism, NO generic hero, NO three-identical-feature-cards, NO batik clip-art or kitsch heritage decoration. Body text contrast >= 4.5:1. One clear action per screen. Dense pro tool, not a marketing page — usable on a phone browser as well as desktop. All UI copy in English.

## Output format

Structured Markdown, in this order:

1. Design decisions (the 8–12 most important choices, each with one line of why).
2. Information architecture (tabs, first screen, primary action per screen).
3. Visual system (exact hex palette, type scale, spacing/radius, component specs with states).
4. Graph design (node visuals per type, edge styles per kind, interactions, side-panel editor fields, empty state, persistence rules).
5. Files + ZIP import (flows step by step, UI strings, backend endpoint contract).
6. Teams / Models / Runs / Settings (per-tab design, fields, flows, human copy).
7. Mobile design (breakpoints, stacked layout, bottom-sheet inspector spec, touch targets).
8. Implementation checklist, prioritised P0 (must ship) / P1 (real UX wins) / P2 (polish), each item concrete enough to check off — include the exact strings, hex values and measurements the implementer needs, not references back to earlier sections.

Do not ask questions. Do not describe what you cannot decide. Decide, specify, and move on.
