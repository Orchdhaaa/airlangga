## 1. Diagnosis of the overlap (Issue 1a)

**Offending rules** in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L55-L56) and [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L257):

```css
/* Base (lines 55–56) */
.row { display:flex; gap:12px; flex-wrap:wrap; }
.row > * { flex:1; min-width:220px; }

/* Mobile (line 257, inside @media (max-width: 640px)) */
.row > * { min-width:0; }
```

**Why it collapses at ~390px:**
`flex: 1` expands to `flex: 1 1 0%` (`flex-basis: 0%`). On desktop (`> 640px`), `min-width: 220px` clamps each item's hypothetical main size up to `220px`, which is the **only** thing causing `flex-wrap: wrap` to break fields onto multiple rows (2 columns in the 640px modal, 3–5 columns on a wide screen).

At `<= 640px`, `.row > * { min-width: 0; }` removes that `220px` floor while leaving `flex-basis: 0%` intact. Every child's hypothetical width drops to `0px`, so the combined width of all 9 fields in Main Brain (`9 × 0px + 8 × 12px gap = 96px`) is smaller than the ~336px card width. `flex-wrap: wrap` therefore **never wraps**: all 9 Main Brain fields (Screenshot 1) and all 8 Member "Model & cost" fields (Screenshot 2) are crammed onto **one single horizontal row** (~27px–33px per column). Labels overflow their 27px box horizontally and collide into adjacent columns, while `.card input, .modal-card input { width: 100%; }` shrinks every input/select into a 1-character slit staggered vertically by uneven label wrapping.

**Why desktop and the earlier review missed it:**
- Desktop (`> 640px`) never triggers `@media (max-width: 640px)`, so `min-width: 220px` keeps wrapping intact.
- The earlier review/design docs (`uiux-gemini-review.md`, `uiux-gemini-design.md`) mistakenly prescribed `.row > * { min-width: 0; }` thinking it both prevented horizontal overflow and collapsed `.row` to 1 column — without changing `flex-direction` or `flex-basis`. On 2-field `.row`s like **Identity** (`ID` + `Role` in Screenshot 2), 2 items split 350px into ~169px each and look passable, masking the bug until a 3+ field `.row` renders on a phone.

---

## 2. Exact mobile form fix (Issue 1b)

**Final decision:** Convert `.row` from Flexbox to **CSS Grid** (`repeat(auto-fit, minmax(min(220px, 100%), 1fr))` on desktop, explicit single column `minmax(0, 1fr)` at `<= 640px`), introduce a dedicated `.row-inline` flex utility for the one select-plus-buttons control (`#attachBox`), stack `.launchbar` cleanly on phone, and enforce `44px` minimum touch targets on inputs, selects, and checkbox rows.

### Verbatim CSS changes in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html)

**1. Replace lines 55–56** (`.row` and `.row > *`) with:

```css
  .row { display:grid; grid-template-columns:repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap:12px; align-items:start; }
  .row > * { min-width:0; }
  .row > div > label { margin:0 0 4px; }
  .row-inline { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .row-inline > :first-child { flex:1 1 200px; min-width:0; }
  .row-inline .inline-actions { flex:0 0 auto; display:flex; gap:8px; }
```

**2. Update `.launchbar` (lines 175–176)** so `#runTeam` does not rely on inline `style="width:180px"`:

```css
  .launchbar { display:flex; gap:8px; align-items:flex-end; flex-wrap:wrap; }
  .launchbar .team-field { flex:0 0 180px; min-width:0; }
  .launchbar .grow { flex:1 1 200px; min-width:0; }
```

**3. Inside `@media (max-width: 640px)` (lines 244–264):**
- **Remove** line 257 (`.row > * { min-width:0; }`) and line 248 (`#addNodeType { max-width:84px; }`, removed in Issue 2).
- **Replace/add** these rules inside `@media (max-width: 640px)`:

```css
  @media (max-width: 640px) {
    /* ...existing header/toolbar/zoom rules... */
    #memberModal, #zipModal, #addNodeModal { align-items:flex-end; padding:0; }
    #memberModal .modal-card, #zipModal .modal-card, #addNodeModal .modal-card {
      max-height:92dvh; border-radius:12px 12px 0 0; overflow-y:auto;
      padding-bottom:calc(20px + env(safe-area-inset-bottom, 0px));
    }
    input, select, textarea { font-size:16px; }
    input:not([type="checkbox"]):not([type="radio"]), select { min-height:44px; }
    button, nav button, .file-row, .check { min-height:44px; }
    .pw-wrap button { min-height:34px; }
    .row { grid-template-columns:minmax(0, 1fr); gap:10px; }
    .row .spacer-label { display:none; }
    .launchbar { flex-direction:column; align-items:stretch; gap:10px; }
    .launchbar .field, .launchbar .team-field, .launchbar .grow { flex:0 0 auto; width:100%; min-width:0; }
    .launchbar #btnRun { width:100%; }
    /* ...existing .stacked table rules... */
  }
```

### Targeted HTML updates required by the CSS above

1. **Teams `#createTeamCard` spacer label ([ui.html:349](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L349)):** add `class="spacer-label"` to the desktop alignment placeholder `<label class="spacer-label">&nbsp;</label>` so single-column mobile stacking does not leave a blank vertical gap above the checkbox.
2. **Files `#attachBox` ([ui.html:389](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L389)):** change `<div class="row">` to `<div class="row-inline">` and replace `<div style="flex:0 0 auto">` with `<div class="inline-actions">`:
   ```html
   <div id="attachBox" style="display:none; margin:8px 0;">
     <label>Attach as charter to</label>
     <div class="row-inline">
       <div><select id="attachTarget"></select></div>
       <div class="inline-actions"><button id="btnDoAttach">Attach</button><button id="btnCancelAttach" class="ghost">Cancel</button></div>
     </div>
   </div>
   ```
3. **Runs `.launchbar` ([ui.html:405](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L405)):** move the inline width off `#runTeam` onto the field wrapper:
   ```html
   <div class="field team-field"><label>Team</label><select id="runTeam"></select></div>
   ```

### How to audit the whole file & complete audit table

Audit command:
```bash
grep -nE 'class="[^"]*(row|launchbar|toolbar|files-split)' airlangga/ui.html
```
Then inspect every `display:flex` / `display:grid` container that holds `<input>`, `<select>`, or `<textarea>`. Every form container in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html) is accounted for below:

| # | Location | Form / section | Fields | Mobile failure before | Fix applied |
|---|---|---|---|---|---|
| 1 | [L342](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L342) | Teams → New team (row 1) | 3 (Name, Template, Mode) | Crushed to ~104px cols | `.row` → 1-col grid (`minmax(0, 1fr)`) |
| 2 | [L348](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L348) | Teams → New team (row 2) | 2 (Budget + Seed checkbox) | Tight 2-col + awkward wrap | `.row` → 1-col grid; `.spacer-label` hidden on phone |
| 3 | [L361](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L361) | Models → Custom providers | 6 fields | Crushed to ~46px cols, colliding labels | `.row` → 1-col grid |
| 4 | [L379](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L379) | Files → New file path | 1 field | None (single child) | `.row` → 1-col grid (unchanged visually, 44px height) |
| 5 | [L389](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L389) | Files → `#attachBox` | 1 select + 2 buttons | **Exception:** equal-width grid would bloat buttons on desktop; single-col button stack is wrong | **Convert to `.row-inline` + `.inline-actions`**: desktop keeps buttons snug right of select; phone gives select full width with `[Attach] [Cancel]` grouped side-by-side underneath |
| 6 | [L439](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L439) | Settings → Approvals & budgets | 3 fields | Crushed to ~104px cols; select text clipped | `.row` → 1-col grid |
| 7 | [L450](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L450) | Settings → Scheduled jobs (`+ Add job`) | 4 fields | Crushed to ~75px cols, colliding labels | `.row` → 1-col grid |
| 8 | [L1165](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1165) | Teams → Inline `editTeamForm()` | 5 fields | Crushed to ~57px cols, colliding labels | `.row` → 1-col grid |
| 9 | [L1201](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1201) | Member modal → Identity | 2 fields (ID, Role) | Narrow 2-col on phone | `.row` → 1-col grid (consistent rhythm) |
| 10 | [L1205](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1205) | Member modal → Model & cost *(Screenshot 2)* | 8 fields | Crushed to ~33px slits, colliding labels | `.row` → 1-col grid + modal safe-area scroll |
| 11 | [L1339](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1339) | Models → Main Brain *(Screenshot 1)* | 9 fields | Crushed to ~27px slits, colliding labels | `.row` → 1-col grid |
| 12 | [L404](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L404) | Runs → `.launchbar` (non-`.row`) | 3 fields + Run button | Inline `width:180px` leaves half-row gap; long `#runMock` option can overflow 390px | Remove inline width; stack `.launchbar` vertically with 100% width controls at `<= 640px` |
| 13 | [L415](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L415), [L475](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L475), [L488](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L488), [L992](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L992) | Settings (Telegram/Password/Skills), `#zipModal`, `#loginScreen`, Graph `#nodeForm` | Sequential stacked fields | Inputs ~40px tall (< 44px target) | Automatically upgraded by `min-height: 44px` on `input:not([type="checkbox"]):not([type="radio"]), select` |

---

## 3. Plain-words explanation of the Add-node list (Issue 2a)

The Graph tab is a visual wiring map of your Airlangga setup: every box is a real piece of your configuration, and the arrows between them decide who uses what when you press **Save graph**. That list was showing every raw type of box you can drop onto the canvas:

- **team** — A group of AI agents working together on one shared goal and one budget (for example, `research-01`).
- **member** — One individual AI agent inside a team with a specific job (such as `researcher`, `fact_checker`, or `writer`).
- **model** — The AI engine (like Claude, GPT, DeepSeek, or local Ollama) that thinks for an agent or Main Brain. One model box can be connected to several agents so you can swap their model in one place.
- **file** — A document from your **Files** tab (like `superagent.md`) that you attach to an agent—either as its **charter** (its persona and rules, loaded on every run) or as reference notes.
- **folder** — A whole folder of documents from your **Files** tab attached to an agent as reference material.
- **tool** — A built-in ability an agent is allowed to use during a run (search the web, read/write files, run terminal commands, or use the browser).
- **skill** — A reusable step-by-step instruction playbook (a `.yaml` file from **Settings → Skills**) that teaches an agent how to follow a specific procedure.

**Why it felt confusing:** you're right—it shouldn't be a 7-item list. Four of those (`file`, `folder`, `tool`, `skill`) do **nothing** floating alone on the canvas; they only take effect when attached to a specific member. And `file` vs `folder` is a technical split—to you, both are just *"attach something from Files."*

---

## 4. ONE final simplified Add-node design (Issue 2b)

### Design decision

1. **Eliminate `<select id="addNodeType">` completely.** Replace the awkward two-step `[+ Add node] [file ▾]` pair with ONE **`+ Add`** button (`#btnAddNode`). On a 390px phone, the entire Graph toolbar (`[Select | Connect] [+ Add] [Save graph]`) now fits cleanly on a single row with zero wrapping.
2. **Replace the Android OS radio dialog with a custom Candi Obsidian sheet (`#addNodeModal`)** — slide-up bottom sheet on phone (`<= 640px`), compact centered dialog on desktop. Every choice is a single-tap button (`min-height: 56px`) with a 3px color stripe matching the canvas node palette, a bold title, and a one-line plain-English purpose (`#F4EFE6` / `#B3AA9B` on `#1F1C17`, contrast `>= 7.4:1`). Tapping a choice immediately creates and wires the node—no separate "confirm add" button.
3. **Split top-level building blocks from member attachments (contextual picker + Inspector action):**
   - Because selecting a node on a phone immediately opens the Inspector bottom sheet (`#sidePanel`, covering the toolbar behind `#sheetScrim`), contextual attachment actions MUST live **inside the Inspector** (and on desktop, clicking toolbar **`+ Add`** while a node is selected opens the exact same contextual sheet for that node).
   - **Merge `file` + `folder` into one choice: `File or folder`.** The user picks an existing file or `folder/` from `S.files` (or enters a custom path), and the UI automatically creates `type: "file"` or `type: "folder"` and wires `has_charter` or `has_file`.
   - **Keep `Model` at top level AND inside Member/Main Brain**, because shared model nodes (`×2`, `×3` badges powering multiple agents) are a core graph concept.
   - **Move `File or folder`, `Tool`, and `Skill` out of the top-level canvas picker** into the **Member** context (`+ Attach to member…` inside the Member Inspector, or toolbar `+ Add` while a Member is selected on desktop), where creating one **auto-wires** the edge immediately and reuses existing shared `tool:*` / `skill:*` / `file:*` nodes.

### Exact picker contents (labels + one-line purposes)

#### A. Canvas level — toolbar `+ Add` (nothing selected, or a file/folder/tool/skill/model selected)
Header: **Add to graph** · Subtitle: *Place a building block on the canvas.*

| Label | Accent stripe | One-line purpose | Action on tap |
|---|---|---|---|
| **Team** | `#D96B43` | *A group of agents sharing one goal and budget.* | Creates `team` node, auto-wires `Main Brain → Team` (`assigns`) if `main_brain` exists, opens Team Inspector. |
| **Member** | `#56B4C8` | *One AI agent with a specific role inside a team.* | Creates `member` node, auto-wires `Team → Member` (`has_member`) if exactly 1 team exists, opens Member Inspector. |
| **Model** | `#4CC38A` | *An AI provider & model that can power one or more agents.* | Creates shared `model` node, opens Model Inspector to pick provider & model. |

Footer hint (12px muted): *To attach a file, folder, tool, or skill, tap any **Member** on the graph.*

#### B. Team context — Team Inspector **`+ Add member to this team`** (or desktop toolbar `+ Add` with Team selected)
Header: **Add to team `<team name>`**
- **Member** (`#56B4C8`) — *Add a new AI agent directly to this team.* (Creates `member` node next to the team, auto-wires `Team → Member` (`has_member`), opens Member Inspector.)
- *(When opened from desktop toolbar `+ Add`, shows a divider "Or add to canvas" with **Team** and **Model** below.)*

#### C. Main Brain context — Main Brain Inspector **`+ Add to Main Brain…`** (or desktop toolbar `+ Add` with Main Brain selected)
Header: **Add to Main Brain**
- **Team** (`#D96B43`) — *Create a new team assigned to Main Brain.* (Auto-wires `Main Brain → Team` (`assigns`).)
- **Model** (`#4CC38A`) — *Create a new AI model to power Main Brain.* (Replaces existing `powers` edge with `New Model → Main Brain`.)

#### D. Member context — Member Inspector **`+ Attach to member…`** (or desktop toolbar `+ Add` with Member selected)
Header: **Attach to `<member name>`** · Subtitle: *Creates and connects directly to this agent.*

| Label | Accent stripe | One-line purpose | Action on tap |
|---|---|---|---|
| **Model** | `#4CC38A` | *Create a new AI model to power this agent.* | Creates `model` node to the right of the member, replaces `uses_model` edge with `Member → New Model`, opens Model Inspector. *(Existing shared models remain 1 tap in the Inspector's `Model (shared node)` dropdown.)* |
| **File or folder** | `#C89B54` | *Attach a charter (e.g. superagent.md), note, or folder from Files.* | Opens step 2 inside the same sheet: lists all files & `folder/` entries from `S.files` (plus custom path input fallback). For a file, offers **Charter (persona rules)** (`has_charter`) vs **Reference attachment** (`has_file`); for a folder, attaches as `type: "folder"` (`has_file`). |
| **Tool** | `#9E9587` | *Allow this agent to use a built-in tool (web, files, terminal, browser).* | Opens step 2 inside the same sheet: lists the 6 built-in `S.toolsets` with one-line descriptions and `Attached` state; tapping toggles/reuses `tool:<name>` and wires/unwires `uses_tool`. |
| **Skill** | `#B3AA9B` | *Attach a step-by-step playbook (.yaml) from Settings → Skills.* | Opens step 2 inside the same sheet: lists skills cached from `/api/skills` (plus custom skill name input & shortcut to Settings → Skills); reuses/creates `skill:<name>` and wires `uses_skill`. |

### Where every node type is reachable

| Node type | Graph creation path | Other tab creation path |
|---|---|---|
| `team` | Toolbar **`+ Add` → Team**; Main Brain Inspector **`+ Add to Main Brain…` → Team**; empty-graph card **`+ Add Team node`** | **Teams** tab → `+ New team` |
| `member` | Team Inspector **`+ Add member to this team`**; Toolbar **`+ Add` → Member** | **Teams** tab → `+ Add member` |
| `model` | Member Inspector **`+ Attach to member…` → Model**; Main Brain Inspector **`+ Add to Main Brain…` → Model**; Toolbar **`+ Add` → Model** (shared) | **Teams** / **Models** tab → Edit member / Main Brain |
| `file` | Member Inspector **`+ Attach to member…` → File or folder** (Charter or Reference); Member Inspector **`Charter file`** dropdown | **Files** tab → `Add to graph` / `Attach as charter…`; Member modal |
| `folder` | Member Inspector **`+ Attach to member…` → File or folder** (pick any `folder/` entry or path ending in `/`) | **Files** tab → `+ Folder` (then attach to member) |
| `tool` | Member Inspector **`Toolsets`** checkboxes (synced to `uses_tool` edges) OR **`+ Attach to member…` → Tool** | **Teams** / **Models** tab → Member modal `Toolsets` |
| `skill` | Member Inspector **`+ Attach to member…` → Skill** | **Settings → Skills** (author YAML) + Member modal `Skills` |

### Exact HTML / CSS / JS changes in [ui.html](file:///home/hatch/workspace/airlangga/airlangga/ui.html)

**1. CSS (add near `#memberModal, #zipModal`, [ui.html:194-205](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L194-L205)):**

```css
  #memberModal, #zipModal, #addNodeModal { position:fixed; inset:0; background:rgba(0,0,0,.62); z-index:45; display:none; align-items:flex-start; justify-content:center; padding:40px 16px; overflow:auto; }
  #memberModal.open, #zipModal.open, #addNodeModal.open { display:flex; }
  #addNodeModal { z-index:46; }
  #addNodeModal .modal-card { max-width:440px; }
  .add-list { display:flex; flex-direction:column; gap:8px; margin-top:10px; }
  .add-opt { display:flex; flex-direction:column; align-items:flex-start; gap:2px; width:100%; min-height:56px; padding:10px 12px;
    background:var(--surface-2); border:1px solid var(--border-ctrl); border-left:3px solid var(--border-hover); border-radius:4px; text-align:left; }
  .add-opt:hover { background:var(--surface-3); border-color:var(--border-hover); }
  .add-opt .add-title { font-size:14px; font-weight:700; color:var(--text); display:flex; align-items:center; gap:8px; width:100%; }
  .add-opt .add-desc { font-size:12px; font-weight:400; color:var(--muted); line-height:1.35; }
  .add-opt.t-team { border-left-color:#D96B43; }
  .add-opt.t-member { border-left-color:#56B4C8; }
  .add-opt.t-model { border-left-color:#4CC38A; }
  .add-opt.t-file { border-left-color:#C89B54; }
  .add-opt.t-tool { border-left-color:#9E9587; }
  .add-opt.t-skill { border-left-color:#B3AA9B; }
  .add-divider { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--subtle); margin:12px 0 4px; }
```

**2. HTML toolbar ([ui.html:301-307](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L301-L307)):** remove `<select id="addNodeType">…</select>` and shorten the button label:

```html
      <button id="btnAddNode" class="ghost">+ Add</button>
```

**3. HTML custom sheet modal (add right after `#zipModal`, [ui.html:486](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L486)):**

```html
<div id="addNodeModal" role="dialog" aria-modal="true" aria-labelledby="addNodeTitle">
  <div class="modal-card">
    <div class="modal-head">
      <h2 id="addNodeTitle">Add to graph</h2>
      <button class="ghost" id="btnCloseAddNode" aria-label="Close">×</button>
    </div>
    <p id="addNodeSub" class="muted small" style="margin:0 0 8px"></p>
    <div id="addNodeBody"></div>
  </div>
</div>
```

**4. JS changes:**

- **Fix `EDGE_KIND_RULES` ([ui.html:534](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L534)):** add `["member", "folder", "has_file"]` right after `["member", "file", "has_file"]` so connecting a member to a folder works in Connect mode too.
- **Cache skills list ([ui.html:509](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L509) & [L1835](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1835)):** declare `let cachedSkills = [];` at top level and save `cachedSkills = d.skills || [];` inside `renderSkillsList()`.
- **Add `syncToolEdges()` next to `syncCharterEdge()` ([ui.html:991](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L991)):** (fixes the existing bug where checking `.nfTool` in the Member Inspector did not update `uses_tool` edges and got wiped on Save graph):

```js
function syncToolEdges(memberNode, toolsets) {
  const want = new Set(toolsets);
  memberNode.data.toolsets = [...want];
  graph().edges = graph().edges.filter(e => !(e.from === memberNode.id && e.kind === "uses_tool"));
  let offset = 0;
  for (const t of want) {
    let tn = graph().nodes.find(x => x.type === "tool" && (x.data.toolset === t || x.label === t));
    if (!tn) {
      tn = { id: "tool:" + t, type: "tool", label: t, x: memberNode.x + 260, y: memberNode.y + offset * 76, data: { toolset: t } };
      graph().nodes.push(tn);
      offset++;
    }
    graph().edges.push({ id: "e-" + Date.now().toString(36) + "-" + offset, from: memberNode.id, to: tn.id, kind: "uses_tool" });
  }
  setDirty(true); renderGraph();
}
```

- **Replace the old `#btnAddNode` click handler ([ui.html:887-899](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L887-L899)) with the unified `createGraphNode()` + `openAddSheet()` flow:**

```js
const TOOL_DESC = {
  web: "Search the web and read pages.",
  file_read: "Read files from the workspace.",
  file_write: "Create and edit workspace files.",
  terminal: "Run shell commands (subject to approval).",
  skills_research: "Search and load reusable research skills.",
  browser: "Fetch and inspect web pages safely.",
};

function closeAddSheet() { document.getElementById("addNodeModal").classList.remove("open"); }
document.getElementById("btnCloseAddNode").addEventListener("click", closeAddSheet);
document.getElementById("addNodeModal").addEventListener("click", ev => { if (ev.target.id === "addNodeModal") closeAddSheet(); });

function createGraphNode(type, anchorNode) {
  const sc = document.getElementById("canvasScroll");
  const x = anchorNode ? anchorNode.x + (NODE_W[anchorNode.type] || 204) + 72
    : Math.max(0, Math.round((sc.scrollLeft + sc.clientWidth / 2) / zoom - (NODE_W[type] || 180) / 2));
  const y = anchorNode ? anchorNode.y + 16
    : Math.max(0, Math.round((sc.scrollTop + sc.clientHeight / 2) / zoom - 32));
  const id = type + ":" + Date.now().toString(36);
  const data = type === "team" ? { template: "blank", team_budget: { usd: 5 }, team_brain_mode: "lead_member" }
    : type === "member" ? { role: "", approval: "smart", toolsets: [], skills: [], attached_files: [] }
    : type === "model" ? { provider: "mock", model: "mock", auth_ref: "none", wire_format: "mock" }
    : (type === "file" || type === "folder") ? { path: "" }
    : type === "tool" ? { toolset: "" } : type === "skill" ? { path: "" } : {};
  const node = { id, type, label: "New " + human(type), x, y, data };
  graph().nodes.push(node);

  // Auto-wire canonical edges when context makes the relationship unambiguous.
  if (type === "team" && nodeById("main_brain")) {
    graph().edges.push({ id: "e-" + Date.now().toString(36), from: "main_brain", to: id, kind: "assigns" });
  } else if (type === "member") {
    const targetTeam = (anchorNode && anchorNode.type === "team") ? anchorNode
      : (graph().nodes.filter(n => n.type === "team").length === 1 ? graph().nodes.find(n => n.type === "team") : null);
    if (targetTeam) graph().edges.push({ id: "e-" + Date.now().toString(36), from: targetTeam.id, to: id, kind: "has_member" });
  } else if (type === "model" && anchorNode && anchorNode.type === "member") {
    graph().edges = graph().edges.filter(e => !(e.from === anchorNode.id && e.kind === "uses_model"));
    graph().edges.push({ id: "e-" + Date.now().toString(36), from: anchorNode.id, to: id, kind: "uses_model" });
  } else if (type === "model" && anchorNode && anchorNode.type === "main_brain") {
    graph().edges = graph().edges.filter(e => !(e.to === "main_brain" && e.kind === "powers"));
    graph().edges.push({ id: "e-" + Date.now().toString(36), from: id, to: "main_brain", kind: "powers" });
  }

  selected = id; setDirty(true); renderGraph(); renderNodeForm();
  if (window.innerWidth <= 820) openSheet();
  return node;
}

function attachFileToMember(memberNode, path, kind, isFolder) {
  const type = isFolder ? "folder" : "file";
  let fn = graph().nodes.find(x => (x.type === "file" || x.type === "folder") && (x.data.path === path || x.label === path));
  if (!fn) {
    fn = { id: type + ":" + path, type, label: path, x: memberNode.x + 260, y: memberNode.y, data: { path } };
    graph().nodes.push(fn);
  }
  if (kind === "has_charter") {
    memberNode.data.charter_file = path;
    graph().edges = graph().edges.filter(e => !(e.from === memberNode.id && e.kind === "has_charter"));
  }
  if (!graph().edges.some(e => e.from === memberNode.id && e.to === fn.id && e.kind === kind)) {
    graph().edges.push({ id: "e-" + Date.now().toString(36), from: memberNode.id, to: fn.id, kind });
  }
  setDirty(true); renderGraph(); renderNodeForm();
}

function attachSkillToMember(memberNode, skillName) {
  const clean = skillName.trim().replace(/\.yaml$/i, "");
  if (!clean) return;
  const fname = clean + ".yaml";
  let sn = graph().nodes.find(x => x.type === "skill" && (x.data.path === fname || x.label === fname || x.id === "skill:" + clean));
  if (!sn) {
    sn = { id: "skill:" + clean, type: "skill", label: fname, x: memberNode.x + 260, y: memberNode.y + 80, data: { path: fname } };
    graph().nodes.push(sn);
  }
  if (!graph().edges.some(e => e.from === memberNode.id && e.to === sn.id && e.kind === "uses_skill")) {
    graph().edges.push({ id: "e-" + Date.now().toString(36), from: memberNode.id, to: sn.id, kind: "uses_skill" });
  }
  setDirty(true); renderGraph(); renderNodeForm();
}

function addOptBtn(cls, title, desc, action, badge) {
  return `<button type="button" class="add-opt ${cls}" data-add-act="${esc(action)}">
    <span class="add-title">${esc(title)}${badge ? `<span class="pill" style="margin-left:auto">${esc(badge)}</span>` : ""}</span>
    <span class="add-desc">${esc(desc)}</span>
  </button>`;
}

function openAddSheet(contextNode) {
  const titleEl = document.getElementById("addNodeTitle");
  const subEl = document.getElementById("addNodeSub");
  const body = document.getElementById("addNodeBody");
  const ctx = contextNode || (selected && !selected.startsWith("e-") ? nodeById(selected) : null);

  if (ctx && ctx.type === "member") {
    titleEl.textContent = "Attach to " + ctx.label;
    subEl.textContent = "Creates and connects directly to this agent.";
    body.innerHTML = `<div class="add-list">
      ${addOptBtn("t-model", "Model", "Create a new AI model to power this agent.", "m-model")}
      ${addOptBtn("t-file", "File or folder", "Attach a charter (e.g. superagent.md), note, or folder from Files.", "m-file")}
      ${addOptBtn("t-tool", "Tool", "Allow this agent to use a built-in tool (web, files, terminal, browser).", "m-tool")}
      ${addOptBtn("t-skill", "Skill", "Attach a step-by-step playbook (.yaml) from Settings \u2192 Skills.", "m-skill")}
    </div>`;
    body.querySelectorAll("[data-add-act]").forEach(btn => btn.addEventListener("click", () => {
      const act = btn.dataset.addAct;
      if (act === "m-model") { closeAddSheet(); createGraphNode("model", ctx); }
      else if (act === "m-file") renderMemberFilePicker(ctx);
      else if (act === "m-tool") renderMemberToolPicker(ctx);
      else if (act === "m-skill") renderMemberSkillPicker(ctx);
    }));
  } else if (ctx && ctx.type === "team") {
    titleEl.textContent = "Add to team " + ctx.label;
    subEl.textContent = "Add a member to this team, or place another building block on the canvas.";
    body.innerHTML = `<div class="add-list">
      ${addOptBtn("t-member", "Member", "Add a new AI agent directly to this team.", "t-member")}
    </div>
    <div class="add-divider">Or add to canvas</div>
    <div class="add-list">
      ${addOptBtn("t-team", "Team", "A group of agents sharing one goal and budget.", "c-team")}
      ${addOptBtn("t-model", "Model", "An AI provider & model that can power one or more agents.", "c-model")}
    </div>`;
    body.querySelectorAll("[data-add-act]").forEach(btn => btn.addEventListener("click", () => {
      const act = btn.dataset.addAct; closeAddSheet();
      if (act === "t-member") createGraphNode("member", ctx);
      else if (act === "c-team") createGraphNode("team");
      else if (act === "c-model") createGraphNode("model");
    }));
  } else if (ctx && ctx.type === "main_brain") {
    titleEl.textContent = "Add to Main Brain";
    subEl.textContent = "Assign a new team or swap the model powering Main Brain.";
    body.innerHTML = `<div class="add-list">
      ${addOptBtn("t-team", "Team", "Create a new team assigned to Main Brain.", "mb-team")}
      ${addOptBtn("t-model", "Model", "Create a new AI model to power Main Brain.", "mb-model")}
    </div>`;
    body.querySelectorAll("[data-add-act]").forEach(btn => btn.addEventListener("click", () => {
      const act = btn.dataset.addAct; closeAddSheet();
      createGraphNode(act === "mb-team" ? "team" : "model", ctx);
    }));
  } else {
    titleEl.textContent = "Add to graph";
    subEl.textContent = "Place a building block on the canvas.";
    body.innerHTML = `<div class="add-list">
      ${addOptBtn("t-team", "Team", "A group of agents sharing one goal and budget.", "c-team")}
      ${addOptBtn("t-member", "Member", "One AI agent with a specific role inside a team.", "c-member")}
      ${addOptBtn("t-model", "Model", "An AI provider & model that can power one or more agents.", "c-model")}
    </div>
    <p class="muted small" style="margin:12px 0 0">To attach a file, folder, tool, or skill, tap any <b>Member</b> on the graph.</p>`;
    body.querySelectorAll("[data-add-act]").forEach(btn => btn.addEventListener("click", () => {
      const act = btn.dataset.addAct; closeAddSheet();
      createGraphNode(act.replace("c-", ""));
    }));
  }
  document.getElementById("addNodeModal").classList.add("open");
}

function renderMemberFilePicker(memberNode) {
  document.getElementById("addNodeTitle").textContent = "Attach file or folder";
  document.getElementById("addNodeSub").textContent = "Pick an item from files/ to wire to " + memberNode.label + ".";
  const body = document.getElementById("addNodeBody");
  const items = S.files || [];
  body.innerHTML = `
    <label>How should this agent use a file?</label>
    <select id="afRole"><option value="has_charter">Charter — persona &amp; rules loaded every run</option><option value="has_file">Reference — attached file or folder</option></select>
    <div class="add-list" style="margin-top:10px">
      ${items.map(f => addOptBtn("t-file", f.type === "folder" ? f.path + "/" : f.path,
        f.type === "folder" ? "Folder attached as reference material." : "Workspace file under files/.",
        (f.type === "folder" ? "D:" : "F:") + f.path, f.type === "folder" ? "folder" : "")).join("")
        || `<p class="muted small">No files yet — create or import them in the Files tab.</p>`}
    </div>
    <label style="margin-top:12px">Or enter a path under files/</label>
    <div class="row-inline">
      <div><input id="afCustomPath" placeholder="personas/scout.md or docs/"></div>
      <div class="inline-actions"><button type="button" id="btnAfCustom" class="gold">Attach</button></div>
    </div>
    <div class="actions"><button type="button" class="ghost" id="btnAfBack">\u2190 Back</button><button type="button" class="ghost" id="btnAfGoFiles">Open Files tab</button></div>`;
  body.querySelectorAll("[data-add-act]").forEach(btn => btn.addEventListener("click", () => {
    const raw = btn.dataset.addAct;
    const isFolder = raw.startsWith("D:");
    const path = raw.slice(2);
    const kind = isFolder ? "has_file" : document.getElementById("afRole").value;
    attachFileToMember(memberNode, path, kind, isFolder);
    closeAddSheet();
  }));
  document.getElementById("btnAfCustom").addEventListener("click", () => {
    const raw = document.getElementById("afCustomPath").value.trim(); if (!raw) return;
    const isFolder = raw.endsWith("/");
    const path = raw.replace(/\/+$/, "");
    const kind = isFolder ? "has_file" : document.getElementById("afRole").value;
    attachFileToMember(memberNode, path, kind, isFolder);
    closeAddSheet();
  });
  document.getElementById("btnAfBack").onclick = () => openAddSheet(memberNode);
  document.getElementById("btnAfGoFiles").onclick = () => { closeAddSheet(); closePanel(); switchTab("files"); };
}

function renderMemberToolPicker(memberNode) {
  document.getElementById("addNodeTitle").textContent = "Attach tool to " + memberNode.label;
  document.getElementById("addNodeSub").textContent = "Tap a tool to connect or disconnect it.";
  const body = document.getElementById("addNodeBody");
  const active = new Set(graph().edges
    .filter(e => e.from === memberNode.id && e.kind === "uses_tool")
    .map(e => { const t = nodeById(e.to); return t ? (t.data.toolset || t.label) : ""; })
    .filter(Boolean));
  body.innerHTML = `<div class="add-list">
    ${S.toolsets.map(t => addOptBtn("t-tool", t, TOOL_DESC[t] || "Built-in toolset.", t, active.has(t) ? "Attached" : "")).join("")}
  </div><div class="actions"><button type="button" class="ghost" id="btnAtBack">\u2190 Back</button><button type="button" class="gold" id="btnAtDone">Done</button></div>`;
  body.querySelectorAll("[data-add-act]").forEach(btn => btn.addEventListener("click", () => {
    const t = btn.dataset.addAct;
    if (active.has(t)) active.delete(t); else active.add(t);
    syncToolEdges(memberNode, [...active]);
    renderNodeForm();
    renderMemberToolPicker(memberNode);
  }));
  document.getElementById("btnAtBack").onclick = () => openAddSheet(memberNode);
  document.getElementById("btnAtDone").onclick = closeAddSheet;
}

function renderMemberSkillPicker(memberNode) {
  document.getElementById("addNodeTitle").textContent = "Attach skill to " + memberNode.label;
  document.getElementById("addNodeSub").textContent = "Choose a skill playbook from Settings \u2192 Skills.";
  const body = document.getElementById("addNodeBody");
  body.innerHTML = `<div class="add-list">
    ${cachedSkills.map(sk => addOptBtn("t-skill", sk.name.replace(/\.yaml$/i, ""), sk.path, sk.name)).join("")
      || `<p class="muted small">No skills created yet \u2014 author one in Settings \u2192 Skills.</p>`}
  </div>
  <label style="margin-top:12px">Or enter a skill name</label>
  <div class="row-inline">
    <div><input id="asCustomName" placeholder="research"></div>
    <div class="inline-actions"><button type="button" id="btnAsCustom" class="gold">Attach</button></div>
  </div>
  <div class="actions"><button type="button" class="ghost" id="btnAsBack">\u2190 Back</button><button type="button" class="ghost" id="btnAsGoSettings">Open Settings \u2192 Skills</button></div>`;
  body.querySelectorAll("[data-add-act]").forEach(btn => btn.addEventListener("click", () => {
    attachSkillToMember(memberNode, btn.dataset.addAct);
    closeAddSheet();
  }));
  document.getElementById("btnAsCustom").addEventListener("click", () => {
    const v = document.getElementById("asCustomName").value.trim(); if (!v) return;
    attachSkillToMember(memberNode, v);
    closeAddSheet();
  });
  document.getElementById("btnAsBack").onclick = () => openAddSheet(memberNode);
  document.getElementById("btnAsGoSettings").onclick = () => { closeAddSheet(); closePanel(); switchTab("settings"); };
}

document.getElementById("btnAddNode").addEventListener("click", () => openAddSheet());
```

- **Add contextual button inside `renderNodeForm()` ([ui.html:1018-1055](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1018-L1055)):**
  - Inside `if (n.type === "member")`: add `<div class="actions"><button type="button" id="btnMemberAttach" class="gold">+ Attach to member\u2026</button></div>` and bind `document.getElementById("btnMemberAttach").onclick = () => openAddSheet(n);`. Also bind `.nfTool` checkbox `change` events to `syncToolEdges(n, [...document.querySelectorAll(".nfTool:checked")].map(x => x.value))` so checking/unchecking toolboxes in the Inspector persists on Save graph.
  - Inside `if (n.type === "team")`: add `<div class="actions"><button type="button" id="btnTeamAddMember" class="gold">+ Add member to this team</button></div>` and bind `document.getElementById("btnTeamAddMember").onclick = () => createGraphNode("member", n);`.
  - Inside `if (n.type === "main_brain")`: add `<div class="actions"><button type="button" id="btnMbAdd" class="ghost">+ Add team or model\u2026</button></div>` and bind `document.getElementById("btnMbAdd").onclick = () => openAddSheet(n);`.
- **Update `#btnEmptyAddTeam` ([ui.html:821-824](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L821-L824)):** replace the removed `#addNodeType` reference with `createGraphNode("team");`.
- **Fix misplaced listener block ([ui.html:808-852](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L808-L852)):** those top-level event listeners (`#btnClosePanel`, `#sheetScrim`, `#btnEmptyAddTeam`, `#sheetGrabber`, `Escape` key handler, `beforeunload`) are currently accidentally nested inside `if (!connectSource) { ... }` inside `onNodeClick()`. Move them out to top-level scope right after `onNodeClick()` closes, and update the `Escape` handler to close `#memberModal, #zipModal, #addNodeModal` (instead of `.modal.open`, which matches nothing).

---

## 5. Implementation checklist (in order)

1. **CSS — Form grid & mobile targets ([ui.html:55-56](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L55-L56), [L175-176](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L175-L176), [L244-264](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L244-L264)):**
   - Replace `.row` / `.row > *` with CSS Grid (`repeat(auto-fit, minmax(min(220px, 100%), 1fr))`) and add `.row > div > label`, `.row-inline`, and `.inline-actions`.
   - Add `.launchbar .team-field`.
   - In `@media (max-width: 640px)`: delete `.row > * { min-width: 0; }` and `#addNodeType { max-width: 84px; }`; add `.row { grid-template-columns: minmax(0, 1fr); gap: 10px; }`, `.row .spacer-label { display: none; }`, `.launchbar` vertical stack rules, `min-height: 44px` on non-checkbox inputs/selects and `.check`, and safe-area bottom padding on `.modal-card`.
2. **HTML — Form exception patches ([ui.html:349](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L349), [L389](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L389), [L405](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L405)):**
   - Add `class="spacer-label"` to the `&nbsp;` label in `#createTeamCard`.
   - Convert `#attachBox` from `.row` + inline `flex:0 0 auto` to `.row-inline` + `.inline-actions`.
   - Replace `style="width:180px"` on `#runTeam` with `class="field team-field"` on its wrapper.
3. **HTML & CSS — Custom Add-node sheet ([ui.html:194-205](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L194-L205), [L301-307](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L301-L307), [L486](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L486)):**
   - Add `#addNodeModal` + `.add-list` / `.add-opt` CSS.
   - Delete `<select id="addNodeType">` and rename `#btnAddNode` text to `+ Add`.
   - Insert `#addNodeModal` markup after `#zipModal`.
4. **JS — Graph node creation, contextual sheet, and sync helpers ([ui.html:509](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L509), [L534](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L534), [L801-900](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L801-L900), [L991-1119](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L991-L1119), [L1835](file:///home/hatch/workspace/airlangga/airlangga/ui.html#L1835)):**
   - Move lines 808–852 out of `onNodeClick()` to top-level scope; fix Escape handler to close `#memberModal, #zipModal, #addNodeModal`; update `#btnEmptyAddTeam` to call `createGraphNode("team")`.
   - Add `["member", "folder", "has_file"]` to `EDGE_KIND_RULES` and cache `cachedSkills` in `renderSkillsList()`.
   - Add `syncToolEdges()`, `createGraphNode()`, `attachFileToMember()`, `attachSkillToMember()`, `openAddSheet()`, `renderMemberFilePicker()`, `renderMemberToolPicker()`, `renderMemberSkillPicker()`, and bind `#btnAddNode` to `openAddSheet()`.
   - Wire contextual add buttons (`+ Attach to member…`, `+ Add member to this team`, `+ Add team or model…`) and `.nfTool` → `syncToolEdges()` inside `renderNodeForm()`.
5. **Verification (390×844 mobile viewport + 1280×800 desktop + pytest):**
   - Run `pytest tests/test_web_ui.py` to confirm zero backend/HTML regressions.
   - Visually inspect at **390px wide** (Android Chrome / DevTools): Models → Main Brain, Models → Custom providers, Teams → New team & Edit team, Member modal → Identity & Model & cost, Files → Attach charter box, Runs → Launch a run, Settings → Approvals & Scheduled jobs (zero overlap, 1 column, full-width inputs >= 44px tall).
   - Visually inspect **Graph tab at 390px and 1280px**: toolbar fits on one row at 390px; `+ Add` opens the 3-item studio sheet; tapping a Member → `+ Attach to member…` reaches Model, File or folder (creating `file` and `folder` nodes), Tool, and Skill, auto-wires edges, and persists cleanly via **Save graph** → reload.
