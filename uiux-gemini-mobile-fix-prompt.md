# Airlangga Web UI — mobile fix discussion (round 2)

You are the designer of the Airlangga Web UI (Agentic Team Studio, "Candi Obsidian & Lontar Studio"
direction from your earlier work). The user just tested the redesigned UI on his phone and found two
mobile problems. Read the files below first, then answer the two questions at the end. Pick ONE final
design/decision for each issue — do not return options for the user to choose from. If anything is
ambiguous, pick the most useful interpretation and state it.

## Repo and context

- Repo: this directory (~/workspace/airlangga/). The UI is ONE self-contained page,
  `airlangga/ui.html` (inline CSS/JS, no build step, no framework, NO external fonts/CDN — it must
  render correctly with no network, system font stack only). Backend: `airlangga/web_ui.py`
  (stdlib http.server). Login: token stored in sessionStorage only, never in the URL.
- The user is phone-first: he tests on Android Chrome at ~390px wide. Desktop layout must keep
  working, but phone must never break.
- Quality bar: premium-playful agency-grade, anti-AI-slop (no gradients, no glassmorphism, no
  batik clip-art, no emoji icons), body contrast >= 4.5:1, min 44px touch targets on phone.

## Issue 1 — Overlapping form grids on mobile (screenshots 1 and 2)

Screenshot 1 (`~/workspace/user/files/278018_0_xpzf.jpg`): Models tab, "Main Brain" form on a phone.
The form has 9 fields in ONE row — PROVIDER / MODEL / ENDPOINT / AUTH REF / CAPABILITIES /
COST PER M TOKENS / CONTEXT LIMIT / MAX TOKENS PER CALL / BUDGET — and at phone width the labels
collide into each other and the inputs become tiny overlapping boxes. Unusable.
Screenshot 2 (`~/workspace/user/files/278019_1_3euf.jpg`): "Edit member" modal, "MODEL & COST"
section — the same failure: PROVIDER / MODEL / ENDPOINT / AUTH REF / BUDGET / COST PER M TOKENS /
CONTEXT LIMIT / APPROVAL crushed into overlapping columns. The rest of both screens looks fine
(capabilities checkboxes, wiring, charter file, toolsets all render well) — ONLY the dense
multi-column form grids break.

Evidence from `airlangga/ui.html` (read the file to confirm):

```css
.row { display:flex; gap:12px; flex-wrap:wrap; }
.row > * { flex:1; min-width:220px; }
...
@media (max-width: 640px) {
  ...
  .row > * { min-width:0; }
  ...
}
```

The Main Brain form is rendered by JS (`renderModels()`) as a single `<div class="row">` holding
9 `<div><label>…</label><input…></div>` children. The member modal's "Model & cost" section is the
same pattern: one `<div class="row">` with 8 field children. Other screens use `.row` too
(Teams create-team card, Files attach box, Runs, inspector forms).

QUESTION 1a: Diagnose WHY the grids overlap at ~390px. Name the exact CSS rule/pattern that
causes it (and why it looked fine on desktop and in the earlier review, which missed it).
QUESTION 1b: Propose the EXACT mobile fix — concrete CSS (which rules to change/add/remove, which
breakpoint) and any HTML/JS structure change if needed. Requirements: at phone width each field
stacks to a single column, label above its input, full-width, min 44px touch targets, zero
overlap, no horizontal squeeze; desktop multi-column layout keeps working; the fix must cover
EVERY `.row`-based form in the file, not just the two screenshotted ones — say how to audit for
other instances of the same flaw and what to do about each (including any `.row` usage where
single-column stacking would be wrong, e.g. a button next to a select).

## Issue 2 — Add-node type list is confusing (screenshot 3)

Screenshot 3 (`~/workspace/user/files/278022_2_nva7.jpg`): Graph tab on a phone. Tapping the
"+ Add node" control opens a bottom sheet listing 7 bare types with radio buttons:
file, folder, model, team, member, tool, skill. No explanation of what any of them does.
The user asks, in his own words: "that list of file, folder, model, etc — what is it for? Why
isn't it simpler?"

Evidence from `airlangga/ui.html`: the control is a native `<select id="addNodeType">` next to a
"+ Add node" button in the graph toolbar. The 7 `<option>` values are file / folder / model /
team / member / tool / skill. On Android Chrome a `<select>` opens as exactly the bottom sheet
in the screenshot. Each option adds a node of that type to the node graph: team = a team of
agents; member = one agent in a team; model = an LLM provider+model a member uses; file/folder =
a persona/charter file (e.g. superagent.md) or folder attached to a member; tool = a capability
a member can call (web, file_read, terminal…); skill = a skill file a member can use.
Nodes are then connected with edges (member uses model, member has charter file, team has
member, etc.) and saved back to airlangga.yaml.

QUESTION 2a: In plain words a non-technical user would understand, explain what this list is
for — what adding each of those 7 things actually DOES in the product.
QUESTION 2b: Propose a SIMPLER design and pick ONE final design. Ideas to consider (judge them
yourself, keep what works, reject what doesn't): merge file+folder into one "File" entry;
hide tool/skill/model from the top-level picker because they only make sense attached to a
member (add them from the member inspector/modal instead); make the picker contextual — the
choices offered depend on what the user tapped (tap a member → offer model/file/tool/skill for
THAT member; tap empty canvas → offer team/member); give every remaining choice a one-line
purpose under its name; replace the native `<select>` with a custom bottom sheet or with direct
action buttons. The picker must still let the user add EVERY node type the graph genuinely
needs — if a type leaves the picker, say exactly where its creation is reachable instead.
State the final picker contents (exact labels + one-line purposes), where each type is created
from, and the exact HTML/JS change (keep it a single self-contained page, no new dependencies).

## Output format

1. Diagnosis of the overlap (issue 1a) — short, with the exact offending rule.
2. Exact mobile form fix (issue 1b) — CSS rules verbatim + audit list of every affected form.
3. Plain-words explanation of the Add-node list (issue 2a) — as if speaking to the user.
4. ONE final simplified Add-node design (issue 2b) — exact labels, purposes, creation paths,
   HTML/JS change.
5. A short implementation checklist in order, so the implementer can apply this without
   re-reading the whole discussion.
