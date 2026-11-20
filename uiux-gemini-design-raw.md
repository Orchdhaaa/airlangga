# Airlangga Web UI — Round 2 Implementation-Ready Design Specification

> **Design scope & explicit decisions on ambiguities:**
> - **Baseline preserved:** The current [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html) already implements the Candi Obsidian & Lontar Studio palette, heading hierarchy, 4-tier buttons, port-to-port edges, fixed toast, and `body.auth-pending`. This specification keeps that foundation and closes every remaining functional, persistence, mobile, and UX gap discovered in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html), [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py), and [brain.py](file:///home/hatch/workspace/airlangga/airlangga/brain.py).
> - **ZIP import transport:** Uses raw binary `POST /api/files/import-zip` (`Content-Type: application/zip`) instead of `multipart/form-data` or base64 JSON so Python's stdlib `http.server` enforces exact `Content-Length` limits before reading a single byte, with zero external libraries.
> - **SUPERAGENT charter execution:** Attaching `files/superagent.md` as a member's `charter_file` must genuinely change member behavior — this spec defines both the UI flow and the required backend prompt injection in [brain.py](file:///home/hatch/workspace/airlangga/airlangga/brain.py) / [team.py](file:///home/hatch/workspace/airlangga/airlangga/team.py).
> - **Offline safety:** Zero external `<link>` tags, zero webfonts, zero CDNs. Typography uses pure system font stacks only.
> - **Test compatibility:** Keeps existing DOM IDs (`loginScreen`, `loginForm`, `loginToken`, `btnLogin`), login copy (`Enter Studio`, `Wrong token`), zero mentions of `localStorage` anywhere in `ui.html` (including comments), and all existing `/api/*` endpoints from [test_web_ui.py](file:///home/hatch/workspace/airlangga/tests/test_web_ui.py).

---

## 1. Design Decisions

1. **Preserve the Candi Obsidian & Lontar Studio foundation and zero-build single-file architecture** — Keeping warm obsidian (`#0D0C0A`), ivory (`#F4EFE6`), and antique gold (`#D4AF37`) inside one offline-safe `ui.html` avoids rework and respects VPS deployment simplicity.
2. **Make the Graph a true bidirectional brain-wiring workbench (`airlangga-graph.json` ↔ `airlangga.yaml`)** — Closing the current gaps where graph-added teams/members never write to YAML, `powers`/`uses_tool`/`uses_skill` edges are ignored on save, and deleted edges resurrect on reload eliminates every graph data-loss trap.
3. **Deduplicate identical model endpoints into shared `Model` nodes** — Rendering one `Model` node powering multiple brains/members directly fulfills *"which brains Model A powers"* and turns multi-member model swaps into a single node edit.
4. **Auto-infer edge kind from `(source.type, target.type)` in Connect mode (plus desktop port-drag)** — Picking from 9 edge kinds before clicking breaks visual flow; smart defaults cut wiring to two taps while keeping manual override one click away.
5. **Fix zoom-compensated pointer drag + 4px click-vs-drag threshold without rebuilding DOM** — Current `startDrag` ignores `zoom` (breaking touch drags when `fitGraph()` zooms to ~30%) and fires `click` after drag, erroneously opening the mobile bottom sheet.
6. **Stream raw binary `.zip` uploads to `POST /api/files/import-zip` with atomic validate-all-before-write** — Checking `Content-Length`, ZIP magic bytes, traversal, symlinks, credentials, file count, and zip-bomb ratio in memory before writing guarantees zero partial writes on rejected archives.
7. **Unify the SUPERAGENT persona workflow across Files, Teams, Graph, and Runtime** — Adding an `Attach as charter…` button inside the Files editor, selecting `superagent.md` in the Member modal or via a `has_charter` graph edge, and injecting the file into `member_prompt()` makes personas real and verifiable in the Run trace.
8. **Fix the `skills: []` member-save wipe bug and expose capability-gated fallbacks + custom `base_url` presets** — Editing any member in `ui.html` currently overwrites `skills` with `[]` and hides `capabilities`, `attached_files`, `cost_per_mtok_usd`, and `fallback`; exposing them with live `ELIGIBLE / WILL SKIP` gate pills brings Airlangga's router guarantee to the UI.
9. **Render every run failure, contract, dissent, and ledger event in plain English** — `showRun()` currently ignores `d.error` (leaving failed runs unexplained) and falls back to raw `JSON.stringify()` in timeline summaries and dissents; translating errors and adding a `Contracts` sub-tab makes Runs operator-ready.
10. **Demote Settings section saves to Secondary at rest and promote to Gold only when dirty** — Updating `S.settings` per saved section without re-rendering untouched cards stops saving Telegram from silently wiping unsaved edits in Budgets while obeying "one primary gold button per screen."
11. **Deliver a full mobile (~390px) bottom-sheet inspector with scrim, grabber, sticky header, and single-row canvas toolbar** — Opening the sheet on node tap, edge tap, and `+ Add node`, moving zoom into a floating corner pill, and stacking all tables makes the entire studio usable on a phone browser.

---

## 2. Information Architecture

### Auth Gate & First Screen
- **Unauthenticated entry (`GET /`, `/ui`, `/ui.html`):** Always serves HTTP `200` HTML with `<body class="auth-pending">` so `<header>`, `<nav>`, and `<main>` stay `visibility: hidden` until `/api/state` resolves (zero flash of unauthenticated chrome).
- **Token handling:** Stored in `sessionStorage` (`airlangga_token`) only. If `?token=...` is present in the URL, `boot()` stores it in `sessionStorage` and strips it immediately via `history.replaceState({}, "", location.pathname)`. Every `/api/*` request sends `X-Airlangga-Token`; `401` clears nothing unless submitted from the login form and reveals `#loginScreen`.
- **First screen after login:** The **Graph** tab (`#tab-graph`). On viewports `<= 820px`, `fitGraph()` runs inside `requestAnimationFrame` immediately after initial render. If `airlangga.yaml` has zero teams (`Object.keys(S.config.teams).length === 0`), the Graph shows the `Main Brain` node plus a non-blocking **Starter Onboarding Card** anchored inside the canvas.

### Global Chrome
- **Header (`52px` fixed height, `#161411`, `1px solid #2E2A22` bottom border):**
  - Left: `20×20px` geometric Kahuripan stepped-diamond gold SVG mark + `Airlangga` (`20px` display serif) + `/ Studio` (`12px` `#B3AA9B`, hidden at `<= 640px`).
  - Right: Compact mono auth badge (`TOKEN ACTIVE` or `LOCALHOST`, `11px` uppercase) + `Sign out` ghost button (visible only when a token is active).
- **Navigation Rail (`44px` height, `#12100D`, `1px solid #2E2A22` bottom border, horizontally scrollable with hidden scrollbar):**
  - 6 tabs in fixed order: `Graph` · `Teams (N)` · `Models` · `Files (N)` · `Runs (N)` · `Settings`.
  - Active tab: `#F4EFE6` text + `2px solid #D4AF37` bottom indicator. Count badges (`N`) render in `11px` mono `#8C8375` (`#D4AF37` when active).
- **Global Status Toast (`#status`):** Fixed bottom-right (`16px` inset on desktop; `12px` left/right/bottom on `<= 820px`, `z-index: 40`), click-to-dismiss, `4500ms` auto-dismiss for neutral/ok and `7000ms` for errors.

### Per-Screen Ownership & Primary Action Matrix

| Screen | Primary Purpose (What Belongs Here) | Explicitly Excluded | The ONE Primary Gold Action |
|---|---|---|---|
| **Login** (`#loginScreen`) | Authenticate operator into the Studio; explain `sessionStorage` token scope. | App navigation, settings, unauthenticated state preview. | `Enter Studio` (full-width `#D4AF37`). |
| **Graph** (`#tab-graph`) | Visual brain/model/member/file/tool wiring, drag layout, node/edge inspection, direct graph-to-YAML persistence. | Long-form file editing, run traces, cron/Telegram settings. | `Save graph` (Gold `*` when dirty; Secondary at rest when clean). |
| **Teams** (`#tab-teams`) | Team creation (with optional template member seeding), team goal/mode/budget editing, member roster CRUD, full Member Editor modal (model, charter, files, tools, skills, fallbacks, budget, approval). | Raw provider reference table, file editing, Telegram/cron config. | `+ New team` (Gold in tab header; inside Create drawer or Member modal, `Create team` / `Save member` takes focus as modal primary). |
| **Models** (`#tab-models`) | Main Brain model/endpoint/capability/budget config, reusable custom `base_url` providers, cross-team Member Models & Fallback Gate overview, collapsible built-in Provider Reference. | Team creation, file browsing, run launching. | `Save Main Brain` (Gold in hero card). |
| **Files** (`#tab-files`) | Full CRUD for files & folders under `files/`, in-UI monospace editor, **ZIP import**, 1-click `Attach as charter…` and `Add to graph`. | YAML skill files (`airlangga/skills/` live in Settings), credential paths. | `Save file` (Gold when open file is dirty; Secondary when clean; inside ZIP modal, `Upload & extract` is modal primary). |
| **Runs** (`#tab-runs`) | Launch team runs (`Mock` or `Real providers`), live running status, Run History table, structured Run Detail (`Timeline`, `Contracts`, `Cost Breakdown`, `Dissents`, `Raw Trace`) + human failure banners. | Editing member models or charters directly (link out instead). | `Run team` (Gold in launch command bar). |
| **Settings** (`#tab-settings`) | 5 independent configuration cards: Telegram Gateway, Approvals & Budgets, Scheduled Jobs (Cron), Skills (YAML), Change UI Password. | Team/member roster edits, file manager. | **Dirty-only per-section promotion:** each section's Save button is Secondary at rest and turns Gold (`#D4AF37`) when that section has unsaved changes (never multiple competing gold buttons at rest). |

---

## 3. Visual System

### Color Palette (WCAG AA Mathematically Verified)

| Token | Hex / Value | Role | Measured Contrast |
|---|---|---|---|
| `--bg` | `#0D0C0A` | Page background (warm volcanic obsidian) | Base canvas |
| `--canvas-bg` | `#090807` | Graph canvas well (with `1px` dot grid `#2A251D` at `20px` spacing) | Deepest layer |
| `--nav-bg` | `#12100D` | Top tab rail background | `#B3AA9B` on `#12100D` = **8.27:1** |
| `--input-bg` | `#11100D` | Inputs, selects, textareas, code wells | `#F4EFE6` on `#11100D` = **16.61:1** |
| `--surface` | `#161411` | Primary cards, header, inspector, modals, bottom sheet (warm andesite) | `#F4EFE6` on `#161411` = **16.05:1** |
| `--surface-2` | `#1F1C17` | Graph nodes, elevated secondary panels, toast, pill base (dark teak) | `#F4EFE6` on `#1F1C17` = **14.83:1** |
| `--surface-3` | `#29251E` | Interactive row hover fill, tag fill, secondary button hover | `#F4EFE6` on `#29251E` = **13.5:1** |
| `--btn-sec` | `#242019` | Secondary button resting fill | `#F4EFE6` on `#242019` = **14.2:1** |
| `--border` | `#2E2A22` | Structural `1px` hairlines (cards, dividers, table rows) | Structural |
| `--border-strong` | `#3D372C` | Table header bottom border, pill borders, login card border | Structural |
| `--border-ctrl` | `#524B3E` | Resting input, select, secondary button, and node border | UI control >= 3:1 |
| `--border-hover` | `#857A66` | Hover border on inputs, buttons, and graph nodes | High emphasis |
| `--text` | `#F4EFE6` | Primary text (warm lontar ivory) | **17.07:1** on `#0D0C0A`, **16.05:1** on `#161411` |
| `--muted` | `#B3AA9B` | Secondary text, labels, table headers, nav inactive | **8.00:1** on `#161411`, **7.39:1** on `#1F1C17` |
| `--subtle` | `#8C8375` | Placeholders, timestamps, byte sizes, footnotes | **4.92:1** on `#161411`, **4.54:1** on `#1F1C17`, **5.09:1** on `#11100D` |
| `--gold` | `#D4AF37` | Primary CTA fill, Main Brain accent, active tab underline, focus ring | `#0D0C0A` on `#D4AF37` = **9.30:1**; `#D4AF37` on `#161411` = **8.74:1** |
| `--gold-hover` | `#E5C558` | Primary CTA hover fill | `#0D0C0A` on `#E5C558` = **11.60:1** |
| `--gold-tint` | `rgba(212,175,55,0.12)` | Active file row, selected table row, connect banner fill | Subtle tint |
| `--accent2` | `#D96B43` | Majapahit terracotta — Team nodes, `has_member` edges, dissent count, capability-skip warning | **5.37:1** on `#161411` |
| `--info` | `#56B4C8` | Nila cyan — Member nodes, `depends_on` edges, links, running status, connect source | **7.67:1** on `#161411` |
| `--ok` | `#4CC38A` | Pandan jade — Model nodes, `uses_model` edges, done/passed/eligible/success | **8.30:1** on `#161411` |
| `--ochre` | `#C89B54` | Sogan ochre — File/Folder nodes, `has_charter`/`has_file` edges, unsaved/draft badges | **7.24:1** on `#161411` |
| `--pewter` | `#9E9587` | Pewter — Tool/Skill nodes, `uses_tool`/`uses_skill` edges | **6.12:1** on `#161411` |
| `--danger` | `#E55B50` | Vermilion — Danger hover fill, error toast border, failed banner border | `#0D0C0A` on `#E55B50` = **5.53:1**; on `#161411` = **5.20:1** |
| `--danger-text` | `#F2786D` | Outlined danger button text, error messages, failed status pill text | **6.73:1** on `#161411` |
| `--danger-border` | `#6E2D28` | Outlined danger button resting border | Subtle containment |

### Typography (100% System Font Stacks — Offline-Safe, Zero External Requests)
- `--font-display`: `'Iowan Old Style', 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif`
- `--font-sans`: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', system-ui, sans-serif`
- `--font-mono`: `ui-monospace, 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', monospace`

| Role | Family | Desktop Size | Mobile (`<=640px`) | Weight | Line-Height | Letter-Spacing / Extras |
|---|---|---|---|---|---|---|
| Login Wordmark | `--font-display` | `30px` | `26px` | `700` | `1.1` | `-0.02em` |
| Header Wordmark | `--font-display` | `20px` | `18px` | `700` | `1.1` | `-0.02em` |
| Section / Card H2 | `--font-sans` | `16px` | `15px` | `700` | `1.25` | `-0.015em` |
| Subsection H3 / Group | `--font-sans` | `12px` | `12px` | `700` | `1.3` | `+0.08em`, `uppercase`, `#B3AA9B` |
| Body / Table Cell | `--font-sans` | `14px` | `14px` | `400` | `1.5` | `0` |
| Form Label / Table TH | `--font-sans` | `11px` | `11px` | `600` | `1.3` | `+0.07em`, `uppercase`, `#B3AA9B` |
| Input / Select / Textarea | `--font-sans` (`--font-mono` for textarea) | `14px` (`13px` textarea) | **`16px`** (prevents iOS zoom) | `400` | `1.45` | `0` |
| Mono Data (IDs, Models, USD, Paths) | `--font-mono` | `12.5px` | `12.5px` | `400`/`500` | `1.45` | `font-variant-numeric: tabular-nums` |
| Trace / Payload `<pre>` | `--font-mono` | `12px` | `11.5px` | `400` | `1.5` (`1.45` mobile) | `white-space: pre-wrap; word-break: break-word` |
| Micro-Pill / Node Type Eyebrow | `--font-mono` | `10.5px`–`11px` | `10.5px`–`11px` | `500`–`600` | `1.2` | `+0.06em`, `uppercase` |

### Spacing, Radius, Borders & Elevation
- **Spacing scale (`4px` base):** `4px`, `8px`, `12px`, `16px`, `20px`, `24px`, `32px`. Main container padding `16px` (`12px` at `<= 820px`). Card padding `16px` (`14px` at `<= 640px`), vertical card gap `14px`. Action bar `.actions`: `display:flex; gap:8px; margin-top:14px; flex-wrap:wrap; align-items:center`.
- **Radius scale:**
  - `2px`: Status pills (`.pill`), micro-tags (`.tag`), auth badge (`#tokenBadge`).
  - `3px`: Tool/Skill graph chips, SVG edge label pill `<rect rx="3">`.
  - `4px`: Cards, buttons, inputs, selects, textareas, graph canvas container, modals, toast, login card.
  - `6px`: Standard graph nodes (`main_brain`, `team`, `member`, `model`).
  - `4px 14px 6px 6px`: `file` and `folder` graph nodes (subtle notched document corner).
  - `12px 12px 0 0`: Mobile slide-up bottom sheet (`#sidePanel`, mobile modals).
- **Elevation / Shadows (zero blur on static panels):**
  - Static cards/panels: `1px solid #2E2A22`, `box-shadow: none`.
  - Selected / dragged graph node: `0 0 0 2px rgba(212,175,55,0.32), 0 8px 22px rgba(0,0,0,0.55)`.
  - Floating toast / mobile bottom sheet / modal card: `0 12px 32px rgba(0,0,0,0.68)`.
  - Backdrop scrim (`#sheetScrim`, `#memberModal`, `#zipModal`): solid `rgba(0,0,0,0.62)` — NO `backdrop-filter: blur()`.

### Iconography Rule (Zero Emoji)
All icons are inline `14×14px` or `16×16px` SVGs with `fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"`:
- **Brand crest (`20×20` header, `24×24` login):** `<path d="M10 1 L17 7 L14 7 L14 13 L17 13 L10 19 L3 13 L6 13 L6 7 L3 7 Z" stroke="#D4AF37" stroke-width="1.5"/>`
- **Upload / ZIP (`14×14`):** `<path d="M7 10V2M4 5l3-3 3 3M2 10v2h10v-2"/>`
- **File (`14×14`):** `<path d="M3 2h5l3 3v7H3zM8 2v3h3"/>`
- **Folder (`14×14`):** `<path d="M2 3h4l1.5 2H12v6H2z"/>`
- **Warning (`14×14`):** `<path d="M7 2L13 12H1zM7 6v3M7 10.5h.01"/>`
- **Close (`14×14`):** `<path d="M3 3l8 8M11 3l-8 8"/>`

### Component Specifications & Interactive States

#### Buttons (4 Strict Tiers)
| Tier | Selector | Default | Hover | Active | Focus-Visible | Disabled |
|---|---|---|---|---|---|---|
| **1. Gold Primary** | `button.gold, button.btn-gold` | `bg:#D4AF37; color:#0D0C0A; border:1px solid #D4AF37; font-weight:700; padding:9px 16px; min-height:36px` | `bg:#E5C558; border-color:#E5C558` | `transform:translateY(1px)` | `outline:2px solid #D4AF37; outline-offset:2px` | `opacity:0.45; cursor:not-allowed; pointer-events:none` |
| **2. Obsidian Secondary** | `button` (default) | `bg:#242019; color:#F4EFE6; border:1px solid #524B3E; font-weight:600; padding:8px 14px; min-height:36px` | `bg:#2E2920; border-color:#857A66` | `transform:translateY(1px)` | `outline:2px solid #D4AF37; outline-offset:2px` | `opacity:0.45; cursor:not-allowed` |
| **3. Ghost** | `button.ghost` | `bg:transparent; color:#B3AA9B; border:1px solid transparent; font-weight:600; padding:7px 12px; min-height:36px` | `color:#F4EFE6; bg:rgba(244,239,230,0.06); border-color:#2E2A22` | `transform:translateY(1px)` | `outline:2px solid #D4AF37; outline-offset:2px` | `opacity:0.4; cursor:not-allowed` |
| **4. Outlined Danger** | `button.danger` | `bg:transparent; color:#F2786D; border:1px solid #6E2D28; font-weight:600; padding:8px 14px; min-height:36px` | `bg:#E55B50; color:#0D0C0A; border-color:#E55B50` | `transform:translateY(1px)` | `outline:2px solid #E55B50; outline-offset:2px` | `opacity:0.4; cursor:not-allowed` |
| **Compact modifier** | `button.small` | `padding:5px 10px; font-size:12.5px; min-height:30px` (promoted to `min-height:44px` on `<=640px`) | Inherits tier | Inherits tier | Inherits tier | Inherits tier |

#### Inputs, Selects, Textareas & Checkboxes
- **Default:** `background:#11100D; color:#F4EFE6; border:1px solid #524B3E; border-radius:4px; padding:9px 11px; font-size:14px` (`16px` at `<= 640px`). Placeholder: `#8C8375`.
- **Hover:** `border-color:#857A66`.
- **Focus:** `border-color:#D4AF37; box-shadow:0 0 0 3px rgba(212,175,55,0.16); outline:none`.
- **Disabled / Read-only:** `background:#161411; color:#8C8375; border-color:#2E2A22; cursor:not-allowed`.
- **Invalid / Error (`.is-invalid`):** `border-color:#E55B50; box-shadow:0 0 0 3px rgba(229,91,80,0.16)` with adjacent `<div class="field-err">` (`12px`, `#F2786D`, `margin-top:4px`).
- **Width scoping:** `width:100%` applies inside `.card`, `#loginScreen`, `.modal-card`, `#sidePanel`, `.field` — NEVER on `.toolbar select` (`width:auto; min-width:128px`).
- **Password Show/Hide (`.pw-wrap`):** `position:relative;` input has `padding-right:68px; min-height:42px` (`46px` mobile); toggle button inside has `position:absolute; right:5px; top:50%; transform:translateY(-50%); min-height:32px` (`36px` mobile, never taller than the input).

#### Tables, Pills, Cards, Modals & Toasts
- **Tables:** Always inside `<div class="table-wrap">` (`overflow-x:auto`). `th`: `11px` uppercase `#B3AA9B`, `bg:#1A1713`, `border-bottom:1px solid #3D372C`, `padding:9px 10px`. `td`: `padding:10px`, `border-bottom:1px solid #26221B`. Hover: `rgba(244,239,230,0.03)`. Selected row (`.selected-row`): `rgba(212,175,55,0.12)` with `box-shadow: inset 3px 0 0 #D4AF37`.
- **Pills (`.pill`):** `2px` radius, `11px` mono uppercase, `padding:2px 7px`. Variants:
  - `.ok`: `color:#4CC38A; border-color:rgba(76,195,138,0.4); bg:rgba(76,195,138,0.10)`.
  - `.run`: `color:#56B4C8; border-color:rgba(86,180,200,0.4); bg:rgba(86,180,200,0.10)` + `6px` pulsing dot.
  - `.warn`: `color:#D96B43; border-color:rgba(217,107,67,0.45); bg:rgba(217,107,67,0.12)`.
  - `.ochre`: `color:#C89B54; border-color:rgba(200,155,84,0.45); bg:rgba(200,155,84,0.12)`.
  - `.fail`: `color:#F2786D; border-color:rgba(229,91,80,0.4); bg:rgba(229,91,80,0.10)`.
  - `.gold`: `color:#D4AF37; border-color:rgba(212,175,55,0.45); bg:rgba(212,175,55,0.12)`.
- **Modals (`#memberModal`, `#zipModal`):** Fixed overlay (`rgba(0,0,0,0.62)`, `z-index:45`), card `max-width:680px` (`520px` for ZIP modal), `bg:#161411`, `border:1px solid #524B3E`, `border-radius:4px`, sticky header + scrollable body (`max-height:76vh`) + sticky footer. Closes on scrim click or `Esc`.
- **Toast (`#status`):** `bg:#1F1C17`, `border:1px solid #524B3E` (`#4CC38A` `.ok`, `#E55B50` `.err`, `#C89B54` `.warn`), `padding:10px 14px`, `border-radius:4px`, `box-shadow:0 12px 32px rgba(0,0,0,0.68)`, `max-width:min(480px, calc(100vw - 32px))`.

### Empty, Loading & Error States Matrix (Every Screen)

| Screen | Loading State | Empty State | Error State |
|---|---|---|---|
| **Login** | Submit button disabled, label `Signing in…`, input disabled. | Initial token input focused, no error text. | Inline `#F2786D` message below input: `Wrong token — try again.` or `Cannot reach server — check connection.` |
| **Graph** | Centered mono caption inside canvas well: `Loading workspace graph…` | `Main Brain` node visible + anchored `#graphEmptyCard` (`No teams wired yet` + `Create first team` gold button + `+ Add Team node` secondary button). | Inline callout bar above canvas (`#E55B50` border): `Could not load graph: <reason>` + `Retry` secondary button. |
| **Teams** | 2 muted placeholder bar rows (`height:76px; bg:#1F1C17; border:1px solid #2E2A22`). | Centered card: `No teams configured yet.` + subtext `Create a team to assign roles, models, and charters.` + `+ New team` gold button. | Error callout card with `Retry` button; inline modal error keeps modal open so inputs are never lost. |
| **Models** | Main Brain card displays `Loading model configuration…`; table displays `Loading member models…`. | Member models table: `No team members configured yet — create a team in Teams to assign models.` | Save failure shows error toast + inline `#F2786D` message above Save button; invalid `auth_ref` (e.g. `sk-`) flags inline before submit. |
| **Files** | File tree shows `Loading files…`; opening a file disables textarea and shows `Opening <path>…` in header. | File tree: `No files under files/ yet — create a file or import a ZIP.` Editor: `Select a file on the left to edit, or create a new charter file.` | Binary file shows non-editable preview card (`Binary file — cannot be edited as text`); API/ZIP errors show inline vermilion callout inside editor or ZIP modal with exact offending path. |
| **Runs** | History table shows `Loading run history…`; Detail panel shows `Loading run trace…` while fetching `/api/runs/<id>`. | History: `No runs yet — choose a team and enter a goal above to start a run.` Dissents tab: `No dissents — the team reached agreement.` | Failed runs display full **Human Failure Banner** inside Run Detail (plain English headline + remedy + collapsible technical error); API failure shows error banner with `Retry`. |
| **Settings** | Inputs disabled with `Loading settings…` until `/api/state` resolves; Skills list shows `Loading skills…`. | Cron table: `No scheduled jobs yet.` Skills list: `No custom skills found in airlangga/skills/.` | Per-section inline `#F2786D` error text directly under that section's Save button + error toast; unsaved values remain intact for correction. |

---

## 4. Graph Design

### Canvas Architecture & Toolbar
- **Canvas Well (`#canvasScroll`):** `background:#090807`, `background-image:radial-gradient(#2A251D 1px, transparent 1px); background-size:20px 20px;`, `border:1px solid #2E2A22; border-radius:4px; height:calc(100vh - 208px); min-height:460px; overflow:auto; position:relative; touch-action:pan-x pan-y;`.
- **Dynamic Canvas Bounds:** `#canvas` and `#edges` SVG resize dynamically on every structural render to `width = Math.max(1600, maxNodeX + 280)` and `height = Math.max(900, maxNodeY + 260)` so large multi-team graphs never clip edges or nodes.
- **Desktop Toolbar (1 clean horizontal bar with `1px` `#2E2A22` dividers):**
  1. Mode segmented toggle: `Select` | `Connect` (active segment `bg:#D4AF37; color:#0D0C0A`). When `Connect` is ON, reveals compact `#edgeKind` `<select>` (`Auto (by node types)` default + all 9 explicit edge kinds).
  2. Add cluster: `+ Add node` (secondary) + compact `#addNodeType` `<select>` (`Team`, `Member`, `Model`, `File`, `Folder`, `Tool`, `Skill`).
  3. View cluster: `−` · `100%` (click to reset 100%) · `+` · `Fit` (ghost buttons).
  4. Right-aligned Save cluster: subtle dirty status chip `Unsaved changes` (`.pill.ochre`, hidden when clean) + `Save graph` (`button.gold` when dirty, `button` secondary when clean; label `Save graph *` when dirty).
- **Connect Banner (`#connectBanner`):** Shown below toolbar when a connect source is chosen: `Connecting from <Label> (<Type>) — click a target node (edge kind: <Auto or chosen>).` + `Cancel (Esc)` ghost button.
- **Legend Bar (`#graphLegend`):** Bottom `11px` mono strip showing all 6 color swatches (`Brain #D4AF37`, `Team #D96B43`, `Member #56B4C8`, `Model #4CC38A`, `File/Folder #C89B54`, `Tool/Skill #9E9587`) + `Drag to move · Drag right port or press C to connect · Click to inspect`.

### Node Visual Specifications (All 8 Types)

Every node has `position:absolute; cursor:grab; user-select:none; touch-action:none; padding:9px 11px;`, a `3px` left semantic rail, a top eyebrow row (`10px` uppercase mono type + `12×12px` inline geometric SVG icon), bold `13px` `#F4EFE6` label (`.l`), and `11.5px` `#B3AA9B` detail line (`.d`). Each node carries a left input port (`.port.in`, `10×10px`, `left:-6px`, `top:50%`) and right output port (`.port.out`, `10×10px`, `right:-6px`, `top:50%`, `cursor:crosshair` on desktop for port-drag connect).

| Node Type | Width | Background | Border & Special Silhouette | Port Color | Detail Line Content | Special Badges |
|---|---|---|---|---|---|---|
| **`main_brain`** | `216px` | `#1C1810` | `1.5px solid #D4AF37`, `border-left:4px solid #D4AF37`, `radius:6px`, inner double-frame `box-shadow: inset 0 0 0 3px #0D0C0A, inset 0 0 0 4px rgba(212,175,55,0.35)` | `#D4AF37` | Mono: `<provider>/<model>` (e.g. `anthropic/claude-opus-4-6`) | `SOVEREIGN` micro-tag top-right |
| **`team`** | `204px` | `#1C1714` | `1px solid #524B3E`, `border-left:3px solid #D96B43`, `radius:6px` | `#D96B43` | `<template> · <Lead member / Separate>` + budget `$15` | `DRAFT` ochre badge if not yet saved to YAML |
| **`member`** | `204px` | `#181A1C` | `1px solid #524B3E`, `border-left:3px solid #56B4C8`, `radius:6px` | `#56B4C8` | `<role>` + `· <charter_file>` (when set, `#C89B54`) | `LEAD` gold badge if team lead; `UNASSIGNED` ochre badge if no incoming `has_member` edge |
| **`model`** | `208px` | `#151B18` | `1px solid #524B3E`, `border-left:3px solid #4CC38A`, `radius:6px` | `#4CC38A` | Mono: `<provider>` + `$/Mtok` (e.g. `anthropic · $3.00/M`) | Powers count tag (`×2`) if connected to >=2 brains/members |
| **`file`** | `192px` | `#1B1813` | `1px solid #524B3E`, `border-left:3px solid #C89B54`, `border-radius:4px 14px 6px 6px` (notched document corner) | `#C89B54` | Mono: `<relative path>` (e.g. `files/superagent.md`) | `CHARTER` ochre badge if target of `has_charter` |
| **`folder`** | `192px` | `#1A1712` | `1px dashed #6B5736`, `border-left:3px solid #C89B54`, `border-radius:4px 14px 6px 6px` | `#C89B54` | Mono: `<path>/` | Folder SVG icon |
| **`tool`** | `152px` | `#1A1815` | `1px dashed #524B3E`, `border-left:3px solid #9E9587`, `radius:3px`, compact padding `7px 9px` | `#9E9587` | `toolset` (single-line compact chip) | — |
| **`skill`** | `156px` | `#1A1815` | `1px dashed #6E6557`, `border-left:3px solid #B3AA9B`, `radius:3px`, compact padding `7px 9px` | `#B3AA9B` | `<skill>.yaml` | `SKILL` micro-tag |

**Node Interactive States:**
- **Hover:** `border-color:#857A66;` (ports scale `1.25×` and fill with port accent).
- **Selected:** `border-color:#D4AF37; box-shadow:0 0 0 2px rgba(212,175,55,0.32), 0 8px 22px rgba(0,0,0,0.55);` — all edges NOT touching the selected node dim to `opacity:0.22` so the selected node's wiring pops instantly.
- **Connect source (`.connect-source`):** `border:1.5px dashed #56B4C8; box-shadow:0 0 0 3px rgba(86,180,200,0.22);`.
- **Valid drop target during connect (`.connect-hover`):** `border-color:#4CC38A; box-shadow:0 0 0 2px rgba(76,195,138,0.28);`.

### Edge Visual Specifications & Auto-Inference (All 9 Kinds)

Edges connect **port-to-port** (source right edge `a.x + aw, a.y + ah/2` to target left edge `b.x, b.y + bh/2`; flips to left→right when `a` center is right of `b` center) using cubic Bezier curves `M x1,y1 C mx,y1 mx,y2 x2,y2`. Every edge renders: (1) an invisible `14px` hit `<path class="hit" stroke="transparent" stroke-width="14">`, (2) the visible styled `<path>` with color-matched `8×8` `<marker>` arrowhead, and (3) a centered `<rect rx="3" fill="#0D0C0A" stroke="#2E2A22">` halo pill behind `10px` `#B3AA9B` label text. Clicking an edge highlights it (`stroke-width + 1.2`, gold halo border `#D4AF37`) and opens the Edge Inspector.

| Edge Kind | Human Label | Stroke Hex | Width | Dasharray | Marker ID | Canonical `(From → To)` | Maps to `airlangga.yaml` |
|---|---|---|---|---|---|---|---|
| `assigns` | `assigns` | `#D4AF37` | `2.2px` | solid | `arr-gold` | `main_brain → team` | Confirms team under `config.teams` |
| `powers` | `powers` | `#D4AF37` | `2.2px` | solid | `arr-gold` | `model → main_brain`, `model → member` | Sets target's `provider`, `model`, `endpoint`, `auth_ref`, `wire_format`, `capabilities`, `cost_per_mtok_usd` |
| `has_member` | `member` | `#D96B43` | `1.8px` | solid | `arr-terra` | `team → member` | Assigns/moves `member` into `team.members` (creates member in YAML if newly added) |
| `uses_model` | `uses model` | `#4CC38A` | `1.8px` | solid | `arr-jade` | `member → model`, `main_brain → model` | Same model fields written to source `member` or `main_brain` |
| `has_charter` | `charter` | `#C89B54` | `1.8px` | solid | `arr-ochre` | `member → file` | Sets `member.charter_file` (replaces previous charter if changed) |
| `has_file` | `attaches file` | `#C89B54` | `1.8px` | `2 4` | `arr-ochre` | `member → file`, `member → folder` | Adds path to `member.attached_files` |
| `uses_tool` | `tool` | `#857A66` | `1.5px` | `4 3` | `arr-pewter` | `member → tool` | Adds toolset name to `member.toolsets` |
| `uses_skill` | `skill` | `#B3AA9B` | `1.5px` | `4 3` | `arr-pewter` | `member → skill` | Adds skill name (without `.yaml`) to `member.skills` |
| `depends_on` | `depends on` | `#56B4C8` | `1.6px` | `5 4` | `arr-cyan` | `member → member`, `team → team` | Stored in `airlangga-graph.json` (ordering/dependency link) |

**Auto-Inference Rule (when `#edgeKind` is `auto`):**
- `main_brain → team` ⇒ `assigns`
- `team → member` ⇒ `has_member`
- `model → main_brain` or `model → member` ⇒ `powers`
- `member → model` or `main_brain → model` ⇒ `uses_model`
- `member → file` ⇒ `has_charter` if member has no existing `has_charter` edge, otherwise `has_file`
- `member → folder` ⇒ `has_file`
- `member → tool` ⇒ `uses_tool`
- `member → skill` ⇒ `uses_skill`
- `member → member` or `team → team` ⇒ `depends_on`
- Reverse clicks (e.g. `file → member` or `tool → member`) automatically flip `(from, to)` to the canonical direction so users never create backwards broken wires. Self-loops (`from === to`) and exact duplicate `(from, to, kind)` edges are blocked with a toast.

### Graph Interactions
- **Drag (Zero DOM Rebuild + Zoom-Safe):**
  - On `pointerdown` on `.node` (ignoring `.port.out` when starting a port-drag): record `startClientX = ev.clientX`, `startClientY = ev.clientY`, `origX = n.x`, `origY = n.y`, `dragged = false`.
  - On `pointermove`: compute `dx = (ev.clientX - startClientX) / zoom`, `dy = (ev.clientY - startClientY) / zoom`. Once `Math.hypot(ev.clientX - startClientX, ev.clientY - startClientY) >= 4`, set `dragged = true`, `n.x = Math.max(16, Math.round(origX + dx))`, `n.y = Math.max(16, Math.round(origY + dy))`, mutate ONLY `div.style.left`, `div.style.top`, and `updateEdgesFor(n.id)` (never `renderGraph()`).
  - On `pointerup`: if `dragged`, set `suppressNextClick = true` (cleared on next microtask), `setDirty(true)`, and expand `#canvas`/`#edges` bounds if needed. Clicking without moving `>= 4px` selects the node normally.
- **Desktop Port-Drag Connect:** `pointerdown` on `.port.out` draws a live dashed `#56B4C8` SVG `<path id="dragWire">` to cursor coordinates `(clientX - canvasRect.left) / zoom`, highlights hovered target `.node` with `.connect-hover`, and creates the auto-inferred edge on `pointerup` over another node.
- **Viewport-Aware `+ Add node`:** Places new nodes inside the visible center of `#canvasScroll` (`x = Math.round((sc.scrollLeft + 140) / zoom) + (count % 5) * 28`, `y = Math.round((sc.scrollTop + 100) / zoom) + (count % 5) * 28`), initializes complete type-appropriate `data` defaults, selects the new node, marks dirty, and opens the inspector (bottom sheet on mobile).
- **Keyboard Shortcuts (active when Graph tab is visible and focus is not inside `input`/`select`/`textarea`):**
  - `Esc`: cancel Connect mode → or close inspector.
  - `C`: toggle Select / Connect mode.
  - `F`: Fit graph to viewport.
  - `Delete` / `Backspace`: delete selected node/edge (with confirmation for config-backed team/member).
  - `Cmd/Ctrl + S`: Save graph immediately.

### Side-Panel Inspector (`#sidePanel`, `300px` desktop right rail / slide-up sheet `<= 820px`)
Header (sticky): Type micro-pill + live node label + `×` close button (`44×44px` on mobile). All edits live-bind to in-memory graph state, update node DOM + edge paths in place, and mark `Save graph *` dirty.

| Selected Item | Inspector Fields | Contextual Actions |
|---|---|---|
| **`main_brain`** | Label (read-only `Main Brain`), Provider preset `<select>`, Model (`input` + datalist), Endpoint / `base_url`, Auth ref, Wire format, Cost `$/Mtok`. | `Edit full settings in Models →` link. (Main Brain cannot be deleted.) |
| **`team`** | Team name (slug, editable if draft / disabled once saved to YAML), Template (`research` / `code-review` / `content` / `blank`), Team brain mode (`Lead member` / `Separate brain`), Lead member `<select>` (populated from connected members), Goal, Team budget (USD). | `Run team →` ghost button; `Delete team` outlined danger (confirms YAML deletion if config-backed, or removes draft). |
| **`member`** | Member ID (slug), Role, Charter file `<select>` (populated from `S.files`; changing it auto-syncs the `has_charter` graph edge!), Attached files checkboxes, Toolsets checkboxes, Skills checkboxes (from `/api/skills`), Approval (`Smart` / `Approve all` / `Off`), Budget (USD). | `Edit model & fallbacks →` (opens `#memberModal`); `Delete member` outlined danger (confirms YAML deletion if config-backed). Note banner if `UNASSIGNED`: `Connect a Team → this Member to save it to airlangga.yaml.` |
| **`model`** | Label (auto `<provider>/<model>`), Provider preset `<select>` (auto-fills defaults), Model (`input` + datalist), Endpoint / `base_url`, Wire format, Auth ref, Cost `$/Mtok`, Capabilities checkboxes (`tool_calling`, `structured_json`, `long_context`, `vision`). | `Remove from graph` outlined danger (clears model node from canvas). |
| **`file` / `folder`** | Existing file/folder `<select>` from `S.files` (or custom path input under `files/`), Label. | `Open in Files editor →` ghost button (jumps to Files and opens this file, or creates it if new); `Remove from graph` outlined danger (helper text: `Removes node from graph only — the file on disk is kept.`). |
| **`tool` / `skill`** | Toolset `<select>` (`S.toolsets`) or Skill `<select>` (`/api/skills`). | `Remove from graph` outlined danger. |
| **Edge** | Source label → Target label (human names, never raw `member:research-01:researcher` IDs), Edge kind `<select>` (human labels). | `Delete connection` outlined danger. |

**Connections List (shown on every node inspector):** `Connections (N)` section listing every incoming (`←`) and outgoing (`→`) link with clickable target name (jumps selection to that node), human edge kind (`· uses model`), and a `×` disconnect button (`44×44px` on mobile).

### Empty State (Brand-New User with 0 Teams)
When `Object.keys(S.config.teams).length === 0`, the canvas renders the `Main Brain` node at `(60, 120)` plus a crisp anchored onboarding card (`#graphEmptyCard`, `position:absolute; left:340px; top:96px; width:340px;` on desktop, centered below Main Brain on mobile; `bg:#161411; border:1px solid #3D372C; border-left:3px solid #D4AF37; border-radius:4px; padding:18px`):
- Title: `Build your first Agentic Team`
- Body: `Connect a Team to Main Brain, wire each member to a model and charter file (like superagent.md), then launch a run.`
- Actions: `Create first team` (`.btn-gold`, opens Teams tab with Create Team drawer expanded & `Seed starter members` checked) + `+ Add Team node` (secondary, inserts a `team` node at `(380, 120)` already wired from `main_brain` via `assigns` and opens its inspector).

### Graph ↔ `airlangga.yaml` Persistence & Reconciliation Rules (All Traps Closed)
1. **Shared model deduplication in `default_graph` (`web_ui.py`):** Group identical `(provider, model, endpoint, auth_ref)` tuples into a single `model:<slug>` node (e.g., `model:anthropic-claude-sonnet-4-5`) connected by `uses_model` from every member sharing that endpoint, and include Main Brain's model node connected via `powers` (`model → main_brain`). Existing saved node positions in `airlangga-graph.json` are always preserved.
2. **Graph-added nodes ALWAYS persist (`_sync_graph` + `apply_graph_to_config`):**
   - `_sync_graph` NEVER drops any node saved in `airlangga-graph.json` (already fixed — keep intact).
   - On `POST /api/graph`, `apply_graph_to_config(graph)` performs full bidirectional reconciliation:
     - **Main Brain:** Updates `config.main_brain` from `main_brain` node data AND any connected `model` node (`powers` → `main_brain` or `main_brain` → `uses_model`).
     - **Teams:** For every `team` node, slugifies its label (`team_name`). If not in `config.teams`, creates a new `TeamConfig(template=..., goal=..., team_brain_mode=..., team_budget=...)`. If already in `config.teams`, updates `template`, `goal`, `team_brain_mode`, `lead_member`, `team_budget`. Rewrites provisional `team:<ts>` ID to canonical `team:<team_name>` (updating edge endpoints) and returns the canonicalized graph!
     - **Members:** For every `member` node with an incoming `has_member` edge from a `team` node: creates a new `MemberConfig` (using connected `model` node or safe `mock` defaults) if new, or moves/updates the existing member in that team (`role`, `approval`, `budget`). Rewrites provisional `member:<ts>` ID to canonical `member:<team_name>:<member_id>`. Disconnected (`UNASSIGNED`) member nodes stay safely in `airlangga-graph.json` without failing validation.
     - **Rebuilt Member Wiring (fixes Edge Resurrection Trap):** For every config-backed `member` node present in `graph["nodes"]`, `apply_graph_to_config` computes its `charter_file`, `attached_files`, `toolsets`, and `skills` authoritatively from the graph's current outgoing `has_charter`, `has_file`, `uses_tool`, and `uses_skill` edges (merged with inspector checkbox edits), and applies any connected `uses_model` OR incoming `powers` model node. Therefore, deleting a `has_charter`, `has_file`, `uses_tool`, or `uses_skill` edge and clicking `Save graph` removes it from `airlangga.yaml`, so `_sync_graph` never resurrects it!
3. **Config-backed Node Deletion Rule:** When the user clicks `Delete team` or `Delete member` in the inspector for a node whose ID exists in `S.config.teams`, the UI confirms (`"Delete member '<id>' from team '<team>' and airlangga.yaml?"`) and calls `DELETE /api/teams/<team>` or `DELETE /api/teams/<team>/members/<id>` (which deletes from `airlangga.yaml` and runs `_prune_graph_nodes`), preventing resurrection on reload. Deleting `file`/`folder`/`model`/`tool`/`skill` or draft nodes deletes only from the in-memory graph until `Save graph`.

---

## 5. Files + ZIP Import

### File Manager Layout & Editing Flow
- **Layout:** Desktop `grid-template-columns: 280px minmax(0, 1fr); gap: 12px;` (`.files-split`). Mobile `<= 820px`: stacked single column with a collapsible `<details open id="fileTreeDrawer">` (`Files & folders (N)`) above the editor so the editor gets full screen width.
- **Left Sidebar (`Files & folders` card):**
  - Header row: `Files & folders` + `Import ZIP` secondary button (with 14px upload SVG icon).
  - Quick-create strip: `<input id="newFilePath" placeholder="personas/superagent.md">` + `+ File` (secondary) + `+ Folder` (ghost).
  - File tree (`#fileTree`, also acts as a drag-and-drop zone for `.zip` files with a `2px dashed #D4AF37` overlay `Drop .zip archive to import into files/`):
    - Displays relative path hierarchy with `12px` per nesting depth level.
    - **Folder rows:** Folder SVG icon + `<name>/` in `#B3AA9B`, muted `folder` caption, plus subtle `×` delete button (shown on hover/focus; calls `DELETE /api/files?path=<dir>` and surfaces `"Folder is not empty; delete its files first."` if non-empty). Clicking a folder row prefills `#newFilePath` with `<folder>/` and focuses the input — NEVER calls `openFile()`.
    - **File rows:** File SVG icon + mono path in `#56B4C8` (`#F4EFE6` when active), `CHARTER` ochre micro-pill if referenced as any member's `charter_file`, and human-formatted size (`480 B`, `2.4 KB`). Clicking opens the file (if current file has unsaved changes, prompts `confirm("Discard unsaved changes to <path>?")`).
- **Right Editor Panel (`Editor` card):**
  - **Header bar:** Mono file path (e.g., `files/superagent.md`), inline `Unsaved *` ochre pill when dirty, and compact action group:
    - `Attach as charter…` (ghost button; opens compact inline popover with `<select>` of all `<team> / <member>` pairs + `Attach` secondary button → immediately `PUT /api/teams/<team>/members/<member>` with `{ charter_file: editingFile }` + toast `"Attached superagent.md as charter for research-01 / researcher."`).
    - `Add to graph` (ghost button; adds/focuses `file:<editingFile>` node on the Graph canvas and switches to Graph tab).
    - `Save file` (`button.gold` when dirty, secondary when clean; also bound to `Cmd/Ctrl + S`).
    - `Delete` (outlined danger `button.danger small`).
  - **Editor textarea (`#fileEditor`):** Monospace `13px` (`16px` mobile), `min-height: 420px` (`52vh` mobile), `tab-size: 2`, `#11100D` well.
  - **Footer meta bar:** `11.5px` mono `#8C8375`: `<lines> lines · <chars> chars · <formatted size> · UTF-8 · Cmd/Ctrl+S to save`.
  - **Binary file handling:** If `GET /api/files?path=...` encounters non-UTF-8 bytes, backend returns `400 {"error": "Binary file cannot be edited as text.", "binary": true, "size": <bytes>}` instead of crashing with `500`. Editor displays a calm card: `<filename> is a binary file (<size>) and cannot be edited as text. You can still attach it to a team member or delete it.` + `Delete file` outlined danger button.

### ZIP Import — Step-by-Step UX Flow & Exact UI Strings

1. **Step 1 — Open Modal (`#zipModal`):**
   - User clicks `Import ZIP` in the Files sidebar OR drops a `.zip` file onto `#fileTree`.
   - Modal header: `Import ZIP into files/` + `×` close button.
   - **Dropzone (`#zipDropzone`):** `border: 1.5px dashed #524B3E; bg: #11100D; border-radius: 4px; padding: 24px 16px; text-align: center; cursor: pointer;` (hover/dragover: `border-color: #D4AF37; bg: rgba(212,175,55,0.06)`).
     - Empty copy: Upload SVG icon + `Choose a .zip file or drop it here` + subtext `Max 10 MB upload · Max 25 MB extracted · Max 200 files · Unsafe paths and credentials are blocked`.
     - File selected copy: Mono `<filename>` + formatted size (`42.8 KB`) + `Change file` ghost link.
     - Client-side immediate validation before upload:
       - Not `.zip`: inline error `#F2786D`: `Only .zip archives are supported.` (`Upload & extract` stays disabled).
       - `> 10 MB`: inline error `#F2786D`: `Archive is <X> MB — maximum upload size is 10 MB.` (`Upload & extract` stays disabled).
   - **Destination folder input (`#zipDest`):** Label `Extract into folder (optional)`, placeholder `packs/superagent (leave empty for files/ root)`.
   - **Collision policy (`#zipOverwrite`):** Label `If a file already exists`, `<select>`:
     - `0` (default): `Skip existing files (safe)`
     - `1`: `Overwrite existing files`
   - **Footer:** `Upload & extract` (`button.gold`, disabled until valid `.zip` chosen) + `Cancel` (`button.ghost`).

2. **Step 2 — Uploading & Extracting:**
   - Button switches to `Extracting…` (disabled); `Cancel` disabled; a `2px` `#D4AF37` progress bar animates along the bottom of the modal header.
   - Browser sends raw `File` via `fetch("/api/files/import-zip?dest=" + encodeURIComponent(dest) + "&overwrite=" + ow, { method: "POST", headers: { "Content-Type": "application/zip", "X-Airlangga-Token": token(), "X-Filename": file.name }, body: file })`.

3. **Step 3A — Success State (HTTP `200`):**
   - Replaces dropzone with a jade summary box (`border: 1px solid rgba(76,195,138,0.45); bg: rgba(76,195,138,0.08); padding: 12px; border-radius: 4px`):
     - Headline: `Extracted <N> file(s) (<formatted total_bytes>) into files/<dest or root>`
     - Sub-line (only if applicable): `Skipped <M> existing file(s)` · `Ignored <K> macOS/system metadata entries`
   - Scrollable list (`max-height: 220px; overflow-y: auto`) of extracted files: each row shows mono relative path, formatted size, and an `Open` ghost button (closes modal and opens that file in `#fileEditor`).
   - Calls `loadState()` silently to refresh `#fileTree` and charter dropdowns across Graph & Teams.
   - Footer: `Import another ZIP` (secondary) + `Done` (`button.gold`).

4. **Step 3B — Rejection / Error State (HTTP `400` / `413` / `415`):**
   - Displays a vermilion callout box (`border: 1px solid #E55B50; bg: rgba(229,91,80,0.10); padding: 12px; border-radius: 4px`):
     - Headline: `Import blocked — no files were written`
     - Human reason + mono offending entry (if returned):
       - `path_traversal`: `Unsafe path blocked (directory traversal or absolute path):` `<code>../etc/passwd</code>`
       - `credential_path`: `Restricted credential path blocked:` `<code>bundle/.env</code>`
       - `symlink_entry`: `Symbolic links inside ZIP archives are not allowed:` `<code>link-to-key</code>`
       - `not_a_zip`: `This file is not a valid ZIP archive.`
       - `zip_too_large`: `ZIP upload exceeds the 10 MB limit.`
       - `uncompressed_too_large`: `Extracted content exceeds the 25 MB safety limit.`
       - `too_many_files`: `Archive contains more than 200 files (limit: 200).`
       - `zip_bomb_ratio`: `Suspicious compression ratio blocked (>100:1) on entry:` `<code>bomb.txt</code>`
       - `encrypted_entry`: `Password-protected ZIP entries are not supported:` `<code>secret.md</code>`
   - Footer: `Choose another file` (secondary, resets error & opens file picker) + `Close` (ghost).

### Backend Endpoint Contract (`airlangga/web_ui.py`)
- **Endpoint:** `POST /api/files/import-zip`
- **Auth:** Requires `_require_auth()` (`401 {"error": "unauthorized: set the X-Airlangga-Token header"}`).
- **Query Parameters:**
  - `dest` (string, optional, default `""`): relative subfolder inside `files/`. Stripped of leading/trailing `/`; if non-empty, validated with `self.store.resolve_file(dest)` (blocks traversal & credential folder names).
  - `overwrite` (`"0"` or `"1"`, optional, default `"0"`).
- **Hard Security Constants (module-level in `web_ui.py`):**
  - `ZIP_MAX_UPLOAD_BYTES = 10 * 1024 * 1024` (10 MB)
  - `ZIP_MAX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024` (25 MB)
  - `ZIP_MAX_FILES = 200`
  - `ZIP_MAX_RATIO = 100` (checked when `info.file_size > 1024 * 1024` and `info.compress_size > 0`)
- **Atomic Validation Sequence (ALL checks run before ANY disk write):**
  1. Read `Content-Length` header. If `> ZIP_MAX_UPLOAD_BYTES`, immediately return `413 {"error": "ZIP file exceeds the 10 MB upload limit.", "code": "zip_too_large", "max_bytes": 10485760}` without reading the full body.
  2. Read `length` bytes (`raw`). Verify `len(raw) >= 4` and `raw[:4] in (b"PK\x03\x04", b"PK\x05\x06")` and open `zipfile.ZipFile(io.BytesIO(raw))`. On `zipfile.BadZipFile` or bad magic, return `415 {"error": "File is not a valid ZIP archive.", "code": "not_a_zip"}`.
  3. Iterate `zf.infolist()`:
     - Normalize `raw_name = info.filename.replace("\\", "/")`.
     - Skip pure OS metadata (`raw_name.startswith("__MACOSX/")`, `raw_name == "__MACOSX"`, basename in `(".DS_Store", "Thumbs.db")`) and increment `ignored_metadata`.
     - Reject encrypted entries (`info.flag_bits & 0x1`) → `400` (`code: "encrypted_entry"`).
     - Reject symlinks (`((info.external_attr >> 16) & 0o170000) == 0o120000`) → `400` (`code: "symlink_entry"`).
     - Reject absolute paths (`raw_name.startswith("/")`), Windows drive letters (`re.match(r"^[A-Za-z]:", raw_name)`), null bytes, or any `".."` path component → `400` (`code: "path_traversal"`).
     - Skip directory-only entries (`info.is_dir()`) after verifying their path is non-traversal and non-credential.
     - Construct `rel = f"{dest}/{clean_name}" if dest else clean_name`.
     - Check `is_write_denied(rel)` → `400` (`code: "credential_path"`).
     - Check `self.store.resolve_file(rel)` stays strictly inside `self.files_root` → `400` (`code: "path_traversal"`).
     - Increment `file_count`; if `> ZIP_MAX_FILES` → `400` (`code: "too_many_files"`).
     - Accumulate `declared_total += info.file_size`; if `> ZIP_MAX_UNCOMPRESSED_BYTES` → `413` (`code: "uncompressed_too_large"`).
     - If `info.file_size > 1_048_576` and `(info.compress_size == 0 or info.file_size / info.compress_size > ZIP_MAX_RATIO)` → `400` (`code: "zip_bomb_ratio"`).
  4. **Phase 2 (Extract):** Under `self._lock`, extract each validated entry in chunks (verifying actual decompressed bytes never exceed `ZIP_MAX_UNCOMPRESSED_BYTES`). If `target.exists()` and not `overwrite`, append `rel` to `skipped`; else write bytes and append `{"path": rel, "size": len(data)}` to `extracted`.
- **Success Response (`200 OK`):**
  ```json
  {
    "ok": true,
    "dest": "packs/superagent",
    "extracted": [{"path": "packs/superagent/superagent.md", "size": 612}],
    "skipped": [],
    "ignored_metadata": 1,
    "total_bytes": 612
  }
  ```

---

## 6. Teams / Models / Runs / Settings

### Tab 2: Teams (`#tab-teams`) — Fast Team Formation & Concrete SUPERAGENT Flow
- **Fastest Path from Idea to Running Team (<60 seconds):**
  1. Click `+ New team` (`button.gold` in tab header) → expands `#createTeamCard`.
  2. Fill `Name` (e.g. `sec-audit-01`), `Template` (`Research` / `Code review` / `Content` / `Blank`), `Team brain mode` (`Lead member` / `Separate brain`), `Team budget (USD)` (default `15`), `Goal`, and keep **`Seed starter members from template`** checked (`#newTeamSeed`, checked by default).
  3. Click `Create team` (`button.gold`). When `seed_members: true`, `POST /api/teams` automatically creates the template's default roster (e.g., `research`: `researcher`, `fact_checker`, `writer`; `code-review`: `coder`, `reviewer`, `tester`; `content`: `drafter`, `editor`, `fact_checker`) with sensible `toolsets`, `approval: "smart"`, and `mock` or Main Brain model defaults — immediately runnable!
  4. Click `Edit` on any member to pick its model, charter file, toolsets, skills, fallbacks, and budget → click `Run team →` right from the team card header.
- **Team Card Layout:**
  - Header: Team name (`16px` bold) + Template pill + Mode pill (`Lead member` / `Separate brain`) + `Lead: <id>` gold micro-pill + `$15.00 cap` mono tag. Right controls: `Run team →` (ghost), `+ Add member` (secondary), `Edit team` (ghost), `Delete` (outlined danger).
  - Inline `Edit team` form (toggled in-place): edits `Goal`, `Template`, `Team brain mode`, `Lead member` `<select>`, and `Team budget (USD)`.
  - Roster Table (`.table-wrap.stacked`): Columns `Member` (with `LEAD` gold pill on lead), `Role`, `Model` (mono `provider/model`), `Tools` (`.tag` chips), `Skills` (`.tag` chips), `Charter` (clickable mono link that opens that file in Files tab, or `—`), `Budget` (tabular USD right-aligned), Actions (`Edit` secondary small, `Remove` outlined danger small).
- **Upgraded Single Member Modal (`#memberModal` — closes the `skills: []` wipe bug):**
  - Preserves ALL existing fields on `PUT` (`skills`, `attached_files`, `capabilities`, `cost_per_mtok_usd`, `context_limit`, `fallback`, `routing_policy`).
  - Organized into 3 clear subsections inside the scrollable modal body:
    1. **Identity, Charter & Policy:** `Member ID`, `Role`, `Charter file` (`<select>` from `S.files` + inline `Create charter in Files →` link), `Attached files` (multi-checkbox list of files under `files/`), `Approval mode` (`Smart — ask on risky actions`, `Approve all — ask every tool`, `Off — disposable host only`), `Member budget (USD)`.
    2. **Model & Endpoint:** `Provider` preset `<select>` (includes saved custom providers; changing auto-fills endpoint, auth_ref, wire_format, capabilities, model suggestions), `Model` (`input` + `<datalist>`), `Wire format` (`OpenAI Chat`, `Anthropic Messages`, `Google Gemini`, `Mock`), `Endpoint / base_url`, `Auth ref` (with inline warning if value matches `/^(sk-|ghp_|xox|AIza)/i`: `"Do not paste raw API keys here — use env:VAR_NAME."`), `Cost ($/Mtok)`, `Context limit`, `Capabilities` checkboxes (`tool_calling`, `structured_json`, `long_context`, `vision`).
    3. **Tools, Skills & Capability-Gated Fallbacks:** `Toolsets` checkboxes (`S.toolsets`), `Skills` checkboxes (populated from `GET /api/skills`, pre-checking `m.skills`), `Required capabilities` (`routing_policy.require` checkboxes), `Routing preference` (`Cheapest above quality floor` | `Local first`), and **Fallback Chain Builder**:
       - Ordered list of fallback cards (`1.`, `2.`, …), each with Provider, Model, Endpoint, Auth ref, Capabilities checkboxes, Up/Down reorder buttons, `×` Remove button, and a **live Capability Gate Pill**:
         - All required caps present → `.pill.ok` `ELIGIBLE`
         - Missing >=1 required cap → `.pill.warn` `WILL SKIP — missing <cap>` (explaining Airlangga's router never silently downgrades).
       - `+ Add fallback` secondary button appends a new fallback row.
- **Concrete SUPERAGENT Persona End-to-End Flow:**
  1. User opens **Files** tab → edits seeded `superagent.md` (or types `personas/superagent.md` → clicks `+ File`, pastes instructions, presses `Cmd/Ctrl + S`).
  2. User attaches it via **any** of 3 equivalent paths:
     - **Fastest (in Files):** clicks `Attach as charter…` in the editor header → picks `research-01 / researcher` → clicks `Attach`.
     - **In Teams:** clicks `Edit` on `researcher` → selects `superagent.md` in `Charter file` → clicks `Save member`.
     - **In Graph:** clicks `+ Add node` (`File`, path `superagent.md`) → connects `researcher` → `superagent.md` (`Charter`) → clicks `Save graph`.
  3. **Backend Runtime Wiring (`airlangga/brain.py` & `airlangga/team.py`):** `member_prompt(member, contract_goal, files_root=...)` resolves `member.charter_file` safely inside `files/` (rejecting traversal/credentials, truncating cleanly at 16,384 bytes with note if oversized) and prepends:
     ```text
     --- PERSONA CHARTER (superagent.md) ---
     <contents of files/superagent.md>
     --- END CHARTER ---
     ```
     plus lists any `member.attached_files` paths available to read, and `TeamRuntime.activate()` records `charter_file` in the member activation event payload so the **Runs** timeline visibly confirms `Charter active: superagent.md`.

### Tab 3: Models (`#tab-models`)
- **Card 1 — Main Brain (`.card.hero`, `3px solid #D4AF37` left rail):**
  - 2-row form grid: `Provider` preset `<select>` (all 8 built-ins + any user custom providers), `Model` (`input` + datalist), `Wire format`, `Endpoint / base_url`, `Auth ref` (with raw-key paste guard), `Cost ($/Mtok)`, `Run budget (USD)`, and `Capabilities` checkboxes.
  - Primary Gold CTA: `Save Main Brain`.
- **Card 2 — Custom `base_url` Providers (collapsible `+ Add custom provider` drawer):**
  - Shows any saved custom endpoints (from `.airlangga-ui.json` → `custom_providers`) with `Remove` outlined danger button.
  - Clicking `+ Add custom provider` reveals a compact form: `Provider slug` (e.g. `litellm-corp` or `vllm-gpu`), `Display label` (`LiteLLM Proxy`), `Wire format` (`OpenAI Chat` / `Anthropic Messages` / `Google Gemini`), `Base URL` (`https://llm.internal/v1`), `Auth ref` (`env:LITELLM_API_KEY` or `none`), `Default models (comma-separated)`, `Capabilities` checkboxes → `Save custom provider` (secondary button, saves to `settings.custom_providers` via `PUT /api/settings`, and backend merges them into `S.providers` so they immediately appear in every provider dropdown in Graph, Teams, and Models!).
  - Inline tip when no custom providers exist: `Use any OpenAI-compatible, Anthropic, or Gemini-compatible base_url (vLLM, LiteLLM, Groq, Together, Ollama). Credentials stay in env:VAR_NAME — never stored in config.`
- **Card 3 — Member Models & Routing (`.table-wrap.stacked`):**
  - Columns: `Team`, `Member`, `Provider / Model` (mono), `Endpoint` (mono, truncated at 36 chars with full `title`), `Auth ref` (mono), `Capabilities` (`.tag` chips), `$/Mtok` (tabular right-aligned), `Fallbacks` (shows `—`, or `.pill.ok` `2 eligible`, or `.pill.warn` `1 eligible · 1 skipped` with hover list), `Actions` (`Edit` ghost button — opens `#memberModal` **directly in place** without switching away from the Models tab!).
- **Card 4 — Provider Reference (`<details>` collapsed by default):**
  - Summary: `Provider reference (8 built-in presets)` showing Anthropic, OpenAI, DeepSeek, OpenRouter, Gemini, Ollama, Custom, Mock with humanized wire format (`OpenAI Chat`, `Anthropic Messages`, `Google Gemini`, `Mock`), Endpoint, Auth ref, and Default models.

### Tab 5: Runs (`#tab-runs`)
- **Card 1 — Launch Bar:**
  - Single responsive row: `Team` `<select>` (`180px`), `Goal` `<input>` (`flex:1`, placeholder `Produce a sourced brief on …`), `Provider mode` `<select>` (`Mock — offline demo, no key` | `Real providers — uses API keys`), and `Run team` (`button.gold`).
  - If no teams exist, `Run team` is disabled with muted inline prompt `Create a team in Teams first.`
- **Card 2 — Run History (`.table-wrap.stacked`):**
  - Columns: `Run` (mono), `Status` (`.pill.run` with pulsing dot `Running`, `.pill.ok` `Done`, `.pill.fail` `Failed`), `Goal` (truncated 64 chars + full `title`), `Events` (tabular), `Cost` (tabular `$0.0000`), `Contracts` (human summary pill: `3 passed` `.ok`, `1 failed · 2 passed` `.fail`, `2 open` `.run`, or `—` — NEVER raw JSON).
  - Clicking any row highlights it (`.selected-row`) and loads `#runDetailCard`. Active running job polls `/api/runs` and `/api/runs/<activeRunId>` every `1500ms`, updating both the table and the open detail view live, and cleanly tears down `clearInterval(runPoll)` on `done`/`failed`/new run/sign-out.
- **Card 3 — Run Detail (`#runDetailCard`):**
  - **KPI Summary Strip:** `Run <id>` (mono) · Status pill · `Total $<cost>` (tabular) · `<N> events` · `<P>/<T> contracts` · `<D> dissents` (`#D96B43` if `> 0`) · `Close ×` ghost button.
  - **Human Failure Callout (`#runErrorBanner`, visible whenever `d.status === "failed"` or `d.error`):**
    - Styled with `border:1px solid #E55B50; border-left:3px solid #E55B50; bg:rgba(229,91,80,0.08); padding:12px 14px; border-radius:4px; margin:12px 0;`.
    - Translates raw runtime errors via `humanizeRunError(errStr)`:
      - Matches `auth_ref 'env:(\w+)'` + `not set` → Headline: `Missing API key: <VAR>` · Body: `Set the <VAR> environment variable on the server, or run in Mock mode to test offline.`
      - Matches `NoCapableModel` → Headline: `No eligible model met required capabilities` · Body: `The pinned model and all fallbacks lacked one or more required capabilities. Open Teams or Models to adjust capabilities or add an eligible fallback.`
      - Matches `BudgetExceeded` or `budget` → Headline: `Run stopped — budget cap reached` · Body: `A run, team, or member spending limit was hit. Increase the cap in Settings or Teams to allow larger runs.`
      - Matches `ContextBudgetExceeded` → Headline: `Prompt exceeded member context budget` · Body: `Shorten the member's charter file or increase context_limit in Teams.`
      - Matches `ConnectError` / `Timeout` / `Connection refused` → Headline: `Could not reach model endpoint` · Body: `Check the endpoint base_url in Models and verify the host (or local Ollama) is running.`
      - Default fallback → Headline: `Run failed before completion` · Body: cleaned first line of error message.
    - Always includes a collapsed `<details>` `Technical detail` containing the raw error string.
  - **5 Internal Sub-Tabs:**
    1. **`Timeline (N)`:** Table with `#` (tabular), `Time (UTC)` (`HH:MM:SS`), `Actor` pill (humanized: `Main Brain`, `Router`, or member ID), `Event` pill (strict human map — NEVER raw snake_case: `plan_created` → `Plan created`, `contract_created` → `Contract issued`, `contract_completed` → `Contract passed`, `contract_failed` → `Contract failed`, `member_state` → `Member status`, `cost` → `Usage & cost`, `blackboard_committed` → `Committed to blackboard`, `fallback_switch` → `Fallback switched` in `.pill.ochre`, `dissent` → `Dissent recorded` in `.pill.warn`, `policy_denied` → `Policy blocked` in `.pill.fail`), and human-formatted `Summary`:
       - `plan_created`: `Goal: "<goal>" (<N> contracts)`
       - `contract_created`: `Assigned to <member_id> — <goal>`
       - `contract_completed`: `<contract_id> passed — <reason>`
       - `contract_failed`: `<contract_id> failed — <reason>`
       - `member_state`: `State changed to <Idle / Working / Reviewing / Blocked / Done>`
       - `cost`: `<tokens> tokens · <tool_calls> tool calls · $<usd>`
       - `blackboard_committed`: `Committed report from <member_id> (entry #<entry_id>)`
       - `fallback_switch`: `Switched to <endpoint> — <reason>`
       - `dissent`: `<member_id> dissented — <reason>`
       - `policy_denied`: `Blocked action: <note>`
       - Plus inline opt-in `<details><summary>Payload</summary><pre>...</pre></details>` (never expanded by default).
    2. **`Contracts (N)`:** Structured table (`Contract ID` mono, `Member`, `Status` pill `Passed` / `Failed` / `Open`, `Goal / Outcome` in human text — derived from `d.contracts` enriched with `contract_created`/`contract_completed`/`contract_failed` events).
    3. **`Cost Breakdown`:** Structured table (`Actor`, `Tokens` en-US comma tabular, `Tool calls` tabular, `USD` `$0.0000` tabular, bold `Total` footer row).
    4. **`Dissents (N)`:** Structured cards (border-left `3px solid #D96B43`) showing `Member`, `Topic / Contract`, `Reason` in plain English, and opt-in `Inspect details`. Empty: `No dissents — the team reached agreement.`
    5. **`Raw Trace`:** `Copy trace` ghost button + monospace `<pre class="trace">` viewer.

### Tab 6: Settings (`#tab-settings`)
- **Layout:** `grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px;` on desktop `>= 1024px` (single column below `1024px`). Left column: Telegram Gateway, Approvals & Budgets. Right column: Change UI Password, Scheduled Jobs, Skills.
- **Dirty-Aware Per-Section Save Contract (Closing the Wipe Trap):**
  - Each section tracks its own dirty flag (`dirtySections.telegram`, `dirtySections.budgets`). Editing any input inside a section shows a `.pill.ochre` `Unsaved` tag next to the section title and toggles that section's Save button from Secondary (`button`) to Gold (`button.gold`).
  - `saveSettingsSection(sectionKey, mut, okMsg)` merges ONLY that section's fields into `S.settings`, sends `PUT /api/settings`, updates `S.settings = res.settings`, clears ONLY `dirtySections[sectionKey]`, and re-renders **ONLY that section** — unsaved edits in other Settings cards are NEVER overwritten!
- **Per-Section Specifications:**
  1. **Telegram Gateway:**
     - Status pill in header: `Configured` (`.pill.ok`) or `Not set` (`.pill`).
     - `Bot token` write-only password field inside `.pw-wrap` with Show/Hide toggle; label `Bot token (stored locally, 0600, never shown back)`, placeholder `Leave blank to keep current token`.
     - `Allowlist user IDs` input (`placeholder="123456789, 987654321"`), validates comma-separated positive integers (flags non-numeric entries inline instead of silently dropping them).
     - Action: `Save Telegram` (Secondary at rest, Gold when dirty).
  2. **Approvals & Budgets:**
     - `Default approval mode` `<select>`: `Smart — ask on risky actions` (`smart`), `Approve all — ask every tool` (`approve`), `Off — disposable host only` (`off`). Choosing `off` reveals an inline ochre warning: `Approval Off is intended only for disposable or sandboxed hosts.`
     - `Default run budget (USD)` and `Default team budget (USD)` numeric inputs (`min="0.1" step="0.5"`, validated `>= 0`).
     - Action: `Save approvals & budgets` (Secondary at rest, Gold when dirty).
  3. **Scheduled Jobs (Cron):**
     - Header action: `Run due jobs now` ghost button (toast: `"Started <N> run(s): <ids>"` or `"No enabled jobs to run."`).
     - Table (`.table-wrap.stacked`): `Job`, `Team`, `Every` (`60 min` mono), `Goal`, `Status` (`Enabled` `.ok` / `Disabled` muted), Actions (`Enable`/`Disable` ghost small, `Delete` outlined danger small).
     - Collapsible `<details>` `+ Add job`: `Job name`, `Team` (`<select>` from `S.config.teams`), `Goal` (required, validated non-empty), `Interval (minutes)` (`min="1"`, default `60`), `Add cron job` secondary button (clears inputs after save).
  4. **Skills (YAML):**
     - List of existing skills in `airlangga/skills/`: each row displays `SKILL` tag, filename (mono), relative path, and `Edit` ghost button (fetches `GET /api/skills?name=<file>` and populates the YAML editor below!).
     - Collapsible `<details id="skillEditorDrawer">` `+ New / edit skill (YAML)`: monospace YAML textarea + `Save skill` secondary button.
     - **Backend safety fix (`web_ui.py`):** Validate and scan `content` in memory (`scan_skill_text` + `Skill.model_validate(yaml.safe_load(...))`) **BEFORE** writing to disk so a blocked or malformed skill never creates a broken file in `airlangga/skills/`.
  5. **Change UI Password:**
     - When `token()` is empty (localhost mode without `AIRLANGGA_UI_TOKEN`): shows muted info note `Running in localhost mode with no UI token set. Restart with AIRLANGGA_UI_TOKEN to enable password login.` and disables inputs cleanly.
     - When token is active: `Current token`, `New token (min 8 chars, no spaces or '=')`, `Confirm new token` (each inside `.pw-wrap` with Show/Hide), `Change UI password` secondary button + `Sign out` ghost button. On success: clears `sessionStorage`, shows login screen with `UI password changed. Sign in with your new token.`

---

## 7. Mobile Design (`~390px` Phone Browser)

### Breakpoint System
| Breakpoint | Layout Changes |
|---|---|
| **`> 1024px`** | Full desktop: Graph canvas + docked `300px` right `#sidePanel`; 2-column Settings; `280px / 1fr` Files split; standard horizontal tables. |
| **`821px – 1024px`** | Narrow desktop/tablet landscape: docked `280px` `#sidePanel`; 1-column Settings; `240px / 1fr` Files split. |
| **`<= 820px`** | **Mobile/Tablet Drawer Mode:** `#graphWrap` stacks vertically (`flex-direction: column`); `#sidePanel` detaches into the **slide-up bottom sheet** behind `#sheetScrim`; Files switches to single-column with collapsible `<details>` tree above editor; `header`, `nav`, `main` padding tightens to `12px`; `fitGraph()` runs automatically on initial load and when switching to Graph tab. |
| **`<= 640px` (`390px` target)** | **Phone Ergonomics:** Header hides `/ Studio` subtitle; compact `#tokenBadge` (`TOKEN` / `LOCAL`); ALL `input, select, textarea` set to **`font-size: 16px`** (stops iOS Safari auto-zoom); ALL interactive buttons, tabs, file rows, and modal close buttons enforce **`min-height: 44px`**; Graph toolbar condenses to 1 clean row + floating canvas zoom pill; ALL data tables use `.stacked` label-value card rows; Modals (`#memberModal`, `#zipModal`) anchor to bottom with `max-height: 92dvh`, sticky header, and sticky action footer. |

### Bottom-Sheet Inspector Spec (`<= 820px`)
- **Backdrop Scrim (`#sheetScrim`):** `position: fixed; inset: 0; background: rgba(0,0,0,0.58); z-index: 34; opacity: 0; pointer-events: none; transition: opacity 180ms ease;`. Active (`.open`): `opacity: 1; pointer-events: auto;`. Tapping scrim calls `closePanel()`.
- **Bottom Sheet (`#sidePanel`):**
  - `position: fixed; left: 0; right: 0; bottom: 0; width: 100%; max-height: 74dvh; z-index: 35; margin: 0; padding: 0; background: #161411; border: none; border-top: 1px solid #524B3E; border-radius: 12px 12px 0 0; box-shadow: 0 -8px 32px rgba(0,0,0,0.72); transform: translateY(105%); transition: transform 200ms cubic-bezier(0.2, 0.8, 0.2, 1); display: flex; flex-direction: column; overflow: hidden;`
  - Active (`.open`): `transform: translateY(0);`.
  - **Grabber Bar (`.sheet-grabber`):** Shown only at `<= 820px`; `height: 22px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; touch-action: none;` with centered `36px × 4px` `#524B3E` pill (`border-radius: 2px`). Dragging down `> 60px` on the grabber or header calls `closePanel()`.
  - **Sticky Sheet Header (`.panel-head`):** `display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px 10px 16px; border-bottom: 1px solid #2E2A22; background: #161411; flex-shrink: 0; min-height: 48px;`. Shows type pill + node/edge title (`text-overflow: ellipsis; overflow: hidden; white-space: nowrap`) + `44×44px` `×` close button (`aria-label="Close inspector"`).
  - **Scrollable Body (`#nodeForm`):** `overflow-y: auto; -webkit-overflow-scrolling: touch;
