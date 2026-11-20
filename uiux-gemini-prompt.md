You are a senior product designer and front-end design reviewer. REVIEW ONLY — do not edit any file. Read the files yourself before judging.

PRODUCT
Airlangga — Agentic Team Studio: a web UI for building and managing teams of AI agents (Main Brain, Team Brains, members, models, files, tools, runs). It is an N8N-style node graph where the connections are between brains, models, files and teams — e.g. Model A powers which brains, which files/folders attach to a member, which members belong to which team — plus Teams, Models, Files, Runs, Settings tabs and a login page.

FILES (in the workspace you have been given)
- airlangga/ui.html — the whole UI: one self-contained page, 630 lines, inline CSS/JS, no build step, no framework. Read it fully. This is what you are auditing.
- airlangga/web_ui.py — the backend (Python stdlib http.server, JSON API). Skim it only for context on what the UI can and cannot do; the audit target is ui.html.

QUALITY BAR (from the product owner, an Indonesian user — do not soften this)
The UI must NOT look like "AI slop" — no generic AI-generated look: no purple-blue gradients, no emoji-as-icons, no cookie-cutter glassmorphism cards, no generic hero, no lorem-style filler, no 3 identical feature cards in a row, no everything-rounded-everything-muted sameness. The durable design bar is premium-playful agency-grade (reference sites: tehtariknation.com, sweet-tape.com, bikebear.com.my): strong typography, real visual hierarchy, high contrast (body text contrast >= 4.5:1), one clear primary action per screen, fast and dense where a pro tool should be dense. Brand direction: Airlangga, an 11th-century Javanese king who reunified East Java — a distinctive Javanese heritage feel is welcome if done tastefully (deep dark + gold #D4AF37 is the house accent), but NO kitsch, NO cheap batik clip-art, NO generic temple clipart.
This is a dense pro tool/dashboard used on a phone browser (~390px) as well as desktop — the node graph, tables, forms and trace view must stay usable and readable, not just pretty.

DELIVER — concrete and implementable, not vague advice. Cite the actual selectors/classes/lines in ui.html wherever you name a problem, and give exact values (hex codes, px, font stacks, weights) wherever you propose a change.

(a) HONEST AUDIT: list the exact AI-slop elements in the current ui.html (cite selectors/classes/lines) and explain what makes each one look generic. Be blunt. Also list what is already good and should be kept.

(b) REVISED VISUAL DIRECTION: color palette (exact hex for background, panels, borders, text, muted text, accent gold, secondary accent, danger, success, graph edge/node colors per node type), typography (font stack — system stack or specific families — sizes and weights for H1/H2/body/labels/mono, line-height, letter-spacing), spacing/radius/shadow rules, node-graph styling (node shapes, edge styles, labels, hover/selection/connect-source states), buttons (primary/gold/ghost/danger), inputs/selects/textareas, tables, pills/badges, login card.

(c) LAYOUT / UX REVISIONS PER TAB: Graph, Teams, Models, Files, Runs, Settings, login page. For each: what to change and in what order. Give the concrete new structure (what goes where, what is the one primary action, what gets removed or merged) for the 3 most important screens. Keep every change implementable in one self-contained HTML file with inline CSS/JS and no build step.

(d) MOBILE (~390px phone browser) FIXES: what breaks at ~390px in the current file (graph canvas is 1600x900, side panel 320px, tables, toolbar, tabs) and the concrete fix for each breakage.

(e) WHAT NOT TO DO: anti-patterns to avoid when implementing this revision (things that would reintroduce the slop).

PRIORITISE everything as P0 (must change to kill the slop), P1 (real UX wins), P2 (nice polish). End with a short ordered P0 checklist an implementer can follow top to bottom.
