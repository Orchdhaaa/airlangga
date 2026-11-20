# Design & UX Audit: `airlangga/ui.html`

Reviewed [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html) (726 lines) against backend capabilities in [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py). Every issue below is tagged **P0** (must change to kill the slop / broken UX), **P1** (high-impact UX win), or **P2** (craft polish).

---

## (a) Honest Audit

### What looks like AI slop (and where it lives)

1. **P0 — Default LLM "Dark Mode Dev-Tool" Color Palette (`:root`, [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L8-L9); `.node.team`, [L55](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L55); `#edges`, [L300](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L300), [L307](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L307))**
   - `--bg:#0f1115`, `--panel:#171a21`, `--panel2:#1e232e`, `--line:#2a3040` is the exact generic cool blue-slate dark palette every LLM defaults to, combined with GitHub Primer's exact tokens (`#3fb950`, `#e5534b`, `#2ea043`, `#8b949e`), electric SaaS blue `#4f8cff` on every default button and every graph edge, and neon purple `#7c5cff` on team nodes.
   - Airlangga gold (`#d4af37`) is dropped onto cold blue-grey panels, where warm metallic gold clashes against `#1e232e` and `#4f8cff`. It reads as a last-minute accent swap on a boilerplate dashboard, not an intentional brand.

2. **P0 — Screaming, Competing Solid Buttons Everywhere (`button`, [L31-L35](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L31-L35); [L95-L114](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L95-L114); [L188-L218](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L188-L218); [L434-L439](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L434-L439))**
   - Default `button` is loud solid electric blue `#4f8cff`, `.gold` is solid gold, `.danger` is solid red `#e5534b`. There is no visual primary action on any screen:
     - **Graph**: solid gold `Save graph` sits next to solid red `Delete selected` (always active even when nothing is selected).
     - **Teams**: solid gold `Create team`, solid blue `+ Add member`, plus a solid red `Delete` button on *every* member row and every team card. A 4-member team renders 5 solid red alarms.
     - **Settings**: 3 solid blue buttons (`Change UI password`, `Add cron job`, `Save skill`) + 1 solid gold button (`Save settings`) orphaned at the bottom.

3. **P0 — Flat, Inverted Typography & Zero Interactive States ([L11-L39](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L11-L39))**
   - Bare `system-ui` stack with no `line-height` on `body` (defaults to cramped ~1.2) and no `tabular-nums` on USD costs, timestamps, or event sequences.
   - Broken scale: `header h1` is `18px` ([L13](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L13)), `.card h2` is `15px` ([L24](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L24)) — *smaller than default 16px body text* — while unstyled `<h3>` elements in `#nodeForm` ([L379](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L379), [L386](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L386)) and `#runDetail` ([L602-L604](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L602-L604)) fall back to `18.72px`, making `h3 > h1 > h2`.
   - **Zero `:hover`, `:focus-visible`, or `:active` rules in the entire stylesheet.** Nothing feels alive, clickable, or keyboard-accessible.
   - **Unstyled `<a>` tags** in `#fileTree` ([L541](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L541)) render in default browser `#0000EE` blue / `#551A8B` visited purple on `#171a21` (~1.8:1 contrast — illegible).

4. **P0 — Broken Toolbar Layout Caused by Global `select { width:100% }` ([L28](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L28), [L61](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L61), [L95-L114](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L95-L114))**
   - `input, select, textarea { width:100% }` applies inside `.toolbar` (`display:flex; flex-wrap:wrap`). Both `#edgeKind` and `#addNodeType` stretch to 100% viewport width, shattering the toolbar into 4 ragged rows on desktop and a tall vertical wall on mobile.

5. **P0 — Everything-in-a-Rounded-Card Sameness & 2005 Folder Tabs (`nav`, [L17-L20](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L17-L20); `.card`, [L23](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L23))**
   - Every tab is a monotonous stack of identical `border-radius:10px; padding:14px` boxes (5 stacked boxes in Settings, 3 in Models, 3 in Runs).
   - `nav button` uses rounded top-only folder tabs with `border-bottom:none` floating over `<main>` with no baseline rule, looking detached and amateurish.

6. **P0 — Node Graph Looks & Behaves Like a Prototype ([L43-L60](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L43-L60), [L296-L374](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L296-L374))**
   - Flat `#12141a` void with no spatial grid, no pan/zoom, no fit-to-view, fixed `1600x900`.
   - Every edge is the same `#4f8cff` `1.6px` stroke ([L307](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L307)), connecting **center-to-center** (`x+90, y+30`, [L303](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L303)) — so SVG arrowheads are buried underneath target node cards!
   - Edge labels ([L311-L314](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L311-L314)) float directly over bezier lines with no backdrop pill, turning illegible whenever curves cross.
   - `startDrag` calls `drawEdgesOnly()` -> `renderGraph()` ([L336](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L336), [L340](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L340)), destroying and recreating every `.node` DOM element on every `pointermove` frame — causing severe drag jank and dropped clicks.
   - Every node type has the exact same `180px` box with only a 4px top bar; `main_brain` has the same visual weight as a `tool` node.

7. **P1 — Raw Internal Strings, Raw JSON Dumps, and Apologetic Instructional Filler ([L113](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L113), [L148](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L148), [L399](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L399), [L533](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L533), [L589](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L589), [L601-L603](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L601-L603))**
   - Raw snake_case (`lead_member`, `uses_model`, `has_charter`, `main_brain`, `anthropic_messages`) exposed directly as UI copy.
   - Raw `JSON.stringify(r.contracts||{})` dumped into Runs table cells ([L589](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L589)) and raw JSON `<pre>` blocks for `Cost by actor` / `Dissents` ([L602-L603](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L602-L603)).
   - Long tutorial sentences bolted onto toolbars and forms ("Drag nodes to move. Connect mode: click a source node...") instead of clear visual affordances.
   - Empty `#status` bar ([L92](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L92)) sits at the top of `<main>` and scrolls completely out of view on long tabs.

8. **P1 — Barebones Tutorial Login Screen & Flash of Unauthenticated Chrome ([L68-L73](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L68-L73), [L222-L234](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L222-L234), [L694-L708](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L694-L708))**
   - A lone `380px` dark grey box in a `#0f1115` void with zero brand identity. Because `#loginScreen` starts `display:none`, unauthenticated visitors briefly see the broken header (`auth: checking…`) and empty tabs before the overlay flashes in.

---

### What is already good and MUST be kept

- **Single self-contained HTML file (`ui.html`), zero build step, zero runtime JS frameworks.** Fast, portable, served straight from `web_ui.py`.
- **No emoji-as-icons, no purple-blue hero gradients, no fake glassmorphism.** The problem is generic dev-tool scaffold flatness, not marketing-page bloat—do not overcorrect into gimmicks.
- **Clean 6-tab IA (`Graph | Teams | Models | Files | Runs | Settings`).** Maps 1:1 to real backend state with zero vanity widgets.
- **Real bi-directional graph-to-YAML persistence.** Rewiring edges in the graph genuinely updates `airlangga.yaml` (`apply_graph_to_config`, [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L315-L368)).
- **Sound security UX.** `sessionStorage`-only token storage, URL token scrubbing via `history.replaceState` ([L699](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L699)), `esc()` HTML escaping, `autocomplete` hints, secret write-only Telegram token, no `window.prompt()`.
- **Practical operator ergonomics.** One-click `Mock` vs `Real providers` toggle on Runs, 1.5s run polling with auto-open trace, instant UI password rotation without server restart.
- **House dark + `#D4AF37` gold anchor.** Strong conceptual fit for Airlangga—just needs the surrounding system rebuilt to honor it.

---

## (b) Revised Visual Direction

**Concept: "Candi Obsidian & Lontar Studio"** — Warm volcanic basalt surfaces (not cold blue-slate), crisp ivory parchment text, antique Javanese gold `#D4AF37` reserved for sovereignty/primary action, grounded in earthy mineral accents (Majapahit terracotta, Nila cyan, pandan jade, sogan ochre). Agency-grade typographic contrast (inspired by `sweet-tape.com` / `tehtariknation.com` / `bikebear.com.my`): confident display voice + crisp structural hairline rules + sharp, tactile controls. Zero batik/temple clipart; heritage comes from **warm dark-stone/gilt materiality**, **crisp stepped/notched geometric framing**, and **Indonesian type craft** (`Plus Jakarta Sans`).

### 1. Color Palette (all text pairs verified >= 4.5:1 WCAG AA)

| Token | Hex | Role & Contrast Check |
|---|---|---|
| `--bg` | `#0D0C0A` | Page background (warm volcanic obsidian, replaces `#0f1115`) |
| `--canvas-bg` | `#090807` | Graph canvas well + dot grid `#242019` |
| `--surface` | `#161411` | Primary panels / drawers / header (warm andesite) |
| `--surface-2` | `#1F1C17` | Elevated cards, inputs, nodes, table headers (dark teak) |
| `--surface-3` | `#29251E` | Hover fill for interactive rows / ghost buttons |
| `--border` | `#2E2A22` | Structural 1px hairlines (panels, table dividers) |
| `--border-ctrl` | `#524B3E` | Input / select / ghost-button resting border |
| `--border-hover` | `#857A66` | Hover border on inputs & nodes |
| `--text` | `#F4EFE6` | Primary text (warm lontar ivory) — **16.1:1** on `#161411`, **14.8:1** on `#1F1C17` |
| `--muted` | `#B3AA9B` | Secondary text, table headers, labels — **8.0:1** on `#161411`, **7.4:1** on `#1F1C17` |
| `--subtle` | `#8C8375` | Placeholders, captions, metadata — **4.9:1** on `#161411`, **4.5:1** on `#1F1C17` |
| `--gold` | `#D4AF37` | House accent: Primary CTA, Main Brain, active tab rule, focus ring — **9.3:1** with `#0D0C0A` ink; **8.8:1** on `#161411` |
| `--gold-hover` | `#E5C558` | Primary gold button hover |
| `--gold-tint` | `rgba(212,175,55,0.12)` | Subtle active highlight / selected row tint |
| `--accent2` | `#D96B43` | Secondary brand accent (Majapahit terracotta; replaces `#4f8cff` / `#7c5cff`) — **5.4:1** on `#161411` |
| `--info` | `#56B4C8` | Cool mineral accent (Nila cyan: links, running status, member nodes) — **7.7:1** on `#161411` |
| `--ok` | `#4CC38A` | Success / done / model nodes (jade) — **8.3:1** on `#161411` |
| `--danger` | `#E55B50` | Danger / error / failed (vermilion) — **5.2:1** on `#161411` (`#F2786D` for outlined text: **6.8:1**) |

#### Graph Node & Edge Color Map (by semantic type)

| Node Type | Accent Hex | Edge Kind(s) | Edge Stroke Style |
|---|---|---|---|
| `main_brain` | `#D4AF37` (Gold) | `assigns`, `powers` | Solid `2.2px` `#D4AF37` |
| `team` | `#D96B43` (Terracotta) | `has_member` | Solid `1.8px` `#D96B43` |
| `member` | `#56B4C8` (Nila Cyan) | `depends_on` | Dashed `5 4`, `1.6px` `#56B4C8` |
| `model` | `#4CC38A` (Jade) | `uses_model` | Solid `1.8px` `#4CC38A` |
| `file` / `folder` | `#C89B54` (Sogan Ochre) | `has_charter` / `has_file` | Solid `1.8px` (`has_charter`), Dotted `2 4` (`has_file`) `#C89B54` |
| `tool` / `skill` | `#9E9587` (Pewter) | `uses_tool`, `uses_skill` | Dashed `4 3`, `1.5px` `#857A66` |

---

### 2. Typography

Load optional non-blocking Google Fonts (works offline cleanly via tuned system fallbacks; **`Plus Jakarta Sans`** is by Indonesian foundry Tokotype — authentic local craft, high mobile legibility):

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" media="print" onload="this.media='all'">
```

- **Font stacks**:
  - `--font-display`: `'Fraunces', 'Iowan Old Style', 'Palatino Linotype', Georgia, serif`
  - `--font-sans`: `'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
  - `--font-mono`: `'JetBrains Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace`

| Role | Family | Size | Weight | Line-Height | Letter-Spacing |
|---|---|---|---|---|---|
| Wordmark / Login H1 | `--font-display` | `20px` header / `30px` login | `700` | `1.1` | `-0.02em` |
| Screen / Section H2 | `--font-sans` | `16px` (`15px` mobile) | `700` | `1.25` | `-0.015em` |
| Subsection H3 | `--font-sans` | `13px` (uppercase eyebrow) | `700` | `1.3` | `+0.08em` (`color: var(--muted)`) |
| Body / Table cells | `--font-sans` | `14px` | `400` | `1.5` | `0` |
| Form labels / Eyebrows | `--font-sans` | `11px` uppercase | `600` | `1.3` | `+0.07em` (`color: var(--muted)`) |
| Mono (IDs, models, paths, USD, traces) | `--font-mono` | `12.5px` (`12px` trace) | `400` / `500` | `1.5` | `0` + `font-variant-numeric: tabular-nums` |

---

### 3. Spacing, Radius & Shadow Rules

- **Spacing scale (4px base)**: `4 / 8 / 12 / 16 / 20 / 24 / 32px`. Eliminate `<p>` wrapper hacks around buttons; use `.actions { display:flex; gap:8px; margin-top:14px; flex-wrap:wrap; align-items:center; }`.
- **Radius hierarchy (kill uniform 10px softness)**:
  - Structural panels / graph canvas / tables / login card: `4px` (crisp, editorial, architectural — not bubbly SaaS).
  - Buttons, inputs, selects: `4px`.
  - Graph nodes: `6px` (`main_brain`: `6px` with double-frame gold inner rule; `tool`/`skill`: `3px` compact chip; `file`/`folder`: `2px 10px 2px 2px` folded-document corner hint).
  - Status pills: `2px` sharp micro-tags (not `border-radius:10px` bubbly capsules everywhere).
- **Shadows (no generic blurred drop-shadows on cards)**:
  - Flat `1px solid var(--border)` for static panels; reserve elevation shadow strictly for floating elements:
    - Dragged/selected graph node: `0 8px 24px rgba(0,0,0,0.55), 0 0 0 2px var(--gold)`.
    - Floating status toast & mobile bottom drawer: `0 12px 32px rgba(0,0,0,0.65)`.

---

### 4. Component Specs

#### Node-Graph Styling
- **Canvas (`#canvasScroll`)**: Background `#090807` with subtle CSS dot grid (`background-image: radial-gradient(#2A251D 1px, transparent 1px); background-size: 20px 20px;`).
- **Node silhouettes & hierarchy (stop making all nodes identical 180px boxes)**:
  - **Left accent rail (`3px` solid type color) + subtle top-right type micro-tag**, not a clumsy `4px` top bar.
  - **`main_brain`**: Wider (`210px`), warm gold-tinted fill `#1C1810`, `1.5px solid #D4AF37`, subtle inner `box-shadow: inset 0 0 0 3px #0D0C0A, inset 0 0 0 4px rgba(212,175,55,0.35)` (tasteful Javanese double-frame authority without clipart).
  - **`team`**: `196px`, `#1C1714` fill, `3px` left `#D96B43` rail.
  - **`member`**: `196px`, `#181A1C` fill, `3px` left `#56B4C8` rail.
  - **`model`**: `200px`, `#151B18` fill, `3px` left `#4CC38A` rail, provider/model rendered in `--font-mono`.
  - **`file` / `folder`**: `184px`, `#1B1813` fill, `3px` left `#C89B54` rail, `border-top-right-radius: 12px`.
  - **`tool` / `skill`**: Compact `148px` height-trimmed pill-block, `#1A1815` fill, `1px dashed #524B3E`.
- **Input / Output Ports**: Render crisp `8px` circular port anchors on the **left edge** (input) and **right edge** (output) of each node (`top: 50%`). Connect edges from **source right port (`a.x + a.w, a.y + a.h/2`) to target left port (`b.x, b.y + b.h/2`)** (falling back to left-to-right when reversed). Now every arrowhead (`markerWidth="8"`, color-matched per edge kind) lands cleanly at the node boundary instead of hiding underneath!
- **Edge labels**: Render `<rect rx="3" fill="#0D0C0A" stroke="#2E2A22" stroke-width="1">` behind every `<text>` label, and display clean human labels (`uses model`, `charter`, `member`, `assigns`, `tool`) instead of `uses_model`. Add an invisible `14px`-wide hit-target `<path stroke="transparent" stroke-width="14">` underneath each visible edge so edges are easy to click and tap!
- **States**:
  - **Hover**: `border-color: var(--border-hover); transform: translateY(-1px);` (for non-dragged nodes); edge stroke thickens `+1px` and brightens.
  - **Selected**: `border-color: var(--gold); box-shadow: 0 0 0 2px rgba(212,175,55,0.3), 0 8px 20px rgba(0,0,0,0.5);` + dim unrelated edges to `opacity: 0.25` so the selected node's connections pop immediately.
  - **Connect-source**: Pulsing dashed `#56B4C8` outline + `cursor: crosshair` on `#canvas` + banner badge `Connecting from [Node] -> click target (Esc to cancel)`.

#### Buttons (Strict 4-tier hierarchy — max ONE `.primary` per screen/section)
- **Primary (`.btn-gold`, replaces `.gold`)**: `background:#D4AF37; color:#0D0C0A; font-weight:700; border:1px solid #D4AF37; padding:9px 16px; border-radius:4px;` Hover: `#E5C558`. Active: `transform:translateY(1px)`.
- **Secondary (default `button`)**: `background:#242019; color:#F4EFE6; border:1px solid #524B3E; font-weight:600; padding:8px 14px; border-radius:4px;` Hover: `background:#2E2920; border-color:#857A66;` (Kills the generic solid blue default button!)
- **Ghost (`.ghost`)**: `background:transparent; color:#B3AA9B; border:1px solid transparent; padding:7px 12px;` Hover: `color:#F4EFE6; background:rgba(244,239,230,0.06); border-color:#2E2A22;`
- **Danger (`.danger`)**: **Outlined by default**, never a loud red brick until hover! `background:transparent; color:#F2786D; border:1px solid #6E2D28; font-weight:600;` Hover: `background:#E55B50; color:#0D0C0A; border-color:#E55B50;`
- **Focus-visible (all buttons/inputs/tabs)**: `outline: 2px solid #D4AF37; outline-offset: 2px;`

#### Inputs, Selects & Textareas
- `background:#11100D; color:#F4EFE6; border:1px solid #524B3E; border-radius:4px; padding:9px 11px; font-size:15px;` (**16px on `<640px` mobile** to prevent iOS Safari auto-zoom!).
- Focus: `border-color:#D4AF37; box-shadow:0 0 0 3px rgba(212,175,55,0.16); outline:none;`
- Scope `width:100%` to form containers (`form input, .field input, .card input, .card select, .card textarea`), NOT `.toolbar select` (`width:auto; min-width:130px;`).
- Style `a { color:#56B4C8; text-decoration:none; } a:hover { color:#F4EFE6; text-decoration:underline; }`.

#### Tables
- Always wrap every `<table>` in `<div class="table-wrap">` (`overflow-x:auto; -webkit-overflow-scrolling:touch;`).
- `th`: `font-size:11px; text-transform:uppercase; letter-spacing:0.07em; color:#B3AA9B; background:#1A1713; border-bottom:1px solid #3D372C; padding:9px 10px; white-space:nowrap;`
- `td`: `padding:10px; border-bottom:1px solid #26221B; font-size:13.5px;`
- Row hover: `tbody tr:hover { background: rgba(244,239,230,0.03); }`
- Numeric/mono columns (`.num`, `.mono`): `--font-mono`, `tabular-nums`, right-aligned for `$` and counts.

#### Pills / Badges
- Sharp micro-tags, not round capsules: `display:inline-flex; align-items:center; gap:5px; padding:2px 7px; border-radius:2px; font-family:var(--font-mono); font-size:11px; font-weight:500; text-transform:uppercase; letter-spacing:0.05em; background:#1F1C17; border:1px solid #3D372C; color:#B3AA9B;`
- Semantic variants with subtle tinted fills:
  - `.ok`: `color:#4CC38A; border-color:rgba(76,195,138,0.4); background:rgba(76,195,138,0.1);`
  - `.run`: `color:#56B4C8; border-color:rgba(86,180,200,0.4); background:rgba(86,180,200,0.1);` (add tiny `6px` pulsing dot)
  - `.fail`: `color:#F2786D; border-color:rgba(229,91,80,0.4); background:rgba(229,91,80,0.1);`
  - `.gold`: `color:#D4AF37; border-color:rgba(212,175,55,0.45); background:rgba(212,175,55,0.1);`

#### Login Card
- Full-bleed obsidian backdrop (`#0D0C0A`) with a crisp hairline geometric architectural frame (subtle CSS radial gold vignette `radial-gradient(circle at 50% 0%, rgba(212,175,55,0.09), transparent 55%)` — no cheap gradient text, no glass blur).
- Card (`max-width:400px`, `background:#161411`, `border:1px solid #3D372C`, `border-top:3px solid #D4AF37`, `border-radius:4px`, `padding:32px 28px`).
- Top mark: tiny crisp 24px inline geometric SVG emblem (4-path stepped diamond/crown inspired by Kahuripan geometry, `#D4AF37` stroke) + `Fraunces` `30px` **Airlangga** wordmark + uppercase mono eyebrow `AGENTIC TEAM STUDIO`.
- Single full-width `.btn-gold` (`Enter Studio`), clear inline error banner, compact muted security footnote.
- **Prevent flash of unauthenticated chrome**: hide `<header>, <nav>, <main>` via `body.auth-pending > :not(#loginScreen) { visibility:hidden; }` until `boot()` resolves.

---

## (c) Layout & UX Revisions Per Tab

### Global Chrome (Header, Nav, Status Toast)
- **Header (P0)**: Compact `52px` bar (`background:#161411; border-bottom:1px solid #2E2A22`). Left: 20px geometric gold SVG mark + `Airlangga` (`Fraunces 20px`) + short subtle separator `/ Studio` (drop the 11-word subtitle from the header — it belongs on the login page, not wasting horizontal space on every tab). Right: compact auth pill (`LOCALHOST` or `TOKEN ACTIVE`) + a subtle `Sign out` ghost button when a token is set (missing today!).
- **Nav (P0)**: Replace detached folder tabs with a clean horizontal underline rail (`background:#12100D; border-bottom:1px solid #2E2A22; padding:0 16px; gap:4px;`). Active tab gets `color:#F4EFE6; border-bottom:2px solid #D4AF37;` with count badges where helpful (`Teams 2`, `Runs 5`).
- **Status feedback (P0)**: Replace static `#status` at the top of `<main>` ([L92](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L92)) with a fixed bottom-right (bottom-center on mobile) dismissible toast (`position:fixed; bottom:16px; right:16px; z-index:40;`) so feedback is always visible when saving deep inside Teams or Settings.

---

### Priority Screen 1: **Graph** (Primary Workspace)

**One primary action**: `Save graph` (`.btn-gold`, dynamically displays an amber dirty dot `Save graph *` whenever local nodes/edges differ from server state, and dims to secondary when clean).

**What to change (in order)**:
1. **P0 — Fix drag performance & port-anchored edges**: Stop calling `renderGraph()` inside `pointermove` ([L336](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L336)). Update only the dragged node's `style.left/top` and update the `d` attributes of connected `<path>`/`<text>` elements directly in place. Anchor edges to right/left ports (`x + width` -> `x`) with color-coded strokes, arrowheads, haloed labels, and 14px hit paths.
2. **P0 — Fix the broken toolbar & declutter controls**: Remove global `width:100%` on toolbar selects. Group controls cleanly into 3 compact clusters separated by `1px` vertical dividers:
   - *Mode cluster*: `Select` / `Connect` segmented toggle + compact edge-kind dropdown (shown *only* when Connect mode is active, with human labels: `uses model`, `has member`, `has charter`, `attaches file`, `uses tool`, `assigns`, `depends on`).
   - *Canvas cluster*: `+ Add file/folder` (note: [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L301-L303) `_sync_graph` silently drops newly added `team`/`member`/`tool`/`skill` nodes on save because teams/members live in `airlangga.yaml`! Restrict `+ Add node` to `file` / `folder` / `model` — or clearly label quick-link to Teams tab for creating teams/members — to eliminate a major data-loss trap!), `Zoom - / 100% / +`, `Fit` (auto-fits all nodes into viewport using CSS `transform: translate() scale()` on `#canvas`).
   - *Save cluster (right-aligned)*: `Save graph` (`.btn-gold`). **Remove** `Delete selected` from the top toolbar and move it *inside* the Inspector panel (only visible when a node or edge is actually selected).
3. **P0 — Delete the 24-word help sentence ([L113](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L113))**. Replace with a subtle `11px` mono legend bar at the bottom of the canvas showing the 6 node color swatches + `Drag to move · Scroll/pinch to pan · Click node to inspect`.
4. **P1 — Upgrade the Right Inspector (`#sidePanel`)**:
   - Header shows node type micro-badge + node label + close `×` button.
   - Replace the clunky 2-step "Apply to node" + "Save graph" friction: auto-apply inspector input changes immediately to the in-memory graph (`input`/`change` listeners) and flag `Save graph *` as dirty, leaving a single clear `Save graph` action.
   - For `member` nodes, change `Charter file` from raw text input ([L388](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L388)) to a `<select>` populated from `S.files` (matching the Teams tab) and change `Approval` ([L390](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L390)) to a `<select>` (`smart` / `approve` / `off`).
   - Show an `Incoming / Outgoing Connections` list inside the inspector with a 1-click `×` disconnect button per edge (huge win on mobile where tapping thin SVG lines is hard).
   - Stagger newly added nodes (`x: 160 + count*24, y: 140 + count*24`) instead of stacking them all at `(120, 120)` ([L359](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L359)).

**Concrete New Structure (Graph)**:
```
[ Toolbar: (Select | Connect [+EdgeKind when on]) | (+ Add File/Model) | (- 100% + Fit)      (Save graph *) ]
+-----------------------------------------------------------------------+------------------------------------+
|  #canvasScroll (dot-grid well, pan + zoom transform, port-to-port     |  #sidePanel (300px desktop /       |
|   color-coded bezier edges, distinct node silhouettes)                |   bottom sheet on mobile)          |
|                                                                       |  - Node Type Pill + Title + Close  |
|  [Main Brain] ──assigns──> [Team] ──member──> [Member] ──model──> [M] |  - Live-bound form fields          |
|                                                  └──charter──> [File] |  - Connections list (click to      |
|                                                                       |    remove edge)                    |
|  [Legend bar: ● Brain ● Team ● Member ● Model ● File ● Tool]          |  - [Outlined Danger: Delete node]  |
+-----------------------------------------------------------------------+------------------------------------+
```

---

### Priority Screen 2: **Teams** (Roster & Member Configuration)

**One primary action**: `+ New team` (`.btn-gold` in the tab header bar, opening a collapsible creation drawer/card — stop burning 240px of permanent top-of-screen real estate on a create form you use once a week!).

**What to change (in order)**:
1. **P0 — Collapse `Create team` behind a header button**: Top bar of Teams tab becomes: Left `Teams (N)` heading + Right `+ New team` (`.btn-gold`). Clicking toggles the creation panel cleanly above the list.
2. **P0 — Kill the sea of red `Delete` buttons & fix duplicate-ID bug**:
   - In each team card header: Team Name + `template` / `mode` micro-tags on the left; **Quick `Run team` ghost button** (switches to Runs tab pre-selected to this team!) + secondary `+ Add member` + subtle icon/text `Delete team` (ghost-danger, never solid red) on the right.
   - In the members table: combine `Model` as compact `provider / model` in mono, render `Tools` as tiny wrapped micro-tags (not comma text), format `Budget` right-aligned tabular mono, and replace the loud `Edit` + solid red `Delete` buttons with clean compact `Edit` (secondary) and `Remove` (ghost-danger).
   - Fix the global `#mfId` duplicate-ID bug ([L449-L466](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L449-L466)) by rendering the Member Editor as a **single modal / slide-over drawer** (or closing any open inline form before opening another) with a `Cancel` button (currently impossible to close an open member form without saving or refreshing!).
3. **P1 — Expose `Edit team` (goal / template / mode)**: `PUT /api/teams/<name>` already exists in [web_ui.py](file:///home/hatch/workspace/airlangga/airlangga/web_ui.py#L869-L878), so allow editing a team's goal and `team_brain_mode` inline rather than forcing delete-and-recreate.
4. **P1 — Auto-fill provider defaults in Member Editor**: When the user picks a provider preset in `#mfProvider`, pre-fill `#mfEndpoint`, `#mfAuth`, and offer a `<datalist>` of that provider's preset `models` so users don't have to flip to the Models tab to remember model IDs.

**Concrete New Structure (Teams)**:
```
[ Tab Header:  Teams (2)                                                      (+ New team [gold]) ]
[ Collapsible Create-Team Drawer (hidden by default; 3-col grid + Goal + Create/Cancel)           ]

+-------------------------------------------------------------------------------------------------+
|  research-01   [RESEARCH] [LEAD MEMBER]                   [Run ->]  [+ Add member]  [Delete]    |
|  "Monitor SEA fintech filings and produce sourced briefs"                                       |
|  ---------------------------------------------------------------------------------------------  |
|  MEMBER         ROLE         MODEL (mono)             TOOLS           CHARTER     BUDGET   ACT  |
|  analyst-1      researcher   anthropic/claude-sonnet  [web] [read]    superagent  $5.00  Edit × |
|  reviewer-1     critic       openai/gpt-5-mini        [read]          —           $2.00  Edit × |
+-------------------------------------------------------------------------------------------------+
[ Single Slide-over / Modal Member Editor when Editing or Adding (with Cancel + Save member)      ]
```

---

### Priority Screen 3: **Runs** (Execution & Trace Investigation)

**One primary action**: `Run team` (`.btn-gold`).

**What to change (in order)**:
1. **P0 — Compact Run Launcher bar + fix empty-state JS bug**:
   - Compress "Launch a run" into a tight single-row command bar (`Team` select `180px` | `Goal` input `flex:1` | `Mock / Live` compact toggle | `Run team` `.btn-gold`).
   - Fix the broken empty state at [L585-L591](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L585-L591) (`data.runs.length ? ... : '<div class="empty">No runs yet — launch a team above.</div>'`).
2. **P0 — Kill raw JSON in Runs table and Run Detail**:
   - In Runs table ([L589](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L589)): replace raw `JSON.stringify(r.contracts||{})` with a clean count/status pill (e.g. `2 contracts` or `—`). Make the entire row clickable to open the trace (with a selected highlight), removing redundant `Trace` button noise.
   - In Run Detail (`#runDetail`, [L598-L604](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L598-L604)): replace the wall of 3 raw JSON `<pre>` dumps with a **structured 3-part investigation layout**:
     1. **Summary KPI strip**: Run ID (mono), Status pill, Total Cost (`$0.0412` in large tabular mono), Event Count, Dissent Count (highlighted in terracotta if `> 0`), plus a `Close` button.
     2. **Internal sub-tabs inside Run Detail**: `Timeline (N)` | `Cost Breakdown` | `Dissents (N)` | `Raw Trace`.
        - `Timeline`: compact event log with `seq`, `HH:MM:SS` UTC (strip verbose date prefix), `actor` pill, `type` pill, and concise human-formatted payload summary (expandable `<details>` for raw JSON).
        - `Cost Breakdown`: actual HTML `<table>` (Actor | Calls/Tokens | USD) parsed from `d.cost_by_actor` instead of `JSON.stringify`.
        - `Raw Trace`: clean monospace viewer with a `Copy trace` ghost button.
3. **P1 — Clear polling leak**: Store the `setInterval` handle ([L614](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L614)) and clear it if another run starts or if `status` fails, and show a live pulsing `Running…` indicator on the active run row.

**Concrete New Structure (Runs)**:
```
[ Command Bar: (Team v) | (Goal input — flex:1 .........................) | (Mock v) | (Run team [gold]) ]

+----------------------------------------------------------------------------------------------------------+
|  RUN HISTORY                                                                                             |
|  RUN ID (mono)     STATUS      GOAL                                 EVENTS   COST       CONTRACTS        |
|  run-20261120-a1   [● RUNNING] Produce sourced brief on ...             12   $0.0142    2 ok             |
|  run-20261120-9f   [DONE]      Audit auth handlers in web_ui.py         28   $0.0830    3 ok             |
+----------------------------------------------------------------------------------------------------------+

+----------------------------------------------------------------------------------------------------------+
|  RUN DETAIL: run-20261120-9f  [DONE]   Total: $0.0830 · 28 events · 0 dissents                    [ × ]  |
|  Sub-tabs: [ Timeline (28) ]  [ Cost Breakdown ]  [ Dissents (0) ]  [ Raw Trace ]                        |
|  #   TIME      ACTOR        TYPE           SUMMARY                                                       |
|  01  10:42:01  main_brain   plan_created   Goal: Audit auth handlers in web_ui.py  ▸ raw                 |
+----------------------------------------------------------------------------------------------------------+
```

---

### Secondary Tabs: Models, Files, Settings, Login

#### **Models**
- **Primary action**: `Save Main Brain` (`.btn-gold`).
- **Order of changes**:
  1. **P0 — Differentiate the 3 identical cards**: Make `Main Brain` a distinct hero-configured strip with a gold left accent rail (`3px solid #D4AF37`), auto-filling endpoint/auth_ref from provider presets when `#mbProvider` changes.
  2. **P1 — Make `Member models` actionable**: Add a compact `Edit` link per row that jumps straight to that member in Teams (or opens the Member Editor directly), replacing the apologetic note at [L533](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L533). Truncate long endpoints with `title` tooltip.
  3. **P1 — Collapse `Provider presets` into a `<details>` reference drawer** ("Provider Reference (8 presets)") so it stops taking up half the screen on every visit.

#### **Files**
- **Primary action**: `Save file` (`.btn-gold`, shown when a file is open) / `+ New` (secondary in sidebar).
- **Order of changes**:
  1. **P0 — Fix unstyled blue `<a>` links & broken folder clicks ([L541](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L541))**: Render files as full-width clickable rows (`display:flex; justify-content:space-between; padding:8px 10px;`) with active highlight when `editingFile === f.path`. Render `folder` entries as non-clickable muted group headers (or click to prefill `#newFilePath` with `folder/`)—do NOT call `openFile()` on folders, which currently triggers HTTP 400 (`no such file`).
  2. **P0 — Asymmetric IDE split (`280px` file tree | `1fr` editor)** instead of `.row > * { flex:1 }` (50/50 split wastes half the screen on a narrow file list).
  3. **P1 — Move `New file / folder` to the top of the file list** as a compact inline bar (`input` + `+ File` + `+ Dir` ghost buttons), and move `Save file` + outlined `Delete` into the editor header bar alongside the open file path (mono) and dirty `*` indicator. Support `Cmd/Ctrl+S` to save.

#### **Settings**
- **Primary action**: One explicit save button *per independent section* (kills the confusing global `Save settings` button at [L218](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L218) that only saves 2 of the 5 cards!).
- **Order of changes**:
  1. **P0 — Fix the broken Save mental model**: Split Settings cleanly into a 2-column desktop layout (1-col mobile) or crisp stacked sections where **each section owns its own save**:
     - **Budgets & Approvals + Telegram** -> single `Save general settings` (`.btn-gold`) directly inside that section.
     - **UI Password / Access Token** -> self-contained card with secondary `Update password` button (not competing solid blue).
     - **Scheduled Jobs (Cron)** -> show a real table with **Enable/Disable toggle and Delete button** per job (supported by `PUT /api/settings`, missing today!), `Run due now` ghost button, and collapsible `+ Add job` form with `<select>` populated from `Object.keys(S.config.teams)` instead of free-text `#cronTeam` ([L202](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L202)).
     - **Skills (YAML)** -> split into existing skills list + collapsible `+ New / Edit skill` YAML editor.
  2. **P2 — Add `Sign out` action** (clears `sessionStorage` and shows login screen) in the Access Token card and global header.

#### **Login Page**
- **Primary action**: `Enter Studio` (`.btn-gold`, full-width).
- **Order of changes**:
  1. **P0 — Prevent unauthenticated chrome flash**: Add `body.auth-pending` so header/tabs never flash before `#loginScreen` mounts.
  2. **P0 — Brand the card properly**: Add the geometric gold crest SVG, `Fraunces` `30px` title, gold top accent rule (`3px solid #D4AF37`), show/hide token toggle button inside the password field, and clean inline error callout.

---

## (d) Mobile (~390px Phone Browser) Fixes

Currently there are **zero `@media` queries** in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html). At `390px`, the app breaks in 9 distinct places:

| Priority | What breaks at ~390px (exact selector/line) | Concrete CSS / DOM / JS Fix |
|---|---|---|
| **P0** | **Graph canvas crushed to `26px` wide** (`#graphWrap { display:flex }` [L43], `#sidePanel { width:320px; flex-shrink:0 }` [L60]) | `@media (max-width: 820px)`: set `#graphWrap { flex-direction: column; }`, `#canvasScroll { height: 58vh; min-height: 360px; width: 100%; }`, and turn `#sidePanel` into a **bottom drawer** (`position:fixed; left:0; right:0; bottom:0; max-height:68vh; overflow-y:auto; z-index:35; transform:translateY(100%); transition:transform .2s;`) that slides up **only when a node/edge is tapped** (`#sidePanel.open { transform:translateY(0); }`) with a clear `Done / ×` close button. |
| **P0** | **Nav tabs overflow 390px horizontally** (`nav` [L17-L20], 6 buttons ~450px wide) | Set `nav { overflow-x:auto; scrollbar-width:none; -webkit-overflow-scrolling:touch; flex-wrap:nowrap; padding:0 12px; } nav::-webkit-scrollbar { display:none; } nav button { flex:0 0 auto; white-space:nowrap; min-height:44px; padding:10px 14px; }`. |
| **P0** | **Header crushes/overflows** (`header` [L12-L15], long `.sub` + `#tokenBadge`) | Hide `.sub` at `<640px` (or remove permanently per Section c), set `header { padding:10px 12px; gap:8px; }`, compact `#tokenBadge` to short label (`TOKEN` / `LOCAL`). |
| **P0** | **All 5 tables blow out page width** (`table` [L36-L38]: Teams 7 cols, Models 8 cols, Presets 4 cols, Runs 7 cols, Events 5 cols) | Wrap every `<table>` in `.table-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; margin:0 -12px; padding:0 12px; }`. For **Teams members** and **Runs history** on `<640px`, go one step further: use CSS responsive stacked rows (`data-label` attribute on `<td>` with `tr { display:grid; grid-template-columns:1fr 1fr; padding:10px 0; }` or compact 2-line card rows) so the user never has to horizontally scroll just to read member models or tap a Run! |
| **P0** | **Graph canvas (`1600x900`) impossible to navigate or drag on touch** ([L45](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L45), [L331-L339](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L331-L339)) | 1) Add `touch-action:none;` on `.node` so dragging a node doesn't scroll the page, and `touch-action:pan-x pan-y;` on `#canvasScroll`. 2) Add a `Fit` button + `- / +` zoom buttons (`scale` from `0.35` to `1.5`), and auto-call `fitGraph()` on initial load when `window.innerWidth < 768` so the entire graph fits on a 390px screen immediately. 3) Keep edge deletion/editing accessible inside the node inspector's Connections list so mobile users never have to tap a `1.6px` SVG line. |
| **P0** | **Graph toolbar swallows half the phone screen** ([L28](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L28), [L95-L114](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L95-L114)) | Compact single-scroll or 2-row toolbar (`padding:8px; gap:6px;`): Row 1 = `Connect` toggle + `+ Add` + `Fit` + `Save` (gold). Edge-kind `<select>` appears only when Connect is ON. Drop verbose help prose. |
| **P0** | **iOS Safari auto-zooms on every form field** (`input, select, textarea { font-size:14px }` [L29]) | `@media (max-width: 640px) { input, select, textarea { font-size: 16px; } }` and ensure all buttons/tabs/file rows have `min-height: 44px;`. |
| **P1** | **Files 50/50 split & trace `<pre>` cramped at 390px** ([L141](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L141), [L62-L63](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L62-L63)) | At `<768px`, stack Files into a collapsible file picker strip above a `55vh` full-width editor (`min-width:0` on `.row > *` so inputs never overflow `358px`). Give `pre.trace` `font-size:11.5px; line-height:1.45; word-break:break-word; max-height:60vh;`. |
| **P1** | **`#status` banner scrolls off-screen** ([L92](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L92)) | Fixed toast at `bottom: 12px; left: 12px; right: 12px;` on mobile so save/error confirmation is always visible without scrolling back up. |

---

## (e) What NOT To Do (Slop Anti-Patterns to Avoid)

1. **Do NOT introduce purple/blue gradients, neon glow blurs, or glassmorphism (`backdrop-filter: blur()`).** Keep surfaces solid, warm obsidian/teak with crisp 1px borders.
2. **Do NOT use emojis as UI icons (`🧠`, `🤖`, `📁`, `⚙️`, `🚀`).** Use either crisp typography/micro-tags or tiny minimal 14–16px inline geometric `<svg>` strokes (`stroke="currentColor" stroke-width="1.75"`).
3. **Do NOT put cheap batik patterns, wayang silhouettes, or temple clip-art SVG backgrounds anywhere.** Javanese heritage here means obsidian stone + antique gold + disciplined stepped geometry + Tokotype's `Plus Jakarta Sans` — never tourist-brochure kitsch.
4. **Do NOT make multiple buttons solid gold or solid red on the same screen.** Gold (`#D4AF37`) is reserved for the **one** primary action per view; danger actions stay outlined until hover.
5. **Do NOT reintroduce `renderGraph()` inside `pointermove`.** Mutate coordinates and SVG path `d` strings directly during drag; re-render only on structural add/delete/connect.
6. **Do NOT block rendering on external fonts or add a build step / CDN JS framework.** Keep Google Fonts strictly progressive/non-blocking with strong local fallbacks and keep everything in vanilla inline CSS/JS inside `ui.html`.
7. **Do NOT dump raw `JSON.stringify` into table cells or expose raw snake_case enum keys (`lead_member`, `has_charter`) when a 2-word human label works.**
8. **Do NOT add fake KPI hero cards, decorative sparklines, or marketing copy.** This is a fast, dense operator studio — every pixel must earn its place.

---

## Ordered P0 Implementation Checklist

Follow top to bottom inside [airlangga/ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html):

1. **Replace `:root` palette & typography tokens**: Swap blue-slate/GitHub palette for Obsidian (`#0D0C0A`), Andesite (`#161411`), Teak (`#1F1C17`), Lontar Ivory (`#F4EFE6`), Limestone (`#B3AA9B`), Gold (`#D4AF37`), Terracotta (`#D96B43`), Nila (`#56B4C8`), Jade (`#4CC38A`), Vermilion (`#E55B50`). Add progressive `Fraunces` + `Plus Jakarta Sans` + `JetBrains Mono` font link, fix `h1 > h2 > h3` scale, set `line-height: 1.5`, and style `a` links + `:hover` / `:focus-visible` states globally.
2. **Fix button hierarchy & form scoping**: Change default `button` from solid `#4f8cff` to dark secondary `#242019` with `#524B3E` border; make `.danger` outlined by default; restrict `.btn-gold` to one primary CTA per screen; scope `width:100%` away from `.toolbar select`.
3. **Rebuild Header, Underline Nav, and Fixed Toast**: Remove verbose header subtitle, add geometric gold SVG emblem + `Sign out` button, switch `nav` to horizontally scrollable underline tabs (`min-height:44px`), convert `#status` to a fixed toast, and add `body.auth-pending` + branded login card to prevent unauthenticated flash.
4. **Overhaul Graph Canvas & Toolbar**: Add `#090807` dot-grid well, fix drag to mutate node position + connected SVG paths without DOM rebuild, anchor edges port-to-port (right -> left) with type-specific colors/dashes/arrowheads/haloed labels/14px hit paths, differentiate node silhouettes (`main_brain` gold double-frame, distinct type rails), fix toolbar wrapping, add `- / + / Fit` zoom + `touch-action:none`, move `Delete` into the Inspector, auto-apply inspector edits with dirty `*` indicator on `Save graph`, and restrict `+ Add node` so users don't lose unsynced nodes.
5. **Add Mobile (`<=820px` / `<=640px`) Responsive Layout**: Stack `#graphWrap`, convert `#sidePanel` into a slide-up bottom sheet on node tap, wrap all tables in `.table-wrap` (plus stacked card rows on `<640px` for Teams & Runs), enforce `16px` mobile input font-size and `44px` tap targets, and auto-fit graph on narrow viewports.
6. **Clean Up Teams, Runs, Files, Settings UX Traps**:
   - **Teams**: Collapse `Create team` behind `+ New team` gold button; fix `#mfId` duplicate-ID bug with a single dismissible member editor; tone down row delete buttons.
   - **Runs**: Fix empty-state JS bug ([L591](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L591)); replace raw JSON `Contracts` cell & `Cost by actor` `<pre>` with structured pills/tables and sub-tabs inside Run Detail.
   - **Files**: Fix folder click 400 error ([L541](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L541)); use `280px / 1fr` split with full-row clickable file items.
   - **Settings**: Give each independent section its own save button so `Save settings` stops confusing users about what it persists.
