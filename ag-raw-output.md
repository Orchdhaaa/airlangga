# Airlangga: Independent Design Review

## 0. Where I disagree with the brief

1. **Don't "rebuild/fork" Hermes. Build Airlangga as a layer on top of it.** A fork of a 1.1 GB, fast-moving codebase means you carry upstream merge debt forever. Keep a small patch set (hooks for the turn loop, tool-call interception and context assembly) and upstream those hooks if you can. Put Airlangga in its own package: team registry, run ledger, brains, blackboard and router. Hermes keeps the gateway, skills, memory primitives, cron and guardrails.
2. **"Persistent agents" should mean persistent state, not persistent processes or chat histories.** An agent is a durable record: charter, role prompt, tool permissions, model policy, private notes and track record. Each activation builds a fresh, budgeted context from that record. Long-lived conversation threads are the main cause of token blowup and drift.
3. **Main Brain and Team Brain are one runtime in two configurations.** They share the same code with different tool sets and authority. Team Brain should also be optional. A team of 1–3 members should use a *lead member* instead of a separate brain call, because an always-on three-tier hierarchy (Main, Team, Member) adds 2 extra LLM hops to every task.
4. **"Different model per member" is a cost and risk surface, not just a feature.** A fallback from a strong model to a weak one silently changes behaviour. Fallbacks must be capability-gated (see §c).

---

## (a) Features actually needed

### Must-have, in priority order

| # | Feature | Why it matters |
|---|---|---|
| 1 | **Durable run ledger** (event-sourced, SQLite WAL). Every plan, assignment, message, tool call, cost and verdict is an append-only event. | Resume after a VPS crash, audit, replay and debugging. Without it, multi-agent systems can't be debugged. |
| 2 | **Hard budget governor.** Per-run, per-team and per-member caps on tokens, dollars, wall-clock time and tool calls, enforced *outside* the LLMs. | Cost runaway is the number one way this kind of system fails. |
| 3 | **Task contracts.** Each assignment has a goal, inputs (artifact refs), output schema, acceptance check, budget and deadline. | This replaces vague chat delegation and makes quality gates checkable. |
| 4 | **Verifiers, not just opinions.** Acceptance checks can be executable (tests, linters, schema validation, a URL fetch, a diff check) as well as an LLM judge. | An LLM judge grading LLM output is weak. A runnable check is strong. |
| 5 | **Policy engine at the tool-call boundary.** Per-role tool allowlists, path and network scopes, and approval-required actions, enforced by the runtime. | This is the only reliable defence against a member bypassing guardrails (§d). |
| 6 | **Provider router with capability tags and fallback chains.** Each model is tagged (tool-calling, JSON mode, context size, vision, cost, p50 latency). Routing is by *purpose*, with static rules first. | This is the "multi-AI" requirement made safe. |
| 7 | **Human-in-the-loop via the Hermes gateway.** Approve a plan, approve spend above a threshold, approve risky tools, answer escalations. Use Telegram/Discord as the approval channel. | Real users need a brake. This reuses the gateway you already have. |
| 8 | **Artifact store.** Files, patches and reports live in a per-run workspace and are passed by reference, not pasted into prompts. | Key to controlling context size. |
| 9 | **Team templates (YAML).** Teams such as "research", "code+review" and "content" are declared, versionable and shareable. | Users won't hand-assemble roles. Templates are the real onboarding path. |
| 10 | **Trace viewer.** A CLI first, then a small web page showing the plan tree, who said what, cost per node and debate outcomes. | You can't trust or tune what you can't see. |
| 11 | **Local-model first-class (Ollama/OpenAI-compatible).** A cheap, free tier is needed to satisfy "no paid service by default". | Use local models for drafting, critique and summarisation. |
| 12 | **Replay and tiny eval harness.** Re-run a recorded task against a different model config and compare cost and pass rate. | This is how users validate that "model X for role Y" is actually better. |

### Leave OUT (at least for v1, some permanently)

- **Auto-evolving agents, self-rewriting prompts, "agents hiring agents" at runtime.** These are unbounded and untestable.
- **Visual drag-and-drop team builder.** YAML plus a CLI is enough.
- **Vote-among-N consensus as the default.** It multiplies cost for marginal quality. Use it only for a few flagged high-stakes decisions.
- **Learned or ML-based routing.** Start with static rules plus logged outcomes. Add learning only once you have data.
- **Agent "personalities" and social chatter between members.** Tokens with no value.
- **Dedicated vector DB service.** SQLite FTS5 plus an optional local embedding index is enough on one VPS.
- **A marketplace for agents or teams**, voice, and multi-tenant SaaS features.
- **A second, new gateway, skills system or cron.** Reuse Hermes's.

---

## (b) Agentic Team vs the alternatives

| Dimension | Swarm | One-shot subagents | Plain orchestrator/router | **Agentic Team (Airlangga)** |
|---|---|---|---|---|
| **Persistence** | None or ephemeral. Agents spawn and die. | None. Dies when the task returns. | Orchestrator has a session. Workers are stateless. | Team and member **identities persist** across runs (charter, notes, track record). Activations are on-demand. |
| **Memory** | Implicit, via message passing or shared scratch. | Parent passes a prompt. Result returns as text. | Orchestrator's context only. | **Typed team memory** (blackboard: facts, decisions, open questions, artifacts) with provenance, versions and TTL. Plus private member notes. |
| **Authority** | Flat or emergent. | Parent is absolute. | Orchestrator is absolute and routes. | **Layered and explicit.** Main Brain owns budget, goal and verdict. Team Brain owns tactical decisions inside its contract. Members own their output. A member can formally *dissent*. |
| **Communication** | Broadcast or peer-to-peer, unstructured. | Prompt in, text out. | Hub-and-spoke. | **Structured reports** (claim, evidence refs, confidence, diff) through the team channel. Members don't talk to Main Brain directly. |
| **Conflict handling** | None, or last-write-wins or voting. | None (a single result). | Orchestrator picks or re-asks. | **Bounded protocol:** propose, critique (preferably by a different model), revise, then decide by verifier result, Team Brain ruling, or escalation. Max 2 rounds. Dissent is recorded. |
| **Failure handling** | Redundancy hides failures. | Parent retries or gives up. | Orchestrator retries. | **Typed failures** (tool error, budget, quality gate, provider outage). Each has a policy: retry, swap member, swap model via fallback, escalate or abort. State is checkpointed in the ledger. |
| **Cost** | High and unpredictable (N parallel agents). | Low and predictable. | Low to medium. | **Medium to high by design, but capped.** Budgets are allocated top-down and enforced by the runtime. Cheap models handle the bulk and strong models handle gating. |

**The concrete mechanics that make it a different thing:**
- **Contracts, not conversations.** Work crosses layers as a signed task contract plus a structured report.
- **A shared blackboard with write rules.** Members propose entries and the Team Brain commits them, which stops memory pollution.
- **An explicit dissent and merge step.** This is the part orchestrators don't have.
- **Budget is a delegated resource.** Main Brain gives each team a budget, and the team sub-allocates it.
- **Identity survives the run.** A "reviewer" that was repeatedly wrong on a task type is visible in its stats, and the router can act on that.

---

## (c) Proposed architecture

### Components

```
                         ┌───────────────────────────────┐
  Telegram / Discord /   │   Hermes Gateway (reused)     │
  CLI / cron (Hermes) ──►│   auth, sessions, approvals   │
                         └──────────────┬────────────────┘
                                        │ goal / approvals / status
┌───────────────────────────────────────▼─────────────────────────────────────┐
│                           AIRLANGGA CORE (new package)                      │
│                                                                             │
│  ┌────────────┐   plan/assign/verdict   ┌──────────────────────────────┐    │
│  │ MAIN BRAIN │◄───────────────────────►│  Run Ledger (SQLite, events) │    │
│  │ strategic  │                         └──────────────────────────────┘    │
│  └─────┬──────┘                         ┌──────────────────────────────┐    │
│        │ task contracts / budgets       │  Budget Governor (hard caps) │    │
│  ┌─────▼──────────────────────────┐     └──────────────────────────────┘    │
│  │ TEAM RUNTIME (per team)        │     ┌──────────────────────────────┐    │
│  │  ┌────────────┐                │     │  Policy Engine (tool gate)   │    │
│  │  │ TEAM BRAIN │ (or lead role) │     └──────────────────────────────┘    │
│  │  └──┬───┬───┬─┘                │     ┌──────────────────────────────┐    │
│  │     │   │   │   structured     │     │  Provider Router             │    │
│  │   [M1] [M2] [M3]  reports       │◄───►│  tags, fallbacks, routing    │    │
│  │     │   │   │                  │     └──────────────────────────────┘    │
│  │  ┌──▼───▼───▼───────────────┐  │     ┌──────────────────────────────┐    │
│  │  │ Team Blackboard (memory) │  │     │  Context Builder (budgeted)  │    │
│  │  └──────────────────────────┘  │     └──────────────────────────────┘    │
│  └────────────────────────────────┘     ┌──────────────────────────────┐    │
│                                         │  Artifact Store (run workspace)│  │
│                                         └──────────────────────────────┘    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ LLM calls, tool calls
                  ┌─────────────▼──────────────┐
                  │ Hermes turn loop, skills,  │──► OpenAI / Anthropic / Gemini /
                  │ memory, guardrails (reused)│    OpenRouter / Ollama / custom
                  └────────────────────────────┘
```

### Where each Brain lives
- **Main Brain** is one per run. It runs as a process in Airlangga Core, not inside any team. It has *no* domain tools. Its tools are `plan`, `assign(team, contract)`, `reallocate_budget`, `accept/reject`, `ask_human` and `finalize`. It reads only briefs and verdicts. Use your best model here, since it makes few and short calls.
- **Team Brain** is one per team and runs inside the Team Runtime. Its tools are `assign_member`, `request_critique`, `commit_to_blackboard`, `merge`, `rule` and `escalate`. Use a mid-tier model, and for small teams make it a lead member.
- **Members** are specialists with domain tools, narrow allowlists and per-role model policies.

### Context and memory flow (token control)

| Layer | Sees | Never sees |
|---|---|---|
| **Main Brain** | Goal, plan tree, a ≤300-token *brief* per team, verdicts, budget state, escalations | Member transcripts, raw artifacts, tool outputs |
| **Team Brain** | Team charter, task contract, blackboard *digest*, member reports (structured), conflict items | Other teams' internals, Main Brain's full plan beyond its slice |
| **Member** | Role prompt, its contract, *retrieved* blackboard slices (top-k), artifact refs it opens on demand, its private notes | Full blackboard, other members' private notes, budgets of others |

Key mechanics:
1. **Summarise at write time.** Every blackboard entry and report carries a ≤150-token abstract produced when it's written. Readers get abstracts first and pull bodies by ID only if needed.
2. **Pass by reference.** Artifacts and long tool outputs go to the artifact store. Prompts carry `artifact://id` plus an abstract.
3. **Context Builder with hard token budgets** per role and per call. It fills in priority order: contract, then pinned decisions, then retrieved slices, then recent events. It truncates with a visible "N items omitted" marker.
4. **Retrieval:** SQLite FTS5 over blackboard entries plus tags (type, task ID, member). Add optional local embeddings later. No separate service.
5. **Rolling digest** per team. The Team Brain re-compacts it when entries exceed a threshold, and old entries are archived, not deleted.
6. **Typed, versioned blackboard entries** (`fact | decision | open_question | artifact | risk`) with `author`, `evidence`, `confidence`, `valid_until`, `supersedes`. Only the Team Brain commits. Members propose.
7. **Reuse Hermes memory** for long-term, cross-run user/agent memory. The blackboard is *run-and-team-scoped working memory*. Promotion from blackboard to long-term memory is an explicit, Main-Brain-approved step.

### Debate and merge protocol (bounded)
`propose → critique (different model if possible) → revise → decide`. Max 2 rounds. Decision order:
1. A **verifier** result (test, schema or fetch) decides if one exists.
2. Otherwise the **Team Brain rules**, with the reasoning recorded.
3. If the Team Brain is low-confidence or the stakes are flagged, **escalate** to the Main Brain, and then to a human.

The decision is always recorded with the dissent.

### Router
Each model has a profile: `{provider, base_url, auth_ref, tags:[tools,json,vision,long_ctx], ctx_limit, $/Mtok, p50_latency}`. A role policy looks like `{require:[tools,json], prefer:cheapest_above_quality_floor, fallbacks:[...]}`. **Fallbacks must satisfy `require`.** A fallback that fails the capability check is skipped, not used silently. Every switch is logged in the ledger.

---

## (d) Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Infinite debate loops** | Hard round cap (2) and a per-debate token cap. Decision order falls back to verifier, then Team Brain ruling, then escalation. The loop counter lives in the runtime, not the prompt. A repeated-argument detector (embedding or string similarity of consecutive critiques) forces an early close. |
| **Main Brain bottleneck** | Main Brain is *event-driven and low-frequency*: it wakes on contract completion, escalation, budget threshold or checkpoint, not on every message. Teams run in parallel and can finish a contract without waking it. Pre-delegated authority (team-level retries, member swaps and budget slack of X%) means most failures never reach it. Keep its context to briefs only. |
| **Context explosion** | The layered visibility table, write-time abstracts, pass-by-reference, per-call token budgets in the Context Builder and digest compaction. Add a hard alarm when any prompt exceeds its role's budget, and log it as a defect. |
| **Conflicting provider outputs** | Don't average. Normalise outputs through output schemas. Use verifiers where possible. Have a *different* model critique. Record provider and model on every blackboard entry so contradictions are attributable. Treat disagreement as a conflict item, not a merge. Pin a "reference" model per decision type. |
| **Cost runaway** | The Budget Governor lives outside the agents and enforces caps on tokens, dollars, time and tool calls at four levels (run, team, member, call). It does a pre-flight cost estimate and requires human approval above a threshold. It defaults to local/cheap models for drafting. A circuit breaker pauses the run and pings the user. Pricing comes from the router's model profiles, and unknown models are priced conservatively. |
| **Guardrail bypass by a team member** | Enforce at the **tool-call boundary** in the runtime. Each member's allowlist is per role. A member *can't* grant itself tools, and neither can a Team Brain, because tool scopes are set by the template or Main Brain and signed in the contract. Treat inter-agent messages as **untrusted input** (prompt-injection from tool outputs or other members is the real vector). Keep Hermes's 8 guardrail layers *below* Airlangga, so every member call goes through them. Log every denied call. Approval-required actions go to a human, never to a Brain. |
| **Stale shared memory** | `valid_until` and `supersedes` fields, entry versions, and a staleness check at read time (source artifact hash changed means the entry is flagged). Only the Team Brain commits. A periodic digest rebuild can drop superseded items. Anything marked `fact` needs evidence refs. When it's stale, the reader sees a "stale?" marker rather than silent trust. |
| **Fork drift from Hermes** | Layered package plus a small upstreamable hook set (see §0). Pin a Hermes version, and run a smoke suite on upgrade. |
| **Failure cascades and partial state** | The ledger makes every step resumable and idempotent. Contracts carry idempotency keys. Tools with side effects need an "undo or approval" classification. |
| **Complexity overhead on simple tasks** | A *fast path*: a single-member contract skips the Team Brain and debate. The Main Brain can answer trivially simple requests without spawning anything. |
| **Eval blindness** (you can't tell if the team beats a single agent) | The replay harness (§a) should include a "single Hermes agent" baseline. If the team doesn't beat it on cost-adjusted quality for a task type, don't use a team for that type. |

---

## (e) v1 vs v2

### v1 (target: ~6–8 weeks, one or two engineers)

1. Airlangga package on top of Hermes, with a small hook patch set and no wholesale fork.
2. **Run ledger** (SQLite event log) with resume-after-restart.
3. **Main Brain** with plan, assign, accept/reject and finalize. Event-driven.
4. **Team Runtime with 2–3 hand-written templates** (for example research, code+review). The Team Brain is a *lead role* rather than a separate tier.
5. **Task contracts** with an output schema and an acceptance check (schema validation, a shell test command, or an LLM judge).
6. **Blackboard** with typed entries, write-time abstracts, FTS5 retrieval and Team Brain commit-only writes.
7. **Context Builder** with per-role token budgets and pass-by-reference artifacts.
8. **Provider router** with static per-role policies, capability tags and ordered fallback chains. Support OpenAI-compatible, Anthropic, Gemini and Ollama/custom base_url.
9. **Budget Governor** with hard caps (tokens, dollars, time) at run and team level, plus a circuit breaker.
10. **Policy engine** with per-role tool allowlists and approval-required actions, routed through the Hermes gateway.
11. **Bounded debate** (propose, critique, decide, max 2 rounds) with recorded dissent.
12. **CLI trace viewer** and a **replay command**, with a single-agent baseline for comparison.
13. Telegram/Discord status and approvals via the existing Hermes gateway, with cron triggers reused from Hermes.
14. English-only UX, YAML config, single-VPS deployment with SQLite and local files. Default config works with a local Ollama model, and paid APIs are opt-in.

### v1 non-goals
- A separate Team Brain LLM tier (it's a lead role in v1).
- Learned or adaptive routing, and cost/quality auto-tuning.
- Dynamic team creation by agents at runtime.
- Vote-based consensus. Cross-run agent track-record scoring.
- A web UI beyond a simple read-only trace page, and a visual team builder.
- Multi-user and multi-tenant support, and distributed or multi-node execution.
- A vector DB service.
- Template marketplace, voice, and any new gateway, skills or cron implementation.

### v2
- A **separate Team Brain tier** for large teams, with team-of-teams and cross-team contracts.
- **Track-record-aware routing**: per-member and per-model success, cost and latency stats feed the router, and the Main Brain can swap underperformers.
- **Local embeddings** and hybrid retrieval, plus automated blackboard compaction with quality checks.
- **Selective consensus** (N-model vote) for flagged high-stakes decisions only.
- **Web dashboard** with live traces, budget burn-down and one-click approvals.
- **Team template sharing and import**, with signature checks.
- **Eval suites** per template, regression-gated on model or prompt changes.
- **Long-term memory promotion pipeline** from blackboard to Hermes memory, with review.
- Optional **multi-process or multi-VPS** worker pools.

---

## Bottom line

The strongest ideas in the brief are the **contracts, the budget delegation and the bounded debate**. They're what separate this from a swarm or a router. The weakest points are the **two-brain hierarchy as an always-on LLM tier**, the **fork instead of a layer**, and **"any model per member" without capability gating**. If v1 ships only the ledger, contracts, budget governor, policy engine and blackboard, it already beats a single agent on long tasks in the ways that matter: resumability, cost control and auditability.
