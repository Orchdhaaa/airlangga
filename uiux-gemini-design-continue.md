# Continuation — Airlangga Web UI design spec, sections 7 (rest) + 8

You already wrote most of this design specification. The file `uiux-gemini-design-raw.md` in the added workspace directory contains your output so far (sections 1–6 complete, section 7 "Mobile Design" cut off mid-sentence inside "### Bottom-Sheet Inspector Spec (<= 820px)", right after the "Scrollable Body (#nodeForm)" bullet). Read that file first — do NOT redesign anything already specified, do NOT repeat sections 1–6.

Write ONLY the missing remainder, in the same style (implementation-ready, concrete values, no vague advice):

1. Finish section 7 "Mobile Design": complete the Bottom-Sheet Inspector spec from exactly where it stopped (Scrollable Body onwards: grabber drag behaviour, sheet heights/peeks, backdrop, safe-area, keyboard behaviour), then the remaining mobile subsections you had planned (stacked layout rules per tab, scrollable tab nav, tables, touch targets, graph auto-fit on load, login page on mobile). Keep every value consistent with what sections 1–6 already specify.

2. Then section 8 "Implementation Checklist": prioritised P0 (must ship) / P1 (real UX wins) / P2 (polish). Each item concrete enough to check off — exact strings, hex values and measurements the implementer needs, not references back to earlier sections. The checklist must cover every P0 gap from the original brief: ZIP import end to end (frontend flow + backend endpoint contract), graph-added team/member nodes persisting through save/reload, Settings per-section save persisting every section, port-to-port type-coloured edges, no full-DOM re-render per drag pointermove, mobile bottom-sheet inspector, and the visual-system rollout. Order P0 items in the order they should be built.

Output only sections 7 (remainder) and 8, as Markdown. Do not ask questions.
