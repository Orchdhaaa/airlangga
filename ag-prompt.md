You are acting as an independent senior systems architect / design reviewer. Give your own honest input — do not just agree with the brief. Be concrete, specific, and critical where warranted. Output in English, structured with clear headings.

CONTEXT
- Hermes Agent v0.23.2 (Nous Research, MIT, Python+TS, 1.1G) is installed on a VPS. It already has: single-agent turn loop, multi-provider model switching (OpenAI/OpenRouter/Nous Portal/custom endpoint), subagent spawning with per-subagent provider/model, skills + memory + cron + Telegram/Discord gateway, and 8 guardrail layers.
- New project "Airlangga" (named after a Javanese king) is a rebuild/fork of Hermes with a different core concept: Agentic Team — NOT swarm, NOT one-shot subagents, NOT a plain orchestrator/router.
- Required features:
  (1) Agentic Team: persistent teams of specialist agents with roles, shared team memory/context, debate + merge + conflict resolution.
  (2) Main Brain: strategic brain — plans, decomposes, assigns, owns budget/quality gate, final verdict.
  (3) Group/Team Brain: tactical brain per team — coordinates its members, merges partial results, escalates to Main Brain.
  (4) Multi-AI config: every member/team can use a DIFFERENT AI/model/provider by purpose — official API, custom base_url, or fully custom provider (OpenAI-compatible, Anthropic, Gemini, Ollama/local) — with fallback chains and cost/latency/quality routing.

ANSWER THESE FIVE THINGS:
(a) What other features are actually needed for this to be useful (not gimmicks)? Prioritise by real user value; say what to leave OUT.
(b) How must Agentic Team differ in concrete mechanics from swarm / one-shot subagents / plain orchestrator-router? Give a comparison table (dimensions: persistence, memory, authority, communication, conflict handling, failure handling, cost).
(c) Proposed architecture: components, data flow, where Main Brain vs Team Brain live, how context/memory is shared without exploding tokens (context budget, summarisation, retrieval, what each layer sees). Include a simple text diagram.
(d) Biggest risks / failure modes and how to mitigate them (include: infinite debate loops, Main Brain bottleneck, context explosion, conflicting provider outputs, cost runaway, guardrail bypass by a team member, stale shared memory).
(e) Minimal v1 scope vs v2: concrete v1 feature list (buildable in weeks, not months), explicit v1 non-goals, and what v2 adds.

Constraints to respect in your answer: build on Hermes where sensible (do not reinvent its gateway/skills/memory/cron), keep it self-hostable on a single VPS, English-only product surface, no paid service assumed by default.
