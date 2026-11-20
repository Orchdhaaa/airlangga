  - **Scrollable Body (`#nodeForm`):** `overflow-y: auto; -webkit-overflow-scrolling: touch; overscroll-behavior: contain; flex: 1 1 auto; min-height: 0; padding: 12px 16px calc(20px + env(safe-area-inset-bottom, 0px));`. `overscroll-behavior: contain` prevents rubber-band bounce inside the inspector from scrolling `#canvasScroll` or the document behind it.
  - **Sheet Heights, Peek & Snap Detents:**
    - **Closed (default):** `transform: translateY(105%)`, `pointer-events: none`, `#sheetScrim` inactive.
    - **Default Open / Natural Peek:** `max-height: 74vh; max-height: 74dvh;` (`height: auto`). Compact items (Edge, `tool`, `skill`, `file`) naturally hug content at `~36dvh–48dvh`, keeping the top half of the graph canvas visible above the scrim; taller forms (`member`, `model`, `team`) cap at `74dvh` and scroll cleanly inside `#nodeForm`.
    - **Expanded Full-Height Detent (`.sheet-tall`):** `max-height: 92vh; max-height: 92dvh;`. Triggered when the user drags `.sheet-grabber` or `.panel-head` **upward** by `> 48px`, or double-taps `.sheet-grabber`. Dragging down `> 48px` from `.sheet-tall` returns to `74dvh` (or dismisses directly if dragged `> 140px` or fast-flicked).
  - **Grabber & Header Drag-to-Dismiss Behaviour:**
    - Attach `pointerdown` / `pointermove` / `pointerup` / `pointercancel` to `.sheet-grabber` and `.panel-head` (explicitly ignoring `ev.target.closest("#btnCloseNode")`).
    - On `pointerdown`: record `startY = ev.clientY`, `startTime = performance.now()`, `sheetH = panel.offsetHeight || 400`, set `panel.style.transition = "none"` and `scrim.style.transition = "none"`, call `setPointerCapture(ev.pointerId)`.
    - On `pointermove`: compute `dy = ev.clientY - startY`.
      - When `dy > 0` (dragging down): translate live `panel.style.transform = \`translateY(${dy}px)\`` and fade backdrop proportionally `scrim.style.opacity = String(Math.max(0, 1 - dy / sheetH))`.
      - When `dy < 0` (dragging up from default detent): apply damped upward visual cue `panel.style.transform = \`translateY(${Math.max(-24, dy * 0.25)}px)\`` to signal expandability.
    - On `pointerup` / `pointercancel`: clear inline `transition`, `transform`, and `scrim.style.opacity`. Compute velocity `vy = dy / Math.max(1, performance.now() - startTime)` (`px/ms`):
      - If `dy > 60` or `vy > 0.5`: call `closePanel()` (unless in `.sheet-tall` with `dy <= 140 && vy <= 0.5`, in which case remove `.sheet-tall` to step down to `74dvh`).
      - Else if `dy < -48` and not `.sheet-tall`: add `.sheet-tall` (`max-height: 92dvh`).
      - Else: snap back to `translateY(0)` over `200ms cubic-bezier(0.2, 0.8, 0.2, 1)`.
  - **Open / Close Triggers & Scroll Lock:**
    - **Opens automatically at `<= 820px`** on: (1) node tap (when drag movement `< 4px` and not in Connect mode), (2) edge `.hit` tap, and (3) `+ Add node` click (immediately opens the new node's inspector so the user can name/configure it).
    - **Closes** on: tapping `#sheetScrim`, tapping `#btnCloseNode` (`×`), tapping blank `#canvasScroll`, pressing `Esc`, deleting the selected node/edge, or dragging the grabber down `> 60px`.
    - **Background scroll lock:** `openPanel()` adds `document.body.classList.add("sheet-open")` (`overflow: hidden;`) on `<= 820px`, sets `role="dialog" aria-modal="true"` on `#sidePanel`, and adds `.open` to both `#sidePanel` and `#sheetScrim`. `closePanel()` removes `sheet-open`, `.open`, `.sheet-tall`, strips dialog attributes on desktop, clears `selected`, and re-renders selection highlight.
  - **Safe-Area Insets (iOS Home Indicator / Android Gesture Bar):**
    - Viewport meta MUST be `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`.
    - `#nodeForm` bottom padding: `calc(20px + env(safe-area-inset-bottom, 0px))`.
    - `#memberModal .modal-foot` and `#zipModal .modal-foot` bottom padding: `calc(12px + env(safe-area-inset-bottom, 0px))`.
    - `#status` toast resting bottom inset: `calc(12px + env(safe-area-inset-bottom, 0px))`.
  - **Virtual Keyboard Behaviour (`visualViewport`):**
    - Register a `visualViewport` `resize` + `scroll` listener. Whenever `#sidePanel.classList.contains("open")` and `window.innerWidth <= 820`:
      - Compute keyboard inset `kb = Math.max(0, window.innerHeight - window.visualViewport.height - window.visualViewport.offsetTop)`.
      - Set `#sidePanel.style.bottom = kb + "px"` and `#sidePanel.style.maxHeight = Math.min(window.visualViewport.height - 16, Math.round(window.innerHeight * 0.92)) + "px"`.
      - On `focusin` of any `input`, `select`, or `textarea` inside `#nodeForm`, schedule `setTimeout(() => ev.target.scrollIntoView({ block: "nearest", behavior: "smooth" }), 120)` so the focused field is never occluded by the software keyboard.
    - On `closePanel()` or when `kb === 0` after blur, clear inline `bottom` and `maxHeight`.
  - **Toast Stacking with Open Sheet:**
    - `#status` stays at `z-index: 40` (above `#sidePanel` at `z-index: 35`). When `body.sheet-open` is active at `<= 820px`, move `#status` to `top: 60px; bottom: auto; left: 12px; right: 12px;` so save/error feedback appears cleanly above the sheet and software keyboard.

---

### Mobile Header & Scrollable Tab Navigation (`<= 820px` & `<= 640px`)

- **Header (`header`, `52px` fixed height, `#161411`, `border-bottom: 1px solid #2E2A22`):**
  - At `<= 820px`: `padding: 0 12px; gap: 8px;`.
  - At `<= 640px`:
    - `header .sub` (`/ Studio`): `display: none;`.
    - `header h1`: `font-size: 18px;`.
    - `#tokenBadge`: displays compact `TOKEN` or `LOCAL` (`font-size: 10.5px; padding: 3px 6px;`) instead of `TOKEN ACTIVE` / `LOCALHOST` so it fits comfortably beside `Sign out` on `390px`.
    - `#btnSignOut`: `min-height: 44px; padding: 8px 10px; font-size: 13px;`.
- **Scrollable Tab Rail (`nav#tabs`, `44px` height, `#12100D`, `border-bottom: 1px solid #2E2A22`):**
  - `display: flex; flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; scroll-snap-type: x proximity; scrollbar-width: none; gap: 2px; padding: 0 12px;` (`nav::-webkit-scrollbar { display: none; }`).
  - Each tab button: `flex: 0 0 auto; white-space: nowrap; min-height: 44px; padding: 10px 12px; font-size: 13.5px; scroll-snap-align: start;`. Count badges (`Teams (N)`, `Files (N)`, `Runs (N)`) stay inline in `11px` mono `#8C8375` (`#D4AF37` when active).
  - **Right-Edge Overflow Affordance:** Wrap `nav#tabs` in `.nav-wrap` (`position: relative; background: #12100D;`) with `.nav-wrap.has-more-right::after` rendering a `28px`-wide `pointer-events: none` right gradient (`linear-gradient(to left, #12100D 20%, transparent)`) toggled on `scroll` and `resize` whenever `nav.scrollLeft + nav.clientWidth < nav.scrollWidth - 2`.
  - **Active Tab Auto-Reveal:** `switchTab(name)` calls `activeBtn.scrollIntoView({ inline: "nearest", block: "nearest", behavior: "smooth" })`.

---

### Mobile Graph Canvas, Single-Row Toolbar & Auto-Fit (`<= 820px` & `<= 640px`)

- **Canvas Well (`#canvasScroll`):**
  - At `<= 820px`: `width: 100%; height: calc(100dvh - 208px); min-height: 360px; max-height: 64dvh;` (fallback `58vh`), `touch-action: pan-x pan-y;`.
  - Wrap `#canvasScroll` inside `#canvasStage` (`position: relative; width: 100%;`) so the floating zoom pill pins to the viewport corner of the canvas and does NOT scroll away with the canvas contents.
- **Single-Row Phone Toolbar (`<= 640px`, exact `366px` budget on `390px` viewport minus `12px × 2` main padding):**
  - `.toolbar`: `flex-wrap: nowrap; gap: 6px; margin-bottom: 8px; align-items: center;`. Hide `.toolbar .vdiv`, desktop zoom buttons (`#btnZoomOut`, `#btnZoomLabel`, `#btnZoomIn`, `#btnFit`), and desktop dirty pill text (`Unsaved changes`) at `<= 640px`.
  - Exact control sizing in the single row:
    1. `.seg` (`Select` | `Connect`): each button `padding: 8px 9px; font-size: 13px; min-height: 44px;` (`~124px` total).
    2. `#btnAddNode`: `padding: 8px 10px; font-size: 13px; min-height: 44px;` showing `+ Add` (`~56px`).
    3. `#addNodeType`: `width: 84px; min-width: 78px; max-width: 96px; padding: 8px 6px; font-size: 16px; min-height: 44px;` (`84px`).
    4. `#btnSaveGraph`: `margin-left: auto; padding: 8px 12px; font-size: 13px; min-height: 44px; white-space: nowrap;` showing `Save` (clean, Secondary `#242019`) or `Save *` (dirty, Gold `#D4AF37`) below `420px` (`~74px`).
    - Total row width: `124 + 6 + 56 + 6 + 84 + 6 + 74 = 356px <= 366px` (zero wrap, zero horizontal overflow).
  - **Connect Strip on Phone:** When `Connect` mode is active at `<= 640px`, move `#edgeKind` (`width: 100%; min-height: 44px; font-size: 16px;`) into a dedicated full-width `#connectBanner` row directly beneath the toolbar: line 1 = `Connecting from <Label> — tap target node` (or `Connect mode — tap a source node`) + `Cancel` ghost button (`min-height: 44px`); line 2 = `#edgeKind` `<select>` (`Auto (by node types)` default).
- **Floating Zoom Corner Pill (`#canvasZoomPill`, visible ONLY at `<= 640px`):**
  - Anchored inside `#canvasStage` at `position: absolute; right: 10px; bottom: 10px; z-index: 12;`.
  - Styling: `display: inline-flex; align-items: center; background: rgba(22,20,17,0.94); border: 1px solid #524B3E; border-radius: 4px; box-shadow: 0 4px 16px rgba(0,0,0,0.55); overflow: hidden;`.
  - Contains 4 touch-safe buttons separated by `1px solid #2E2A22`: `−` (`44×44px`), `100%` (`min-width: 48px; height: 44px; font-family: var(--font-mono); font-size: 12px;`, resets zoom to `100%`), `+` (`44×44px`), `Fit` (`min-width: 44px; height: 44px; font-size: 12px;`).
- **Compact Mobile Legend (`#graphLegend` at `<= 640px`):**
  - Hide the desktop keyboard/drag helper span; display the 6 semantic swatches (`Brain #D4AF37`, `Team #D96B43`, `Member #56B4C8`, `Model #4CC38A`, `File #C89B54`, `Tool #9E9587`) in a compact flex-wrap strip (`gap: 6px 12px; font-size: 10.5px; padding-top: 6px;`).
- **Auto-Fit on Load, Tab Switch & Orientation Change (`<= 820px`):**
  - Trigger `requestAnimationFrame(() => fitGraph())`:
    1. Immediately after initial `loadState()` renders the Graph tab when `window.innerWidth <= 820`.
    2. Inside `switchTab("graph")` **after** `.tab.active` is applied (ensuring `#canvasScroll.clientWidth > 0`) when `window.innerWidth <= 820`.
    3. On `orientationchange` (debounced `150ms`) when Graph tab is active.
  - **`fitGraph()` Math & Scroll-Bounds Sync:**
    - Compute bounding box `(minX, minY, maxX, maxY)` across all nodes using `NODE_W[n.type]` and measured `nodeH[n.id]`.
    - Clamp scale `maxZ = window.innerWidth <= 820 ? 1.0 : 1.25`; `z = Math.max(0.25, Math.min(maxZ, (sc.clientWidth - 24) / Math.max(1, maxX - minX), (sc.clientHeight - 24) / Math.max(1, maxY - minY)))`.
    - Apply `setZoom(z)` AND update a `#canvasSizer` wrapper (`width: Math.ceil(canvasW * z) + "px"`, `height: Math.ceil(canvasH * z) + "px"`) around `#canvas` so `#canvasScroll` never leaves dead unscaled overflow whitespace after zooming out to `~30%–45%`.
    - Center scroll offsets: `sc.scrollLeft = Math.max(0, Math.round((minX - 12) * z))`, `sc.scrollTop = Math.max(0, Math.round((minY - 12) * z))`.
  - **Empty-State Card (`#graphEmptyCard`) on Phone (`<= 640px`):**
    - When `Object.keys(S.config.teams).length === 0`, place `Main Brain` at `(16, 20)` and position `#graphEmptyCard` at `left: 16px; top: 136px; width: calc(100vw - 56px); max-width: 340px;` so both are immediately readable at `100%` zoom without horizontal panning.

---

### Stacked Layout Rules Per Tab (`<= 820px` & `<= 640px`)

| Tab | `<= 820px` Layout Changes | `<= 640px` (`390px`) Phone Rules |
|---|---|---|
| **Graph** (`#tab-graph`) | `#graphWrap` stacks vertically; `#sidePanel` detaches into slide-up bottom sheet (`74dvh` / `92dvh`); auto-`fitGraph()`. | Single-row toolbar (`Select\|Connect`, `+ Add`, type select, `Save`); `#canvasZoomPill` bottom-right of canvas; `#edgeKind` inside `#connectBanner`; legend hides desktop hints. |
| **Teams** (`#tab-teams`) | `.row` grids collapse to 1 column (`min-width: 0`); `#createTeamCard` fields stack cleanly. | Team card header splits to 2 lines: line 1 = name + Template/Mode/Lead pills + `$15.00 cap`; line 2 = `2×2` action button grid (`grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px;`) for `Run team →`, `+ Add member`, `Edit team`, `Delete`. Roster table uses `.stacked` cards. `#memberModal` anchors to bottom (`border-radius: 12px 12px 0 0; max-height: 92dvh;`, sticky header, scrollable body, sticky safe-area footer with `Save member` `flex: 1` + `Cancel`). Fallback chain rows stack vertically with `44×44px` Up/Down/Remove controls. |
| **Models** (`#tab-models`) | Main Brain hero form fields stack to 1–2 columns; Custom Providers drawer 1-column. | All inputs 1-column full-width; Capabilities checkboxes in `2-column` grid (`min-height: 44px` per `.check` label); `Save Main Brain` `width: 100%`; Member Models table uses `.stacked` cards; Provider Reference `<details>` retains horizontal `.table-wrap` scroll inside its collapsed drawer. |
| **Files** (`#tab-files`) | `.files-split` switches to `grid-template-columns: 1fr; gap: 12px;`. Sidebar wraps inside `<details open id="fileTreeDrawer">` (`Files & folders (N)`). Selecting a file auto-collapses `#fileTreeDrawer` (`open = false`) and scrolls `#fileEditorCard` into view. | Quick-create stacks `#newFilePath` (line 1) over a 3-button row (`+ File`, `+ Folder`, `Import ZIP`, each `min-height: 44px; flex: 1;`). Editor header splits path + `Unsaved *` pill (line 1) over wrapped `44px` actions (`Save file`, `Attach as charter…`, `Add to graph`, `Delete`). `Attach as charter…` popover expands full-width inline beneath the header. `#fileEditor`: `font-size: 16px; min-height: 52dvh;`. `#zipModal` uses bottom-docked `92dvh` sheet layout with `min-height: 112px` tap dropzone (`accept=".zip,application/zip"`). |
| **Runs** (`#tab-runs`) | `.launchbar` wraps cleanly; Run Detail KPI strip wraps. | `.launchbar` stacks vertically (`flex-direction: column; align-items: stretch; gap: 10px;`): full-width `Team`, `Goal`, `Provider mode`, and `Run team` (`width: 100%`). Run History, Timeline, Contracts, and Cost Breakdown all use `.stacked` cards. Run Detail KPIs render in a `2-column` grid (`gap: 8px 12px`) with `44×44px` `Close ×` top-right. `.subtabs` scrolls horizontally (`flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none;`, `44px` buttons). `pre.trace`: `font-size: 11.5px; line-height: 1.45; max-height: 58dvh;`. |
| **Settings** (`#tab-settings`) | Single-column stack (`grid-template-columns: 1fr;` applies below `1024px`). Order: Telegram → Approvals & Budgets → Scheduled Jobs → Skills → Change UI Password. | Every primary/section Save button (`Save Telegram`, `Save approvals & budgets`, `Add cron job`, `Save skill`, `Change UI password`) stretches `width: 100%` (`min-height: 44px`). Cron table uses `.stacked` cards. Skill rows wrap filename/path above full-height `44px` `Edit` button. |

---

### Responsive Stacked Tables Spec (`.table-wrap.stacked` at `<= 640px`)

Every operational table (Teams Roster, Models Member Routing, Runs History, Run Detail Timeline, Run Detail Contracts, Run Detail Cost Breakdown, and Settings Scheduled Jobs) wraps in `<div class="table-wrap stacked">` and sets `data-label="<Column>"` on every `<td>` (`data-label=""` on trailing action cells):

```css
@media (max-width: 640px) {
  .stacked table, .stacked tbody, .stacked tr, .stacked td { display: block; width: 100%; }
  .stacked thead { display: none; }
  .stacked tr {
    background: #1A1713;
    border: 1px solid #2E2A22;
    border-radius: 4px;
    padding: 10px 12px;
    margin-bottom: 10px;
  }
  .stacked tr.selected-row {
    background: rgba(212,175,55,0.12);
    border-color: #D4AF37;
    box-shadow: inset 3px 0 0 #D4AF37;
  }
  .stacked td {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(46,42,34,0.55);
    text-align: right;
    min-width: 0;
    word-break: break-word;
  }
  .stacked td:last-child { border-bottom: none; padding-bottom: 0; }
  .stacked td::before {
    content: attr(data-label);
    flex: 0 0 92px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #B3AA9B;
    text-align: left;
  }
  .stacked td.cell-long { flex-direction: column; align-items: stretch; gap: 3px; text-align: left; }
  .stacked td.cell-long::before { flex: none; }
  .stacked td[data-label=""] {
    padding-top: 8px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .stacked td[data-label=""]::before { display: none; }
  .stacked td[data-label=""] button { flex: 1 1 auto; min-height: 44px; }
}
```

- Apply `.cell-long` to multi-word cells (`Goal`, `Summary`, `Goal / Outcome`, `Endpoint`) so long values read left-aligned cleanly under their uppercase label instead of squishing into a narrow right column.

---

### Touch Targets & Input Ergonomics (`<= 640px`)

- **Strict `44×44px` Minimum Tap Target:** Every interactive control — `button`, `button.small`, `nav button`, `.subtabs button`, `.file-row`, `.conn-row button`, `#btnCloseNode`, modal close `×`, `details summary`, `.check` checkbox wrappers, and `#canvasZoomPill` buttons — MUST enforce `min-height: 44px` (and `min-width: 44px` for icon-only controls).
- **Password Toggle Exception (`.pw-wrap button`):** Inputs inside `.pw-wrap` increase to `min-height: 46px; padding-right: 68px;`; the embedded `Show` / `Hide` button uses `min-height: 36px; min-width: 52px; right: 5px;` so it stays centered inside the `46px` input border without overflow.
- **Prevent iOS Safari Auto-Zoom:** `input, select, textarea { font-size: 16px; }` across all forms, toolbars, modals, and the inspector at `<= 640px`.
- **Minimum Spacing Between Touch Controls:** `gap: 8px` (`6px` inside compact graph toolbar & `2×2` team header grid) so adjacent destructive buttons (`Remove`, `Delete`) are never accidentally tapped next to `Edit` or `Save`.
- **Touch Feedback & Drag Safety:**
  - `-webkit-tap-highlight-color: rgba(212,175,55,0.16);` on interactive controls.
  - `touch-action: none;` on `.node`, `.port.out`, and `.sheet-grabber`; `touch-action: pan-x pan-y;` on `#canvasScroll`.
  - Drag threshold `>= 4px` (Euclidean screen distance) + zoom-compensated deltas (`dx / zoom`, `dy / zoom`) + `suppressNextClick` after drag prevents mobile finger drags from falsely triggering `onNodeClick` and opening the bottom sheet.

---

### Login Page on Mobile (`<= 640px`)

- **Container (`#loginScreen`):** `position: fixed; inset: 0; z-index: 50; display: none; align-items: center; justify-content: center; padding: 16px 12px calc(16px + env(safe-area-inset-bottom, 0px)); overflow-y: auto; min-height: 100dvh; background: radial-gradient(circle at 50% 0%, rgba(212,175,55,0.09), transparent 55%), #0D0C0A;`.
  - Short-viewport keyboard rule (`@media (max-height: 560px)`): switch to `align-items: flex-start; padding-top: 24px;` so the token input and `Enter Studio` button remain scrollable and visible when the phone keyboard is open.
- **Card (`.loginCard`):** `width: 100%; max-width: 400px; background: #161411; border: 1px solid #3D372C; border-top: 3px solid #D4AF37; border-radius: 4px; padding: 24px 18px;` (`32px 28px` on `> 640px`).
- **Content & Controls:**
  - `24×24px` stepped-diamond gold SVG crest + `Airlangga` (`26px` `--font-display`, `#F4EFE6`) + `AGENTIC TEAM STUDIO` (`11px` `--font-mono`, `letter-spacing: 0.14em`, `#B3AA9B`).
  - `#loginToken`: `type="password"`, `font-size: 16px`, `min-height: 46px`, `padding-right: 68px`, `autocapitalize="off" autocorrect="off" spellcheck="false"`, paired with `Show` / `Hide` button (`#btnToggleToken`, `min-height: 36px`).
  - `#loginError`: `min-height: 20px; font-size: 13px; color: #F2786D;` (`"Wrong token — try again."`, `"Enter your UI token."`, `"Cannot reach server — check connection."`).
  - `#btnLogin` (`Enter Studio`): `width: 100%; min-height: 46px; font-size: 15px; font-weight: 700; background: #D4AF37; color: #0D0C0A; border: 1px solid #D4AF37;`. During submit: disabled, label `"Signing in…"`.
  - Footer note (`12px` `#8C8375`): `"The token is stored only in this tab (sessionStorage) and never in the URL. On a public server the token is the one set as AIRLANGGA_UI_TOKEN."`

---

## 8. Implementation Checklist

### P0 — Must Ship (Build in Exact Order Below)

- [ ] **P0.1 — Visual System Rollout, Offline Typography & Auth Invariants (`airlangga/ui.html`)**
  - Lock `:root` CSS variables to exact Candi Obsidian & Lontar Studio hexes: `--bg:#0D0C0A`, `--canvas-bg:#090807`, `--nav-bg:#12100D`, `--input-bg:#11100D`, `--surface:#161411`, `--surface-2:#1F1C17`, `--surface-3:#29251E`, `--btn-sec:#242019`, `--border:#2E2A22`, `--border-strong:#3D372C`, `--border-ctrl:#524B3E`, `--border-hover:#857A66`, `--text:#F4EFE6`, `--muted:#B3AA9B`, `--subtle:#8C8375`, `--gold:#D4AF37`, `--gold-hover:#E5C558`, `--gold-tint:rgba(212,175,55,0.12)`, `--accent2:#D96B43`, `--info:#56B4C8`, `--ok:#4CC38A`, `--ochre:#C89B54`, `--pewter:#9E9587`, `--danger:#E55B50`, `--danger-text:#F2786D`, `--danger-border:#6E2D28`.
  - Use pure offline system font stacks only (ZERO `<link>` tags, ZERO webfonts, ZERO CDN URLs): `--font-display: 'Iowan Old Style','Palatino Linotype',Palatino,'Book Antiqua',Georgia,serif`, `--font-sans: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',system-ui,sans-serif`, `--font-mono: ui-monospace,'SFMono-Regular',Menlo,Monaco,Consolas,'Liberation Mono',monospace`.
  - Enforce 4-tier button classes: Gold Primary (`bg:#D4AF37; color:#0D0C0A; border:1px solid #D4AF37; hover:#E5C558; font-weight:700; min-height:36px`), Obsidian Secondary (`bg:#242019; color:#F4EFE6; border:1px solid #524B3E; hover:#2E2920/#857A66`), Ghost (`bg:transparent; color:#B3AA9B; hover:#F4EFE6/rgba(244,239,230,0.06)`), Outlined Danger (`bg:transparent; color:#F2786D; border:1px solid #6E2D28; hover:#E55B50/#0D0C0A`).
  - Add `.pill.warn` (`color:#D96B43; border-color:rgba(217,107,67,0.45); bg:rgba(217,107,67,0.12)`) and `.pill.ochre` (`color:#C89B54; border-color:rgba(200,155,84,0.45); bg:rgba(200,155,84,0.12)`) alongside `.ok`, `.run`, `.fail`, `.gold`.
  - Use inline `14×14px`–`20×20px` stroke SVGs (`stroke="currentColor" stroke-width="1.6" fill="none"`) for brand crest, upload, file, folder, warning, and close; zero emoji icons; zero `backdrop-filter: blur()`.
  - Keep `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`, `body.auth-pending` FOUC guard, fixed toast `#status` (`z-index:40`, `4500ms` neutral/ok, `7000ms` error), and all test-checked auth elements (`#loginScreen`, `#loginForm`, `#loginToken`, `#btnLogin`, `"Enter Studio"`, `"Wrong token"`, `sessionStorage` only — zero occurrences of the string `localStorage` anywhere in `ui.html`).

- [ ] **P0.2 — Bidirectional Graph Persistence (`airlangga-graph.json` ↔ `airlangga.yaml`) (`airlangga/web_ui.py`)**
  - Update `UIStore.default_graph(config)`: deduplicate identical `(provider, model, endpoint, auth_ref)` tuples into shared `model:<slug>` nodes (connected via `uses_model` from every member sharing that endpoint) and add Main Brain's model node connected via `powers` (`model → main_brain`).
  - Preserve `_sync_graph()` invariant: never drop any node stored in `airlangga-graph.json` on load (saved positions and user-added draft nodes always survive reload).
  - Upgrade `UIStore.apply_graph_to_config(graph)` on `POST /api/graph` to persist ALL graph edits back to `airlangga.yaml` and canonicalize provisional node IDs:
    - **Main Brain:** update `config.main_brain` from `main_brain` node `data` and any connected `model` node (`powers` → `main_brain` or `main_brain` → `uses_model`).
    - **Teams:** for every `team` node, slugify its label (`re.sub(r"[^a-z0-9_-]+", "-", label.lower()).strip("-")`). If absent from `config.teams`, create a `TeamConfig(template=data.get("template") or "research", goal=data.get("goal",""), team_brain_mode=data.get("team_brain_mode") or "lead_member", lead_member=data.get("lead_member"), team_budget=...)`; if present, update those fields. Rewrite provisional `team:<ts>` ID to canonical `team:<slug>` and update all edge `from`/`to` references before saving `airlangga-graph.json`.
    - **Members:** for every `member` node with an incoming `has_member` edge from a `team` node, slugify `member_id` from label; create a new `MemberConfig` (using connected `model` node or safe `mock` defaults) if new, or move/update existing member (`role`, `approval`, `budget`) in that team; auto-set `team.lead_member` if `lead_member` mode and unset; rewrite provisional `member:<ts>` ID to canonical `member:<team>:<member_id>`. Keep disconnected (`UNASSIGNED`) member nodes in `airlangga-graph.json` without failing validation.
    - **Authoritative Edge Reconciliation (close Edge Resurrection Trap):** for every config-backed `member` node in `graph["nodes"]`, recompute its `charter_file` (from outgoing `has_charter`), `attached_files` (from outgoing `has_file`), `toolsets` (from outgoing `uses_tool` merged with `node.data.toolsets`), and `skills` (from outgoing `uses_skill` merged with `node.data.skills`), plus model fields from outgoing `uses_model` OR incoming `powers` edge. Deleting an edge in the graph and saving now removes it from `airlangga.yaml` so `_sync_graph` never resurrects it on reload.
  - Ensure `POST /api/graph` persists the canonicalized graph and returns `200 {"ok": true, "graph": <canonical_graph>}`.

- [ ] **P0.3 — Graph Visuals: 8 Distinct Node Types, Port-to-Port Type-Coloured Edges & Auto-Inferred Connect (`airlangga/ui.html`)**
  - Dynamic canvas bounds on structural render: `canvasW = Math.max(1600, maxNodeX + 280)`, `canvasH = Math.max(900, maxNodeY + 260)` applied to both `#canvas` and `#edges` SVG (`background: #090807`, `radial-gradient(#2A251D 1px, transparent 1px)` at `20px 20px`).
  - Style all 8 node types distinctly with `10×10px` `.port.in` (`left:-6px`) and `.port.out` (`right:-6px`):
    - `main_brain`: `216px`, `bg:#1C1810`, `1.5px solid #D4AF37`, `border-left:4px solid #D4AF37`, inner double-frame `inset 0 0 0 3px #0D0C0A, inset 0 0 0 4px rgba(212,175,55,0.35)`, `SOVEREIGN` micro-tag.
    - `team`: `204px`, `bg:#1C1714`, `border-left:3px solid #D96B43`, `DRAFT` ochre badge if not in `S.config.teams`.
    - `member`: `204px`, `bg:#181A1C`, `border-left:3px solid #56B4C8`, `LEAD` gold badge if team lead, `UNASSIGNED` ochre badge if no incoming `has_member` edge.
    - `model`: `208px`, `bg:#151B18`, `border-left:3px solid #4CC38A`, mono `<provider> · $<cost>/M`, `×N` tag when powering `>= 2` nodes.
    - `file`: `192px`, `bg:#1B1813`, `border-left:3px solid #C89B54`, `border-radius:4px 14px 6px 6px`, `CHARTER` ochre badge if target of `has_charter`.
    - `folder`: `192px`, `bg:#1A1712`, `1px dashed #6B5736`, `border-left:3px solid #C89B54`, `border-radius:4px 14px 6px 6px`.
    - `tool`: `152px`, `bg:#1A1815`, `1px dashed #524B3E`, `border-left:3px solid #9E9587`, `radius:3px`, `padding:7px 9px`.
    - `skill`: `156px`, `bg:#1A1815`, `1px dashed #6E6557`, `border-left:3px solid #B3AA9B`, `radius:3px`, `padding:7px 9px`, `SKILL` micro-tag.
  - Render all 9 port-to-port Bezier edge kinds (`M x1,y1 C mx,y1 mx,y2 x2,y2`, flipping `left ↔ right` when source center X > target center X) with `14px` transparent `.hit` path, `8×8` color-matched SVG `<marker>`, and `#0D0C0A` halo pill (`rx="3"`, `stroke="#2E2A22"`, `10px` `#B3AA9B` label):
    - `assigns` (`"assigns"`): `#D4AF37`, `2.2px`, solid, `arr-gold`
    - `powers` (`"powers"`): `#D4AF37`, `2.2px`, solid, `arr-gold`
    - `has_member` (`"member"`): `#D96B43`, `1.8px`, solid, `arr-terra`
    - `uses_model` (`"uses model"`): `#4CC38A`, `1.8px`, solid, `arr-jade`
    - `has_charter` (`"charter"`): `#C89B54`, `1.8px`, solid, `arr-ochre`
    - `has_file` (`"attaches file"`): `#C89B54`, `1.8px`, `dasharray="2 4"`, `arr-ochre`
    - `uses_tool` (`"tool"`): `#857A66`, `1.5px`, `dasharray="4 3"`, `arr-pewter`
    - `uses_skill` (`"skill"`): `#B3AA9B`, `1.5px`, `dasharray="4 3"`, `arr-pewter`
    - `depends_on` (`"depends on"`): `#56B4C8`, `1.6px`, `dasharray="5 4"`, `arr-cyan`
  - Dim unrelated edges to `opacity: 0.22` when a node is selected; highlight selected edge with `stroke-width + 1.2` and `#D4AF37` halo stroke.
  - Add `<option value="auto">Auto (by node types)</option>` as the default in `#edgeKind`: auto-infer edge kind from `(source.type, target.type)`, flip reversed pairs (`file → member`, `tool → member`, `skill → member`, `member → team`) to canonical direction, and block self-loops (`from === to`) or exact duplicate `(from, to, kind)` edges with toast `"Connection already exists."` / `"Cannot connect a node to itself."`.
  - Make `+ Add node` place nodes in the visible center of `#canvasScroll` (`x = Math.round((sc.scrollLeft + 140) / zoom) + (count % 5) * 28`, `y = Math.round((sc.scrollTop + 100) / zoom) + (count % 5) * 28`), populate type-appropriate `data` defaults, select the new node, and mark dirty.
  - Toggle `#btnSaveGraph` between Secondary (`"Save graph"`, `#242019`) when clean and Gold Primary (`"Save graph *"`, `#D4AF37`) when dirty.
  - For config-backed `team` / `member` nodes deleted in the inspector, prompt confirmation (`"Delete member '<id>' from team '<team>' and airlangga.yaml?"`) and call `DELETE /api/teams/<team>` or `DELETE /api/teams/<team>/members/<id>` so deleted nodes never resurrect on reload.

- [ ] **P0.4 — Zero-DOM-Rebuild Zoom-Compensated Graph Drag (`airlangga/ui.html`)**
  - Rewrite `startDrag(ev, n, div)` to ignore `.port.out` clicks (reserved for desktop port-drag), capture `startClientX = ev.clientX`, `startClientY = ev.clientY`, `origX = n.x`, `origY = n.y`, `dragged = false`.
  - On `pointermove`: check `Math.hypot(ev.clientX - startClientX, ev.clientY - startClientY) >= 4`; once crossed, set `dragged = true`, compute zoom-compensated coordinates `n.x = Math.max(16, Math.round(origX + (ev.clientX - startClientX) / zoom))`, `n.y = Math.max(16, Math.round(origY + (ev.clientY - startClientY) / zoom))`, and mutate ONLY `div.style.left`, `div.style.top`, and `updateEdgesFor(n.id)` — ZERO `renderGraph()` or `drawEdges()` DOM rebuilds during drag.
  - On `pointerup` / `pointercancel`: remove window listeners; if `dragged`, set `suppressNextClick = true` (reset via `queueMicrotask(() => { suppressNextClick = false; })`), call `setDirty(true)`, and expand `#canvas`/`#edges` bounds if `n.x + 280 > canvasW` or `n.y + 260 > canvasH`. In `onNodeClick`, return immediately if `suppressNextClick` is true.

- [ ] **P0.5 — Backend ZIP Import Endpoint & Binary File Guard (`airlangga/web_ui.py`)**
  - Define module-level security constants: `ZIP_MAX_UPLOAD_BYTES = 10 * 1024 * 1024`, `ZIP_MAX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024`, `ZIP_MAX_FILES = 200`, `ZIP_MAX_RATIO = 100`.
  - Add `POST /api/files/import-zip` route in `do_POST` (requiring `_require_auth()` → `401 {"error": "unauthorized: set the X-Airlangga-Token header"}`), parsing query params `dest` (default `""`, trimmed of leading/trailing `/`, validated via `store.resolve_file(dest)` when non-empty) and `overwrite` (`"1"` → `True`, default `"0"` → `False`).
  - Implement atomic Phase 1 validation in memory BEFORE writing any bytes to disk:
    1. Reject `Content-Length > ZIP_MAX_UPLOAD_BYTES` immediately with `413 {"error": "ZIP file exceeds the 10 MB upload limit.", "code": "zip_too_large", "max_bytes": 10485760}` without reading the full request body.
    2. Read `raw` bytes; reject `len(raw) < 4` or `raw[:4] not in (b"PK\x03\x04", b"PK\x05\x06")` or `zipfile.BadZipFile` with `415 {"error": "File is not a valid ZIP archive.", "code": "not_a_zip"}`.
    3. For every `ZipInfo` in `zf.infolist()`: normalize `\\` → `/`; silently skip and count `ignored_metadata` for `__MACOSX`, `__MACOSX/*`, `.DS_Store`, `Thumbs.db`; reject `info.flag_bits & 0x1` → `400 {"error": "...", "code": "encrypted_entry", "entry": raw_name}`; reject Unix symlinks `((info.external_attr >> 16) & 0o170000) == 0o120000` → `400 {"error": "...", "code": "symlink_entry", "entry": raw_name}`; reject leading `/`, Windows drive `^[A-Za-z]:`, `\x00`, or `".."` path segment → `400 {"error": "...", "code": "path_traversal", "entry": raw_name}`; check `is_write_denied(rel)` → `400 {"error": "...", "code": "credential_path", "entry": raw_name}`; verify `store.resolve_file(rel)` stays under `files_root` → `400 {"error": "...", "code": "path_traversal", "entry": raw_name}`; reject `file_count > 200` → `400 {"error": "...", "code": "too_many_files"}`; reject `declared_total > 25 MB` → `413 {"error": "...", "code": "uncompressed_too_large"}`; reject `info.file_size > 1_048_576 and (info.compress_size == 0 or info.file_size / info.compress_size > 100)` → `400 {"error": "...", "code": "zip_bomb_ratio", "entry": raw_name}`.
  - Implement Phase 2 under `self._lock`: stream-decompress each validated file in chunks while enforcing actual total extracted bytes `<= 25 MB`; skip existing target when `overwrite=False` (append to `skipped`), otherwise write and append `{"path": rel, "size": len(data)}` to `extracted`; return `200 {"ok": True, "dest": dest, "extracted": [...], "skipped": [...], "ignored_metadata": N, "total_bytes": B}`.
  - Update `UIStore.read_file()` / `GET /api/files?path=...`: catch `UnicodeDecodeError` and return `400 {"error": "Binary file cannot be edited as text.", "binary": True, "size": target.stat().st_size}` instead of HTTP `500`.

- [ ] **P0.6 — Frontend ZIP Import Modal, Drag-Drop & File Manager Upgrades (`airlangga/ui.html`)**
  - Add `Import ZIP` secondary button (with `14×14px` upload SVG) in the Files sidebar header and make `#fileTree` a `.zip` drag-and-drop zone (`2px dashed #D4AF37` overlay: `"Drop .zip archive to import into files/"`).
  - Build `#zipModal` (`z-index:45`, `rgba(0,0,0,0.62)` scrim, `max-width:520px`, `bg:#161411`, `border:1px solid #524B3E`):
    - Header: `"Import ZIP into files/"` + `×` close button (`44×44px` on mobile).
    - Dropzone `#zipDropzone` (`border:1.5px dashed #524B3E; bg:#11100D; padding:24px 16px;`, dragover `#D4AF37` / `rgba(212,175,55,0.06)`): `"Choose a .zip file or drop it here"` + `"Max 10 MB upload · Max 25 MB extracted · Max 200 files · Unsafe paths and credentials are blocked"`.
    - Client pre-checks before enabling `Upload & extract` (Gold): non-`.zip` → `#F2786D` `"Only .zip archives are supported."`; `> 10 MB` → `"Archive is <X> MB — maximum upload size is 10 MB."`.
    - Fields: `#zipDest` (`"Extract into folder (optional)"`, placeholder `"packs/superagent (leave empty for files/ root)"`), `#zipOverwrite` (`"If a file already exists"`: `0` `"Skip existing files (safe)"`, `1` `"Overwrite existing files"`).
    - Upload state: button `"Extracting…"` (disabled), `Cancel` disabled, `2px` `#D4AF37` animated bar under modal header; `fetch("/api/files/import-zip?dest=...&overwrite=...", { method:"POST", headers: { "Content-Type":"application/zip", "X-Airlangga-Token": token(), "X-Filename": file.name }, body: file })`.
    - Success state (`200`): jade box (`border:1px solid rgba(76,195,138,0.45); bg:rgba(76,195,138,0.08)`), headline `"Extracted <N> file(s) (<formatted total_bytes>) into files/<dest or root>"`, optional sub-line `"Skipped <M> existing file(s) · Ignored <K> macOS/system metadata entries"`, scrollable `max-height:220px` list with mono path + size + `Open` ghost button, silent `loadState()` refresh, footer `Import another ZIP` (secondary) + `Done` (gold).
    - Error state (`400`/`413`/`415`): vermilion box (`border:1px solid #E55B50; bg:rgba(229,91,80,0.10)`), headline `"Import blocked — no files were written"`, mapped plain-English message for all 9 error codes (`path_traversal`, `credential_path`, `symlink_entry`, `not_a_zip`, `zip_too_large`, `uncompressed_too_large`, `too_many_files`, `zip_bomb_ratio`, `encrypted_entry`) + `<code>entry</code>`, footer `Choose another file` (secondary) + `Close` (ghost).
  - Add Files editor upgrades: `Save file` Gold-when-dirty / Secondary-when-clean + `"Unsaved *"` ochre pill, unsaved-change `confirm("Discard unsaved changes to <path>?")` when switching files, folder row `×` delete button (surfaces `"Folder is not empty; delete its files first."`), binary-file preview card (`"<filename> is a binary file (<size>) and cannot be edited as text. You can still attach it to a team member or delete it."` + `Delete file` danger button), and footer stats (`<lines> lines · <chars> chars · <size> · UTF-8 · Cmd/Ctrl+S to save`).

- [ ] **P0.7 — Fix Member Save `skills: []` Wipe Bug & Real SUPERAGENT Charter Injection (`airlangga/ui.html`, `airlangga/brain.py`, `airlangga/team.py`, `airlangga/web_ui.py`)**
  - Fix `saveMember()` in `ui.html` so `PUT /api/teams/<t>/members/<m>` preserves and submits `skills` (checked from `/api/skills`), `attached_files`, `capabilities`, `cost_per_mtok_usd`, `context_limit`, `fallback`, and `routing_policy` — NEVER hardcoding `skills: []`.
  - Expose `Charter file` `<select>` (+ `"Create charter in Files →"` link), `Attached files` multi-checkboxes, `Skills` multi-checkboxes, `Capabilities` multi-checkboxes, `Cost ($/Mtok)`, `Context limit`, and `Wire format` inside `#memberModal`.
  - Add 1-click `Attach as charter…` ghost button in the Files editor header: opens compact inline popover with `<select>` of all `<team> / <member>` pairs + `Attach` secondary button → sends `PUT /api/teams/<team>/members/<member>` with `{ charter_file: editingFile }` + toast `"Attached <file> as charter for <team> / <member>."`.
  - Update `member_prompt(member, contract_goal, files_root=None)` in `airlangga/brain.py`: when `member.charter_file` and `files_root` are set, resolve safely inside `files_root` (rejecting traversal / `is_write_denied`), read UTF-8 text (truncating at `16,384` bytes with `\n[Charter truncated at 16 KB]`), prepend `--- PERSONA CHARTER (<charter_file>) ---\n<content>\n--- END CHARTER ---\n\n`, and append available `member.attached_files` list if non-empty.
  - Pass `files_root=self.files_root` from `UIStore.start_run()` to `TeamRuntime(..., files_root=...)` in `airlangga/team.py`, pass it to `member_prompt()`, and include `"charter_file": record.config.charter_file` in the member activation `member_state` (`WORKING`) ledger event so Runs displays `"Charter active: superagent.md"`.

- [ ] **P0.8 — Settings Dirty-Aware Per-Section Save & Skill Validation Before Write (`airlangga/ui.html`, `airlangga/web_ui.py`)**
  - Arrange `#tab-settings` in a 2-column CSS grid (`grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px;`) at `>= 1024px`, single column `< 1024px`.
  - Demote `Save Telegram` and `Save approvals & budgets` to Obsidian Secondary (`#242019`) at rest; track `dirtySections = { telegram: false, budgets: false }` on input/change, show `.pill.ochre` `"Unsaved"` next to the card title, and promote ONLY that section's Save button to Gold (`#D4AF37`).
  - Update `saveSettingsSection(sectionKey, mut, okMsg)` to clone `S.settings`, apply ONLY `mut(body)`, send `PUT /api/settings`, store `S.settings = res.settings`, clear ONLY `dirtySections[sectionKey]`, and re-render ONLY that section (NEVER calling full `loadState()` or re-rendering untouched Settings cards, so saving Telegram never wipes unsaved edits in Approvals & Budgets or vice versa).
  - Validate Telegram allowlist entries as comma-separated positive integers (flag non-numeric tokens inline `#F2786D` instead of silently dropping); show inline `#C89B54` warning `"Approval Off is intended only for disposable or sandboxed hosts."` when `approval_default === "off"`; show `"Configured"` (`.pill.ok`) / `"Not set"` (`.pill`) on Telegram card; disable Change UI Password inputs with `"Running in localhost mode with no UI token set. Restart with AIRLANGGA_UI_TOKEN to enable password login."` when `token()` is empty.
  - Fix `PUT /api/skills` in `airlangga/web_ui.py`: run `scan_skill_text(content)` and `Skill.model_validate(yaml.safe_load(content))` in memory BEFORE writing `target.write_text(...)` so rejected/malformed YAML never leaves a broken file in `airlangga/skills/`.

- [ ] **P0.9 — Mobile Bottom-Sheet Inspector, Single-Row Graph Toolbar, Stacked Tables & 44px Ergonomics (`airlangga/ui.html`)**
  - Add `#sheetScrim` (`rgba(0,0,0,0.58)`, `z-index:34`) and convert `#sidePanel` at `<= 820px` into a slide-up bottom sheet (`z-index:35`, `max-height:74dvh`, `.sheet-tall` `92dvh`, `border-top:1px solid #524B3E`, `border-radius:12px 12px 0 0`, `box-shadow:0 -8px 32px rgba(0,0,0,0.72)`, `transform:translateY(105%)` → `translateY(0)` over `200ms cubic-bezier(0.2,0.8,0.2,1)`).
  - Add `.sheet-grabber` (`height:22px`, centered `36×4px` `#524B3E` pill) with pointer drag-to-dismiss (`dy > 60px` or `vy > 0.5 px/ms`) and drag-up expand (`dy < -48px` → `.sheet-tall`), sticky `.panel-head` (`min-height:48px`, `44×44px` `×` close button), scrollable `#nodeForm` (`overscroll-behavior:contain`, `padding-bottom:calc(20px + env(safe-area-inset-bottom, 0px))`), `visualViewport` keyboard lift/resize handler, `body.sheet-open` background scroll lock, and top-anchored `#status` (`top:60px`) while sheet is open.
  - Open `#sidePanel` automatically at `<= 820px` on node tap (`< 4px` drag), edge tap, and `+ Add node`.
  - Implement `<= 640px` single-row Graph toolbar (`Select|Connect` `~124px`, `+ Add` `~56px`, `#addNodeType` `84px`, `Save`/`Save *` `~74px`, total `356px <= 366px`) + `#canvasZoomPill` floating bottom-right corner control (`−`, `100%`, `+`, `Fit`, `44×44px` buttons, `z-index:12`) + `#edgeKind` inside `#connectBanner`.
  - Auto-run `requestAnimationFrame(() => fitGraph())` at `<= 820px` on initial `loadState()`, `switchTab("graph")`, and debounced `orientationchange`, syncing `#canvasSizer` dimensions to scaled `canvasW * zoom × canvasH * zoom`.
  - Enforce `<= 640px` phone rules: `font-size: 16px` on all `input, select, textarea`; `min-height: 44px` on all buttons, tabs, file rows, summaries, and checkbox labels (`36px` inside `46px` `.pw-wrap`); `.table-wrap.stacked` card rows with `data-label` on all 7 operational tables; bottom-docked `92dvh` `#memberModal` and `#zipModal` with sticky header/footer; collapsible `<details open id="fileTreeDrawer">` on Files that auto-collapses when opening a file; mobile Login card (`padding:24px 18px`, `26px` wordmark, `46px` token input & `Enter Studio` CTA, `max-height:560px` keyboard-safe alignment).

- [ ] **P0.10 — End-to-End Backend & Persistence Test Suite (`tests/test_web_ui.py`)**
  - Add tests for `POST /api/files/import-zip`: valid multi-file ZIP extraction (`200`), `dest` subfolder extraction, `overwrite=0` skip vs `overwrite=1` overwrite, `__MACOSX`/`.DS_Store` ignored, unauthenticated `401`, and zero-files-written atomic rejection for `path_traversal` (`../evil`, `/etc/passwd`), `credential_path` (`.env`, `.ssh/id_rsa`), `symlink_entry`, `not_a_zip` (`415`), `zip_too_large` (`413`), `uncompressed_too_large` (`413`), `too_many_files` (`400`), `zip_bomb_ratio` (`400`), and `encrypted_entry` (`400`).
  - Add test for `GET /api/files?path=<binary>` returning `400` with `binary: true`.
  - Add tests verifying graph-added `team` + `member` + `has_member` + `powers`/`uses_model` + `has_charter` + `uses_tool` + `uses_skill` persist through `POST /api/graph` → `airlangga.yaml` → reload, and deleting a `has_charter` or `uses_tool` edge removes it from `airlangga.yaml` without resurrection.
  - Add test verifying per-section `PUT /api/settings` preserves all untouched sections (`telegram`, `approval_default`, `budgets`, `cron`, `custom_providers`).
  - Add test verifying `member_prompt()` injects `files/superagent.md` charter text and blocks traversal charter paths.
  - Run full `pytest` and verify 100% pass with zero regressions on existing `test_web_ui.py` tests.

---

### P1 — Real UX Wins (High Operator Leverage)

- [ ] **P1.1 — Capability-Gated Fallback Chain Builder & Raw API-Key Paste Guard (`airlangga/ui.html`)**
  - Add Section 3 in `#memberModal`: `Required capabilities` (`routing_policy.require` checkboxes), `Routing preference` (`Cheapest above quality floor` | `Local first`), and ordered Fallback Chain Builder (`1.`, `2.`, … with Provider, Model, Endpoint, Auth ref, Capabilities checkboxes, Up/Down reorder, `×` Remove, `+ Add fallback`).
  - Compute live Capability Gate Pill on every fallback row: all required caps present → `.pill.ok` `"ELIGIBLE"` (`#4CC38A`); missing `>= 1` required cap → `.pill.warn` `"WILL SKIP — missing <cap>"` (`#D96B43`).
  - Add inline raw-key paste guard on every `Auth ref` input (Member modal, Main Brain, Graph model inspector, Custom provider form): match `/^(sk-|ghp_|xox|AIza)/i` and show `.is-invalid` (`#E55B50`) + `"Do not paste raw API keys here — use env:VAR_NAME."`, blocking submit until corrected.

- [ ] **P1.2 — Custom `base_url` Providers Registry & In-Place Models Editing (`airlangga/ui.html`, `airlangga/web_ui.py`)**
  - Add Card 2 on `#tab-models`: saved custom providers list with `Remove` outlined danger button + collapsible `+ Add custom provider` form (`Provider slug`, `Display label`, `Wire format` [`OpenAI Chat` / `Anthropic Messages` / `Google Gemini`], `Base URL`, `Auth ref`, `Default models`, `Capabilities`) saving to `settings.custom_providers` via `PUT /api/settings`.
  - Merge `settings.custom_providers` into the `providers` array returned by `GET /api/state` and `GET /api/providers` in `web_ui.py` so custom endpoints (vLLM, LiteLLM, Groq, Together) immediately populate every Provider `<select>` across Graph, Teams, and Models.
  - Change Models table `Edit` button to open `#memberModal` **in place** without tab-switching to Teams, and replace raw fallback text with eligibility summary pills (`"—"`, `.pill.ok` `"2 eligible"`, or `.pill.warn` `"1 eligible · 1 skipped"`).

- [ ] **P1.3 — Plain-English Run Failure Banners, `Contracts` Sub-Tab & Humanized Trace (`airlangga/ui.html`)**
  - Render `#runErrorBanner` (`border:1px solid #E55B50; border-left:3px solid #E55B50; bg:rgba(229,91,80,0.08); padding:12px 14px; border-radius:4px`) inside `#runDetailCard` whenever `d.status === "failed"` or `d.error` is non-empty, translating raw errors via `humanizeRunError()` (`auth_ref` → `"Missing API key: <VAR>"`, `NoCapableModel` → `"No eligible model met required capabilities"`, `BudgetExceeded` → `"Run stopped — budget cap reached"`, `ContextBudgetExceeded` → `"Prompt exceeded member context budget"`, `ConnectError`/`Timeout` → `"Could not reach model endpoint"`, fallback → `"Run failed before completion"`) + collapsed `<details>Technical detail</details>`.
  - Map all 10 ledger event types to human labels and plain-English summaries (never `JSON.stringify()` in summary column): `plan_created` → `Plan created`, `contract_created` → `Contract issued`, `contract_completed` → `Contract passed`, `contract_failed` → `Contract failed`, `member_state` → `Member status`, `cost` → `Usage & cost`, `blackboard_committed` → `Committed to blackboard`, `fallback_switch` → `Fallback switched` (`.pill.ochre`), `dissent` → `Dissent recorded` (`.pill.warn`), `policy_denied` → `Policy blocked` (`.pill.fail`), with opt-in `<details><summary>Payload</summary>`.
  - Add `Contracts (N)` sub-tab (`Contract ID`, `Member`, `Status` pill `Passed`/`Failed`/`Open`, `Goal / Outcome`), upgrade `Dissents (N)` to `3px solid #D96B43` cards (`"No dissents — the team reached agreement."` when empty), render Run History contract status pills (`"3 passed"` `.ok`, `"1 failed · 2 passed"` `.fail`, `"2 open"` `.run`), update open `#runDetailCard` live during `1500ms` polling, and clear `runPoll` cleanly in `signOut()`.

- [ ] **P1.4 — Starter Member Seeding & Fast Team Formation (`airlangga/ui.html`, `airlangga/web_ui.py`)**
  - Add `blank` template option, `Team budget (USD)` input (default `15`), and checked-by-default `#newTeamSeed` checkbox (`"Seed starter members from template"`) to `#createTeamCard`.
  - Support `seed_members: true` in `POST /api/teams` (`web_ui.py`) to auto-seed starter rosters (`research`: `researcher`, `fact_checker`, `writer`; `code-review`: `coder`, `reviewer`, `tester`; `content`: `drafter`, `editor`, `fact_checker`) with sensible `toolsets`, `approval: "smart"`, and `mock` defaults so a new team is runnable in `< 60s`.
  - Add `lead_member` `<select>` and `team_budget` to inline `Edit team`, `LEAD` gold micro-pill and `$15.00 cap` mono tag to Team cards, and clickable Charter links in the Roster table that jump to `#tab-files` and open that charter file.

- [ ] **P1.5 — Brand-New User Graph Onboarding Card & Complete Node/Edge Inspector (`airlangga/ui.html`)**
  - Render `#graphEmptyCard` (`bg:#161411; border:1px solid #3D372C; border-left:3px solid #D4AF37; padding:18px; width:340px;`) when `Object.keys(S.config.teams).length === 0`: title `"Build your first Agentic Team"`, `"Create first team"` (Gold) + `"+ Add Team node"` (Secondary, inserts `team` wired via `assigns` from `main_brain` and opens inspector).
  - Complete inspector fields & actions for all 8 node types + Edge: `main_brain` (`"Edit full settings in Models →"`, non-deletable), `team` (`lead_member`, `team_budget`, `"Run team →"`), `member` (`"Edit model & fallbacks →"`, auto-syncing `has_charter` edge when `#nfCharter` changes, `UNASSIGNED` ochre note `"Connect a Team → this Member to save it to airlangga.yaml."`), `model` (Capabilities checkboxes), `file`/`folder` (`<select>` from `S.files` + `"Open in Files editor →"` + `"Removes node from graph only — the file on disk is kept."`), `tool`/`skill` (`<select>` from `S.toolsets` / `/api/skills`), Edge Inspector displaying human node labels (never raw `member:research-01:researcher` IDs), and clickable `Connections (N)` list jumping selection to connected nodes.

- [ ] **P1.6 — Skills In-UI Read/Edit, Files Badges & Password Show/Hide Everywhere (`airlangga/web_ui.py`, `airlangga/ui.html`)**
  - Extend `GET /api/skills` in `web_ui.py` to accept `?name=<file.yaml>` and return `{"name": name, "content": text}` (validating plain filename, no `/` or `..`); add `Edit` ghost button on every skill row in Settings to load into `#skillEditorDrawer`.
  - Add `Add to graph` ghost button in Files editor header (adds/focuses `file:<editingFile>` node on Graph and switches tab), `CHARTER` ochre micro-pill on charter-referenced files in `#fileTree`, human byte formatting (`480 B`, `2.4 KB`, `1.2 MB`), and `.pw-wrap` Show/Hide toggles on Telegram Bot token (`#tgToken`) and all 3 Change UI Password inputs (`#uiCurToken`, `#uiNewToken`, `#uiNewToken2`).

---

### P2 — Polish

- [ ] **P2.1 — Desktop Port-Drag Wiring (`airlangga/ui.html`)**
  - On desktop (`pointerType !== "touch"`), `pointerdown` on `.port.out` (`cursor: crosshair`) draws a live dashed `#56B4C8` SVG `<path id="dragWire">` to cursor coordinates `(clientX - canvasRect.left) / zoom`, highlights hovered target `.node` with `.connect-hover` (`border-color:#4CC38A; box-shadow:0 0 0 2px rgba(76,195,138,0.28)`), and creates the auto-inferred canonical edge on `pointerup` over another node.

- [ ] **P2.2 — Graph Keyboard Shortcuts, Tab Count Badges & Unsaved-Changes Guard (`airlangga/ui.html`)**
  - Bind Graph keyboard shortcuts when `#tab-graph.active` and focus is outside `input`/`select`/`textarea`: `Esc` (cancel Connect mode → close inspector), `C` (toggle Connect mode), `F` (`fitGraph()`), `Delete`/`Backspace` (delete selected node/edge with YAML confirmation when config-backed), `Cmd/Ctrl + S` (save graph).
  - Add live mono count badges on `nav#tabs`: `Teams (N)`, `Files (N)`, `Runs (N)` (`11px` mono `#8C8375`, `#D4AF37` when active).
  - Register `window.addEventListener("beforeunload", ...)` warning when `graphDirty`, `fileDirtyFlag`, or any `dirtySections` flag is `true`.

- [ ] **P2.3 — Mobile Nav Overflow Fade, Loading Skeletons & HTTP VPS Clipboard Fallback (`airlangga/ui.html`)**
  - Add `.nav-wrap.has-more-right::after` (`28px` `linear-gradient(to left, #12100D 20%, transparent)`) on `nav#tabs` and auto-scroll active tab into view (`scrollIntoView({ inline: "nearest" })`).
  - Add crisp loading placeholders across every screen (`"Loading workspace graph…"`, two `76px` `#1F1C17` bars on Teams, `"Loading files…"` / `"Opening <path>…"`, `"Loading run history…"` / `"Loading run trace…"`, disabled inputs `"Loading settings…"`).
  - Add fallback for `Copy trace` when `navigator.clipboard` is unavailable over plain `http://<VPS_IP>:8100` (off-screen `<textarea>` + `select()` + `document.execCommand("copy")`) so copying traces works on non-HTTPS VPS hosts.

- [ ] **P2.4 — Dialog Semantics, Focus Restoration & Keyboard Accessibility (`airlangga/ui.html`)**
  - Add `role="dialog" aria-modal="true"` and `aria-labelledby` to `#memberModal`, `#zipModal`, and open mobile `#sidePanel`; add `role="status" aria-live="polite"` to `#status` toast; close `#memberModal` and `#zipModal` on `Esc` and restore focus to the button that opened them; enforce `outline: 2px solid #D4AF37; outline-offset: 2px;` (`#E55B50` for `.danger`) on `:focus-visible` across every focusable element.
