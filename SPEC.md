# Airlangga — Specification

- **Status:** Design spec, v2.0 — synthesis only. No code has been written against this spec.
- **Date:** 2026-11-20 (revised after user correction)
- **Sources:** `teardown-hermes.md` (Hermes Agent v0.23.2, read-only inspection, 2026-11-20) and `ag-input.md` (Antigravity/AG design review, 2026-11-20) — used as **learning material only** (see §9).
- **Build decision (user, overrides all earlier framing):** Airlangga is built **FROM SCRATCH, from zero**. No copy, no fork, no layer on Hermes, no importing Hermes libraries, no vendoring Hermes modules. Every component in this spec is an original design. The teardown taught concepts (what a provider abstraction does, what a turn loop does, what guardrail categories are needed); the implementation must be clean, original IP, so it can be commercialised later without licence or attribution entanglement with Hermes.
- **Language rule:** all project content in English; USD, UTC, en-US numbers.

---

## 1. Vision

Airlangga is a persistent, accountable **Agentic Team** runtime built from scratch: a user gives one goal to a Main Brain, the Main Brain decomposes it into signed task contracts and delegates them to named, persistent team members — each running a different AI model of the user's choosing, official API or custom endpoint — and the team returns structured, verifiable results under a hard budget, a durable run ledger, and human approval for anything risky. The name honours **Airlangga, the 11th-century Javanese king who reunified a fragmented East Java and founded the kingdom of Kahuripan after a period of chaos** — the product's job is the same in miniature: take a fragmented, multi-model, multi-member effort and hold it together under one accountable rule, with every decision recorded and every member's track record surviving the run.

---

## 2. What an Agentic Team is

An Agentic Team is **not** a swarm, **not** a set of one-shot subagents, and **not** a plain orchestrator/router. It is a persistent organisation with five concrete mechanics that none of the alternatives has together:

1. **Contracts, not conversations.** Work crosses layers only as a signed task contract (goal, inputs as artifact references, output schema, acceptance check, budget, deadline, idempotency key) and returns only as a structured report (claims, evidence refs, confidence, diff). There is no "ask the child in free text and hope".
2. **Persistent identity.** A team and each member are durable records — charter, role prompt, tool permissions, model policy, private notes, track record — stored in the run ledger and roster config. A member is *activated* per task with a fresh, budgeted context built from that record; it is not a long-lived chat thread and not a process that stays alive between tasks. Persistent *state*, not persistent processes.
3. **A blackboard with commit rules.** Shared working memory is a typed, versioned blackboard (`fact | decision | open_question | artifact | risk`, with `author`, `evidence`, `confidence`, `valid_until`, `supersedes`). Members *propose* entries; only the Team Brain (or lead member in v1) *commits* them. This stops memory pollution, which is what unstructured shared scratch becomes.
4. **Budget as a delegated resource.** The Main Brain allocates a budget top-down (tokens, dollars, wall-clock, tool calls); the team sub-allocates it to members; a runtime governor enforces the caps outside any LLM. A member cannot spend its way out of a bad plan.
5. **Explicit dissent and merge.** A member can formally dissent from a decision; dissent is recorded in the ledger and resolved by a bounded protocol (§5), never by last-write-wins or by silent averaging.

### Comparison table

| Dimension | Swarm | One-shot subagents | Plain orchestrator / router | **Agentic Team (Airlangga)** |
|---|---|---|---|---|
| **Persistence** | None / ephemeral; agents spawn and die | None; dies when the task returns | Orchestrator has a session; workers stateless | Team + member identities persist across runs (charter, notes, track record). Activations are on-demand, context rebuilt per activation. |
| **Memory** | Implicit, via message passing or shared scratch | Parent passes a prompt; result returns as text | Orchestrator's context only | Typed team blackboard with provenance, versions, TTL + per-member private notes. Promotion to long-term memory is an explicit, Main-Brain-approved step. |
| **Authority** | Flat or emergent | Parent absolute | Orchestrator absolute, routes | Layered and explicit: Main Brain owns goal, budget, verdict. Team Brain owns tactical decisions inside its contract. Members own their output. A member can formally dissent. |
| **Communication** | Broadcast / peer-to-peer, unstructured | Prompt in, text out | Hub-and-spoke | Structured reports through the team channel. Members do not talk to the Main Brain directly; member-to-member traffic goes through the blackboard / Team Brain, never as free-form chat. |
| **Conflict handling** | None, or last-write-wins / voting | None (single result) | Orchestrator picks or re-asks | Bounded protocol: propose → critique (preferably a different model) → revise → decide, max 2 rounds. Decision order: verifier result, then Team Brain ruling, then escalation. Dissent always recorded. |
| **Failure handling** | Redundancy hides failures | Parent retries or gives up | Orchestrator retries | Typed failures (tool error, budget, quality gate, provider outage) each with a policy: retry, swap member, swap model via capability-gated fallback, escalate, abort. State checkpointed in the ledger; contracts carry idempotency keys. |
| **Cost** | High, unpredictable (N parallel agents) | Low, predictable | Low–medium | Medium–high by design, but capped. Budgets allocated top-down and enforced by the runtime. Cheap/local models do the bulk; strong models gate decisions. |
| **Auditability** | Low (no durable record of who decided what) | Low (result text only) | Medium (orchestrator log) | High: append-only run ledger — every plan, assignment, message, tool call, cost, verdict, dissent is an event. Replayable. |

---

## 3. Architecture — a new, small, original core

### 3.1 Principle: from scratch, small core, no inherited code

Airlangga is a **new codebase written from zero**. It does not copy, fork, layer on, import, or vendor any part of Hermes. Concepts learned from the Hermes teardown — that a provider abstraction should separate endpoint/auth/wire-format from the agent, that a turn loop needs billing, retry, recovery and overflow handling, that guardrails belong in layers, that a durable typed log is how a system survives a restart — are *ideas*, and ideas are re-implemented here in original code with our own names, structures, and interfaces. Nothing in this spec is a Hermes file, class, or function renamed: every component below is specified by what **it must do**, not by what it reuses. The core stays small on purpose: team runtime + roster/config + blackboard + ledger + layered prompts + provider abstraction + budget/policy enforcement. Everything else (chat front-ends, skills catalogues, schedulers) is either out of scope for v1 or built later, in our own code, if needed at all.

### 3.2 Components (all original — **Build**)

| Component | What it must do |
|---|---|
| **Main Brain** | One per run. Strategic only. No domain tools. Its only tools are `plan`, `assign(team, contract)`, `reallocate_budget`, `accept/reject`, `ask_human`, `finalize`. Event-driven: it wakes on contract completion, escalation, budget threshold, or checkpoint — not on every message. It reads only briefs and verdicts, never member transcripts. It runs on the best available model, because it makes few, short calls. |
| **Team Runtime** | One per team. Owns the roster, the blackboard, the debate, and member lifecycle for that team. It is the only component that may activate members, commit blackboard entries, or settle conflicts inside a team. |
| **Team Brain** | One per team, inside the Team Runtime. Its tools are `assign_member`, `request_critique`, `commit_to_blackboard`, `merge`, `rule`, `escalate`. Mid-tier model. **Optional in v1:** teams of 1–3 members use a **lead member** in this role instead of a separate LLM tier, saving 2 extra LLM hops per task. A separate tier returns in v2 for large teams / team-of-teams. |
| **Members** | Named specialists. Each member is a durable record (charter, role prompt, tool permissions, model policy, private notes, track record) plus, at activation time, a fresh agent session built from that record with a hard context budget. Lifecycle states: `IDLE / WORKING / BLOCKED / REVIEWING / DONE`, plus steering, handoff, and replacement of a failed member. Members never talk to the Main Brain directly and never message each other as free-form chat. |
| **Turn Loop** | Our own single-agent loop, written from first principles: assemble messages → call the model (streaming preferred) → dispatch tool calls → feed tool results back → repeat until a stop condition. Stop conditions, retry with backoff, recovery from a failed tool call, and overflow handling (context compaction when the window fills) are runtime concerns, not prompt instructions. Each Brain and each member activation runs one instance of this loop. The loop is deliberately the smallest loop that is correct; team behaviour lives in the Team Runtime above it, not inside it. |
| **Run Ledger** | Append-only, event-sourced SQLite database (WAL mode). Every plan, assignment, message, tool call, cost, verdict, dissent, and fallback switch is an immutable event with a timestamp, actor, and causal parent. This is the #1 must-have: resume after a crash, audit, replay, debugging. On restart the runtime replays events to reconstruct plan tree, contract states, blackboard, budgets consumed, and member states — no run depends on a process staying alive. |
| **Budget Governor** | Hard caps on tokens, dollars, wall-clock time, and tool calls at four levels (run, team, member, single call), enforced **outside** the LLMs by the runtime. It does a pre-flight cost estimate before an activation, tracks spend live, and trips a circuit breaker that pauses the run and pings the user when a cap is hit or approached. Unknown models are priced conservatively. A member or team can never spend past its allocation by asking nicely. |
| **Task Contracts** | The schema for every assignment: goal, inputs (artifact references), output schema, acceptance check, budget, deadline, idempotency key. Contracts are signed by the issuer (Main Brain or Team Brain) and validated by the runtime before a member may start. A report that fails its output schema is a typed quality-gate failure, not a conversation to repair in chat. |
| **Blackboard** | Durable shared working memory for one team and one run: typed, versioned entries (`fact | decision | open_question | artifact | risk`) with `author`, `evidence`, `confidence`, `valid_until`, `supersedes`. Every entry and report carries a ≤150-token abstract written at write time; readers get abstracts first and pull bodies by ID only if needed. Retrieval is full-text search over entries plus tags (type, task ID, member). Only the Team Brain commits; members propose. Entries go stale visibly: a `valid_until` expiry or a changed source-artifact hash flags the entry "stale?" at read time, never silently trusted. Old entries are archived, not deleted. |
| **Context Builder** | Assembles each activation's context under a hard per-role token budget, in priority order: contract → pinned decisions → retrieved blackboard slices (top-k) → recent events. Long content is passed by reference (`artifact://id` + abstract), never pasted wholesale. Truncation leaves a visible "N items omitted" marker; exceeding a role's budget raises a logged defect alarm. Prompts are assembled in three layers — Main Brain (goal, delegation policy, synthesis rules), Team Brain (team goal, roster, shared context), Member (role, tools, output contract) — never by inheriting a parent's full context. |
| **Provider Router** | Routes each activation to a model by capability, not by name. Every model in the registry carries capability tags (`tool_calling`, `structured_json`, `vision`, `long_context`, `cost_per_mtok`, `latency_p50`, `context_limit`). A role policy declares what it requires; routing is by purpose with static rules first. Fallback chains are **capability-gated**: a fallback that fails the role's required capabilities is skipped, never used silently. Every switch is a ledger event. (Concept learned from the teardown: fallbacks exist in other systems, but ungated downgrade silently changes behaviour — the gating is part of our design, not borrowed code.) |
| **Policy Engine** | Per-role tool allowlists, path and network scopes, and approval-required actions, enforced at the tool-call boundary by the runtime — before the call executes. A member cannot grant itself tools; neither can a Team Brain; scopes are set by the team template / Main Brain and signed into the contract. Every denied call is logged in the ledger. |
| **Artifact Store** | Per-run workspace on disk. Files, patches, and reports live here and are passed by reference, never pasted into prompts. Each artifact has an ID, a content hash, an author, and a version; the blackboard references artifacts by ID, so a changed artifact is detectable (§5.6). |
| **Trace / Replay** | CLI trace viewer first (plan tree, who said what, cost per node, debate outcomes), then a read-only web trace page. A `replay` command re-runs a recorded task against a different model config and compares cost and pass rate, including a **single-agent baseline** — if the team does not beat the baseline on cost-adjusted quality for a task type, do not use a team for that type. |
| **Control Surface (v1)** | CLI plus a minimal HTTP API server (OpenAI-compatible request shape for model calls only where useful). Human-in-the-loop approvals (plan approval, spend above threshold, risky tools, escalations) go to the user through a messaging channel (Telegram/Discord) driven by our own small notifier; the CLI is the fallback. No nine-platform chat surface in v1. |
| **Long-term Memory** | Cross-run user/team memory, separate from the blackboard. The blackboard is run-and-team-scoped working memory; promotion from blackboard to long-term memory is an explicit, Main-Brain-approved step, with provenance kept. Per-member private notes are never promoted without that approval and never visible to other members. |
| **Scheduler** | Our own small job runner (tick loop with a file lock so overlapping ticks cannot run). Team-scheduled work is a job with a team target, a contract template, and its own budget. It reuses the same ledger, contracts, and governor as interactive runs — scheduled and interactive runs are the same code path. |

### 3.3 Diagram (text)

```
  Telegram / Discord / CLI / scheduler (our control surface)
        │  goal / approvals / status
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  AIRLANGGA CORE (new package, written from scratch)              │
│                                                                  │
│  ┌────────────┐  plan / assign / verdict   ┌───────────────────┐  │
│  │ MAIN BRAIN │◄──────────────────────────►│ Run Ledger        │  │
│  │ strategic  │                             │ (SQLite, events)  │  │
│  └─────┬──────┘  task contracts / budgets  └───────────────────┘  │
│        │                                   ┌───────────────────┐  │
│  ┌─────▼──────────────────────────┐        │ Budget Governor   │  │
│  │ TEAM RUNTIME (per team)        │        │ (hard caps)       │  │
│  │  ┌────────────┐                │        └───────────────────┘  │
│  │  │ TEAM BRAIN │ (or lead role) │        ┌───────────────────┐  │
│  │  │            │  turn loop     │        │ Policy Engine     │  │
│  │  └──┬───┬───┬─┘  (ours)        │        │ (tool gate)       │  │
│  │     │   │   │  structured      │        └───────────────────┘  │
│  │   [M1] [M2] [M3]  reports      │        ┌───────────────────┐  │
│  │     │   │   │                  │        │ Provider Router   │  │
│  │  ┌──▼───▼───▼──────────────┐  │◄──────►│ tags, fallbacks   │  │
│  │  │ Team Blackboard         │  │        └───────────────────┘  │
│  │  └─────────────────────────┘  │        ┌───────────────────┐  │
│  └────────────────────────────────┘        │ Context Builder   │  │
│                                            │ (per-role budgets)│  │
│                                            └───────────────────┘  │
│                                            ┌───────────────────┐  │
│                                            │ Artifact Store    │  │
│                                            │ (run workspace)   │  │
│                                            └───────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │ LLM calls, tool calls
                  ┌─────────────▼──────────────┐
                  │ Provider abstraction       │──► Anthropic / OpenAI /
                  │ (ours, §4.1)               │    Gemini / OpenRouter /
                  │ + our turn loop            │    Ollama / custom endpoint
                  └────────────────────────────┘
```

### 3.4 Where each Brain lives

- **Main Brain:** one per run, in Airlangga Core, not inside any team. No domain tools. Best available model (few, short calls). Sees goal, plan tree, ≤300-token briefs per team, verdicts, budget state, escalations.
- **Team Brain:** one per team, inside the Team Runtime. Mid-tier model. In v1, replaced by a **lead member** for teams of 1–3 members. Sees team charter, task contract, blackboard digest, member reports (structured), conflict items.
- **Members:** specialists with domain tools, narrow allowlists, per-role model policies. Each activation builds a fresh context from its durable record; nothing persists as a chat thread between activations.

### 3.5 Context visibility table

| Layer | Sees | Never sees |
|---|---|---|
| **Main Brain** | Goal, plan tree, ≤300-token brief per team, verdicts, budget state, escalations | Member transcripts, raw artifacts, tool outputs |
| **Team Brain / lead** | Team charter, task contract, blackboard digest, member structured reports, conflict items | Other teams' internals, Main Brain's full plan beyond its slice |
| **Member** | Role prompt, its contract, retrieved blackboard slices (top-k), artifact refs it opens on demand, its private notes | Full blackboard, other members' private notes, other members' budgets, other members' credentials |

Mechanics: summarise at write time (every blackboard entry and report carries a ≤150-token abstract); pass by reference (`artifact://id`); Context Builder with hard per-role token budgets, priority-ordered fill, visible omission markers; retrieval via full-text search over blackboard entries + tags (type, task ID, member); rolling team digest re-compacted by the Team Brain when entries exceed a threshold, old entries archived not deleted; typed versioned entries with `author`, `evidence`, `confidence`, `valid_until`, `supersedes`; only the Team Brain commits, members propose.

---

## 4. Multi-AI configuration

### 4.1 Our provider abstraction — designed from first principles

The provider layer answers one question: **how does an agent session talk to any LLM, anywhere, without the rest of the system knowing which vendor it is?** Our design, in our own terms:

- **A model endpoint is a record with four parts:** (a) *where to call* — an endpoint URL (official vendor API or a custom base URL); (b) *how to authenticate* — a credential reference (environment variable, a command that mints a short-lived token, or a vault reference — never a secret pasted into config or prompts); (c) *which wire format* — one of the small set of request/response shapes the industry actually uses (OpenAI-compatible chat completions, Anthropic Messages, Gemini, or a local OpenAI-compatible server); (d) *what it can do and what it costs* — capability tags, context limit, price per million tokens, typical latency.
- **Wire formats are adapters, not vendors.** The system knows four wire formats. A vendor is just a named endpoint that speaks one of them. Adding a new vendor means adding a one-line endpoint record, not new code — unless it speaks a genuinely new wire format, in which case one new adapter is written.
- **Official API and custom endpoint are the same path.** Whether the URL is `api.anthropic.com`, a vendor's own API, or `http://localhost:11434/v1` on the user's machine, the record shape is identical. Local models (Ollama and any OpenAI-compatible local server) are first-class, not a special case.
- **One active model per activation, switchable by the router.** The router (§3.2) picks the endpoint per activation from the member's pinned model first, then its capability-gated fallback chain. A switch mid-task is a ledger event, never silent.
- **Credential isolation per member.** Each member's credential scope is separate; the router resolves credentials only for the activation it is serving, and a credential reference never enters another member's context, blackboard entry, or report.
- **No global default model.** The config has no single "the model". The Main Brain has its own default; every member pins its own. (Concept learned from the teardown: a single global default is the wrong shape for a team — the conclusion is ours, the implementation is ours.)

### 4.2 Full YAML example — team `research-01`, 3 members, 3 providers

```yaml
# airlangga.yaml — example only; no real keys in this file
# (auth_ref = env var / token-minting command / vault reference, never a secret)
version: 1
defaults:
  currency: USD
  timezone: UTC

main_brain:
  provider: anthropic            # official API
  model: claude-opus-4-6
  auth_ref: env:ANTHROPIC_API_KEY
  max_tokens_per_call: 4096
  budget: { tokens: 200000, usd: 20.00, wall_clock_min: 120, tool_calls: 200 }
  tools: [plan, assign, reallocate_budget, accept, reject, ask_human, finalize]
  # Main Brain has NO domain tools (no shell, no file write, no browser).

teams:
  research-01:
    template: research
    goal: "Produce a sourced brief on <topic> with claims, evidence refs, and open questions."
    team_budget: { tokens: 1500000, usd: 15.00, wall_clock_min: 90, tool_calls: 600 }
    # v1: lead role, not a separate Team Brain tier (see §7, open decision 2).
    team_brain_mode: lead_member   # lead_member | separate (v2)
    lead_member: researcher

    members:
      - id: researcher
        role: researcher
        provider: anthropic        # official API
        model: claude-sonnet-4-5
        auth_ref: env:ANTHROPIC_API_KEY
        wire_format: anthropic_messages
        capabilities: [tool_calling, structured_json, long_context]
        context_limit: 200000
        cost_per_mtok_usd: 3.00
        toolsets: [web, file_read, skills_research]
        skills: [research]
        budget: { tokens: 600000, usd: 6.00, wall_clock_min: 45, tool_calls: 200 }
        approval: smart            # §6; never "off" for a tool-using member
        fallback:
          - provider: openai       # capability-gated: must satisfy require below
            model: gpt-5-mini
            auth_ref: env:OPENAI_API_KEY
            wire_format: openai_chat
            capabilities: [tool_calling, structured_json]
          - provider: ollama       # local, last resort
            model: qwen3:8b
            endpoint: http://localhost:11434/v1
            auth_ref: none
            wire_format: openai_chat
            capabilities: [tool_calling, structured_json]
        routing_policy:
          require: [tool_calling, structured_json]
          prefer: cheapest_above_quality_floor

      - id: fact_checker
        role: critic
        provider: custom           # OpenAI-compatible custom endpoint
        model: deepseek-chat
        endpoint: https://api.deepseek.com/v1
        auth_ref: env:DEEPSEEK_API_KEY
        wire_format: openai_chat
        capabilities: [tool_calling, structured_json]
        context_limit: 64000
        cost_per_mtok_usd: 0.28
        toolsets: [web, file_read]
        skills: []
        budget: { tokens: 400000, usd: 3.00, wall_clock_min: 30, tool_calls: 150 }
        approval: smart
        fallback:
          - provider: ollama
            model: qwen3:8b
            endpoint: http://localhost:11434/v1
            auth_ref: none
            wire_format: openai_chat
            capabilities: [tool_calling, structured_json]
        routing_policy:
          require: [tool_calling, structured_json]
          prefer: cheapest_above_quality_floor
        # Critic SHOULD be a different model/provider from the proposer where
        # possible (§5 debate) — here DeepSeek critiques Anthropic's draft.

      - id: writer
        role: writer
        provider: ollama           # local model, first-class
        model: llama3.1:8b
        endpoint: http://localhost:11434/v1
        auth_ref: none
        wire_format: openai_chat
        capabilities: [tool_calling, structured_json]
        context_limit: 128000
        cost_per_mtok_usd: 0.00
        toolsets: [file_write]
        skills: []
        budget: { tokens: 500000, usd: 0.00, wall_clock_min: 30, tool_calls: 100 }
        approval: smart
        fallback: []               # local writer has no fallback; failure escalates (§5)
        routing_policy:
          require: [tool_calling, structured_json]
          prefer: local_first

    policy:
      # Per-member allowlists are signed into each contract (§6).
      # Writer may write only inside the run workspace; researcher is read-only
      # on the filesystem except the artifact store; no member may run shell.
      network_scope: [allow: web_search, api.deepseek.com, api.anthropic.com]
      approval_required: [spend_above_usd_5, external_post, file_write_outside_workspace]
```

Notes on the example: the three members genuinely run three different providers (Anthropic official API, DeepSeek via an OpenAI-compatible custom endpoint, Ollama local at `http://localhost:11434/v1`). The critic is deliberately a different model from the proposer. The writer is local and free, which is what makes the default config work without a paid service. Per-member `budget` and `approval` are enforced by the runtime, not requested of the model. Team templates (`research`, `code+review`, `content`) are versioned YAML files users can share — templates are the onboarding path, not hand-assembled rosters.

---

## 5. Protocols

### 5.1 Goal decomposition (Main Brain)

1. User goal arrives via the control surface or scheduler. Main Brain produces a **plan tree**: goal → sub-goals → task contracts, each with an owner team, a budget slice, and a deadline. The plan tree is a ledger event.
2. Main Brain assigns contracts to teams; it does not do member work itself and does not see member transcripts (§3.5).
3. **Fast path:** a trivially simple request, or a single-member contract, skips the Team Brain and debate entirely. The Main Brain may answer without spawning anything.
4. Pre-delegated authority: team-level retries, member swaps, and budget slack of X% (default 10%, set per team) are authorised in the contract, so most failures never wake the Main Brain. The Main Brain is event-driven and low-frequency by design.

### 5.2 Assignment (Team Runtime / Team Brain or lead)

1. Team Brain (or lead member in v1) receives the contract, decomposes it into member assignments, each itself a mini-contract (goal, inputs as artifact refs, output schema, acceptance check, budget, deadline, idempotency key).
2. Assignments go through the Provider Router (§4.1): the member's pinned model is used first; on provider outage / budget pressure, the capability-gated fallback chain is consulted and the switch is logged.
3. Members activate with a fresh context built by the Context Builder from their durable record + contract + retrieved blackboard slices. No long-lived thread is resumed.
4. Member states: `IDLE → WORKING → REVIEWING → DONE`, with `BLOCKED` on a typed failure. Steering, handoff, and replacement of a failed member are Team Brain operations, recorded in the ledger.

### 5.3 Structured reports

A member returns only a structured report, never free-form chat:

```yaml
report:
  contract_id: <id>
  member_id: <id>
  claims: [{ claim: "...", evidence_refs: [artifact://...], confidence: 0.0-1.0 }]
  diff: artifact://...            # what changed, by reference
  open_questions: [...]
  cost: { tokens: n, usd: n, tool_calls: n, wall_clock_s: n }
  verdict_self: pass | fail | partial
```

Reports are blackboard proposals until the Team Brain commits them. A report that fails its output schema is a typed quality-gate failure (§5.5), not a conversation to repair in chat.

### 5.4 Bounded debate (propose → critique → revise → decide)

Applies only to contested decisions (conflicting claims, low-confidence verdicts, flagged high-stakes items). Not the default path for routine work.

```
propose → critique (preferably a different model/provider) → revise → decide
```

- **Max 2 rounds**, hard cap enforced by a runtime loop counter, not by the prompt. Per-debate token cap as well. A repeated-argument detector (string/embedding similarity of consecutive critiques) forces an early close.
- **Decision order (fixed):** (1) a **verifier** result decides if one exists — executable checks (tests, linters, schema validation, URL fetch, diff check), not just an LLM judge; (2) otherwise the **Team Brain rules**, reasoning recorded; (3) if the Team Brain is low-confidence or stakes are flagged, **escalate** to the Main Brain, then to a human.
- **Dissent is always recorded** in the ledger with the decision, including who dissented and why. A dissenting member's track record is visible to the router later (v2: track-record-aware routing).
- **Merge step:** after a decision, the Team Brain commits the merged blackboard entries (with `supersedes` links to the losing entries) and closes the conflict item. Conflicting provider outputs are never averaged; they are normalised through output schemas, attributed by provider/model on every entry, and treated as a conflict item, not a merge.

### 5.5 Failure types and policies

| Failure type | Detection | Policy (in priority order) |
|---|---|---|
| Tool error | Tool executor / turn loop | Retry once with same member (idempotency key); then swap member; then escalate. |
| Budget exceeded | Budget Governor (pre-flight + live) | Pause member/team; circuit breaker pings user; Main Brain may reallocate from slack or request human approval for more spend. Never silently continue. |
| Quality gate failed | Acceptance check / verifier / schema validation | One revise round (bounded debate if contested); then swap member or model via fallback; then escalate to human. |
| Provider outage / rate limit | Router / credential cooldowns | Capability-gated fallback (§4.1); if no fallback satisfies `require`, escalate — do not downgrade silently. |
| Member blocked / unresponsive | Lifecycle watchdog (stall guard, hard stop) | Mark `BLOCKED`, reassign contract to another member (handoff with blackboard state, not a re-prompt from scratch); record in ledger. |
| Guardrail / policy denial | Policy Engine / safety layers (§6) | Denial is terminal for that call; logged; member may propose an alternative within its allowlist; repeated denials escalate. |
| Stale shared memory | `valid_until` / artifact-hash check at read time | Reader sees a "stale?" marker, never silent trust; Team Brain rebuilds the digest; superseded entries archived. |

### 5.6 Resume after crash

The run ledger is the resume mechanism. On restart, the runtime replays ledger events to reconstruct: plan tree, contract states, blackboard, budgets consumed, and member states. Contracts carry idempotency keys so a re-executed side-effecting step is safe or explicitly approval-gated. Tools with side effects carry an "undo or approval" classification in their contract. Abandoned assignments are recovered from the ledger (claim/release/delivery semantics recorded as events, not as in-memory state). No run depends on a process staying alive: persistent state, not persistent processes.

---

## 6. Guardrails — our own safety layers, designed from first principles

The teardown showed *which categories* of safety a tool-using agent needs; the layers below are our own design, written from scratch, in our own code. No Hermes guardrail code is reused, copied, or vendored. The principle throughout: **enforcement lives in the runtime, at the boundary where an action would happen — never only in a prompt.**

| # | Layer (ours) | What it must do |
|---|---|---|
| 1 | **Approval gates + hardline denylist** | A pattern denylist (destructive commands, credential exfiltration, privilege escalation, and similar) is checked on every proposed tool call and can never be overridden by any mode, any Brain, or any member — the hardline floor is always live. Above the floor, an approval mode decides what needs a human: `smart` by default (risky actions ask; routine actions proceed), `approve` (ask every time) for sensitive deployments, `off` only behind an explicit disposable-host flag. |
| 2 | **File-write safety** | A denylist of paths that may never be written or patched by an agent (SSH keys, cloud credentials, system auth files, environment/secret files, our own credential stores), plus a write-root confinement: agent writes land only inside the run workspace unless a contract explicitly grants a wider, named path. This layer is independent of the terminal path, so it holds even when approvals are off. |
| 3 | **Skill / extension guard** | Any skill, plugin, or extension is scanned before it is loaded or installed, because loaded code executes with the agent's privileges. The scan looks for credential access, network exfiltration, and destructive operations, and produces a finding report; a finding blocks installation until a human clears it. |
| 4 | **Tool loop brake** | Detects identical repeated calls, A-B-A-B call cycles, and stalled turns (many calls, no progress), and stops the turn with a typed failure instead of letting it burn budget. Configurable per role; the watchdog is a runtime counter, not a prompt instruction. |
| 5 | **Runtime self-protection** | The agent may never delete, overwrite, or disable its own runtime, interpreter, ledger, or config — checked on every file/terminal action, not bypassable from inside a session by any mode flag. (Honest caveat: a human with host root access can still edit files from outside the session; that is outside the agent's threat model.) |
| 6 | **Admission control** | The control surface (CLI, API, messaging channel) admits only explicitly listed users/keys. Default is deny: with no allowlist configured, nobody is admitted. The allowlist must be set and verified explicitly before first use. |
| 7 | **Execution isolation** | v1 runs commands on the host the user controls, with the risk stated plainly: the OS is the only boundary. Containerised execution (per-run sandbox) is a v2 hardening item. Until then, the file-write safety layer (§6 layer 2), the approval gates, and the policy engine are the boundaries that matter — and the default config never runs as an unrestricted privileged user on a shared host. |
| 8 | **Secret handling + input hygiene** | Secrets are redacted from logs, traces, blackboard entries, and reports (connection strings, headers, vault values, credential-store paths). URLs fetched by tools pass an SSRF / allowlist policy. Context files and tool outputs are scanned for injected instructions before they enter a prompt — and, decisively, **inter-agent messages are treated as untrusted input** (see §6.2): a tool output or another member's message can carry data, never instructions. |

### 6.2 Team-level guardrails (built into the Team Runtime)

- **Per-member allowlists**, signed into each contract by the template / Main Brain. A researcher member may be read-only; a coder member needs `smart` approval; a writer may write only inside the run workspace. A member cannot grant itself tools, and neither can a Team Brain.
- **Inter-agent messages are untrusted input.** Tool outputs and other members' messages are treated as untrusted data, not instructions — prompt-injection from a tool output or a compromised member is the real vector. The Policy Engine enforces this at the tool-call boundary, not in a prompt. Every denied call is logged in the ledger.
- **Approvals go to a human, never to a Brain.** Plan approval, spend above threshold, risky tools, escalations — all routed to the user. No Brain approves another Brain's risky action.
- **Cross-member secret isolation.** Per-member credential scoping (§4.1); one member's credentials never enter another member's context, blackboard entry, or report.

### 6.3 Approvals mode decision — **smart, not off**

Default for any member with tool access: **`smart`**. `off` is permitted only behind an explicit, disposable-host flag, set deliberately per deployment, never by inheriting a config file. Unattended / scheduled runs default to `approve` unless the user explicitly orders otherwise for a named, bounded job. This decision is made here, in this spec, on purpose — it is not inherited from any inspected config.

---

## 7. v1 scope vs v2, non-goals, open decisions

### 7.1 v1 scope (6–8 weeks, 1–2 engineers)

| # | Item |
|---|---|
| 1 | Airlangga package, written from scratch (own licence, §9); pinned generic dependencies only |
| 2 | Run Ledger (SQLite WAL, event-sourced) with resume-after-restart |
| 3 | Main Brain (plan, assign, accept/reject, finalize; event-driven) + our own turn loop |
| 4 | Team Runtime with 2–3 hand-written templates (`research`, `code+review`, `content`); Team Brain as **lead role**, not a separate tier |
| 5 | Task contracts (output schema + acceptance check: schema validation, shell test command, or LLM judge) + executable verifiers |
| 6 | Blackboard (typed entries, write-time abstracts, full-text retrieval, Team-Brain commit-only writes) |
| 7 | Context Builder (per-role token budgets, pass-by-reference artifacts) |
| 8 | Provider abstraction + Router (static per-role policies, capability tags, ordered gated fallbacks; OpenAI-compatible, Anthropic, Gemini, Ollama/custom endpoint) |
| 9 | Budget Governor (hard caps: tokens, dollars, time, tool calls; run + team level; circuit breaker) |
| 10 | Policy Engine (per-role tool allowlists, approval-required actions) + our 8 safety layers (§6) |
| 11 | Bounded debate (propose → critique → decide, max 2 rounds, recorded dissent) |
| 12 | CLI trace viewer + `replay` command with single-agent baseline |
| 13 | Messaging status + approvals (Telegram/Discord notifier, CLI fallback); our own small scheduler |
| 14 | English-only UX, YAML config, single-VPS deployment (SQLite + local files). Default config works with local Ollama; paid APIs opt-in |

### 7.2 v2

Separate Team Brain tier + team-of-teams and cross-team contracts; track-record-aware routing (per-member/per-model success, cost, latency stats feed the router; Main Brain can swap underperformers); local embeddings + hybrid retrieval, automated blackboard compaction with quality checks; selective N-model consensus for flagged high-stakes decisions only; web dashboard (live traces, budget burn-down, one-click approvals); team template sharing/import with signature checks; eval suites per template, regression-gated on model/prompt changes; long-term memory promotion pipeline (blackboard → long-term memory, with review); optional multi-process / multi-VPS worker pools; containerised (per-run sandbox) execution backend.

### 7.3 Non-goals (v1, some permanent)

Auto-evolving agents, self-rewriting prompts, agents hiring agents at runtime; visual drag-and-drop team builder; vote-among-N consensus as the default; learned/ML-based routing (static rules + logged outcomes first); agent personalities / social chatter between members; dedicated vector DB service (SQLite full-text search + optional local embeddings is enough); marketplace for agents/teams; voice; multi-tenant SaaS; a second gateway/skills/cron system bought in from another agent framework.

### 7.4 Open decisions for the user (5 max, with recommendation)

| # | Decision | Recommendation |
|---|---|---|
| 1 | **Approvals default for tool-using members** — `smart` vs `approve` (ask every time) vs `off`? | **`smart`.** `off` is rejected (§6.3). `approve` for everything would stall a team on every tool call; `smart` keeps the hardline denylist plus human approval for genuinely risky actions. |
| 2 | **Team Brain in v1** — separate LLM tier from day one, or lead-member role? | **Lead member in v1.** A separate tier adds 2 LLM hops per task for teams of 1–3 members; the lead role delivers the same commit/merge authority with one fewer brain in the loop. Revisit as a separate tier in v2 for large teams. |
| 3 | **Build shape** — from scratch (per user correction) vs layer/fork on an existing agent? | **From scratch, as ordered.** The teardown was learning only. A fork or layer would carry licence/attribution entanglement and upstream merge debt; a small original core is slower to start and cleaner to own, sell, and license. |
| 4 | **Default model for the out-of-the-box config** — local Ollama vs a paid API? | **Ollama local, paid opt-in.** A default that requires a paid key violates "no paid service by default"; local models handle drafting/critique/summarisation, and the router's capability gating prevents a weak local model silently taking a job that needs a strong one. |
| 5 | **Human approval channel in v1** — messaging (Telegram/Discord) via our own notifier, or CLI-only until the notifier is proven? | **Messaging as primary, CLI as fallback.** Approvals need a channel that reaches the user when they are away from the VPS; CLI-only would leave spend/risk approvals with no channel. The admission allowlist (§6 layer 6) must be set and verified explicitly before first use. |

---

## 8. File skeleton — new package (small original core)

Every module below is original code written for Airlangga. No module imports, vendors, or wraps another agent framework.

```
airlangga/
├── README.md                  # vision, quickstart, English-only
├── LICENSE                    # our own licence (§9)
├── airlangga.yaml             # example config (teams, members, brains) — see §4.2
├── pyproject.toml             # package; generic dependencies only (§9.3)
├── airlangga/
│   ├── __init__.py
│   ├── cli.py                 # CLI: run, trace, replay, validate-config
│   ├── config.py              # airlangga.yaml loading + validation (roster schema)
│   ├── team.py                # Team: roster, topology (Main → Teams → Members), lifecycle states
│   ├── brain.py               # Main Brain + Team Brain as configurations of our turn loop,
│   │                          #   with layered prompts (goal / team / member)
│   ├── member.py              # Member runtime: durable record + per-activation session,
│   │                          #   pinned model endpoint + credential scope + toolset scope
│   ├── turn.py                # Our turn loop: assemble → model call → tool dispatch →
│   │                          #   results → stop/retry/recover/overflow handling
│   ├── providers.py           # Provider abstraction: endpoint records, wire-format adapters
│   │                          #   (openai_chat, anthropic_messages, gemini, local),
│   │                          #   credential references (env / token command / vault)
│   ├── contracts.py           # Task Contract schema, validation, idempotency keys
│   ├── ledger.py              # Run Ledger: append-only SQLite (WAL), event types, replay/resume
│   ├── blackboard.py          # Durable shared context: typed versioned entries, full-text
│   │                          #   search, write-time abstracts, commit-only writes
│   ├── context.py             # Context Builder: per-role token budgets, pass-by-reference
│   ├── router.py              # Provider Router: capability tags, static per-role policies,
│   │                          #   capability-gated fallback chains
│   ├── budget.py              # Budget Governor: hard caps (run/team/member/call), pre-flight
│   │                          #   estimate, circuit breaker
│   ├── policy.py              # Policy Engine: per-role tool allowlists, path/network scopes,
│   │                          #   approval-required actions, at the tool-call boundary
│   ├── guardrails.py          # Our 8 safety layers (§6); approvals mode = smart by default
│   ├── artifacts.py           # Artifact Store: per-run workspace, artifact:// refs, hashes
│   ├── debate.py              # Bounded debate: propose → critique → revise → decide,
│   │                          #   max 2 rounds, dissent recording, verifier-first decision
│   ├── memory.py              # Long-term memory (cross-run) + per-member private notes;
│   │                          #   explicit, approved promotion from the blackboard only
│   ├── scheduler.py           # Small job runner (tick loop, file lock); team-targeted jobs
│   ├── notify.py              # Human-in-the-loop notifier (messaging channel + CLI fallback)
│   ├── trace.py               # Trace viewer (CLI) + replay command + single-agent baseline
│   └── templates/
│       ├── research.yaml
│       ├── code-review.yaml
│       └── content.yaml
└── tests/
    ├── test_ledger_replay.py  # crash → resume reconstructs plan/blackboard/budgets
    ├── test_budget_governor.py# caps enforced outside the LLM; circuit breaker fires
    ├── test_router_gating.py  # fallback failing `require` is skipped, never used silently
    ├── test_policy_engine.py  # denied call logged; member cannot self-grant tools
    ├── test_debate_bound.py   # max 2 rounds; dissent recorded; verifier decides first
    └── test_guardrails.py     # hardline denylist un-overridable; secrets redacted;
                               #   file-write denylist holds with approvals off
```

---

## 9. IP / commercialisation — clean-room from scratch

### 9.1 What "from scratch" means, precisely

- **No Hermes code.** No Hermes source file, function, class, or module is copied, adapted, vendored, imported, or wrapped — not the provider system, not the turn loop, not the guardrails, not the state/ledger code, not the delegation code. The Hermes teardown (`teardown-hermes.md`) was a **read-only learning exercise**: it taught the team what concepts exist (provider abstraction, turn loop, ledger, blackboard, budget, policy, guardrail categories) and what the gaps are (no persistent team, no per-member model pinning, no team memory). Concepts are not code; every implementation in §3, §4, §6, and §8 is designed and written originally for Airlangga.
- **No Hermes assets or branding.** No Hermes name, logo, config format, prompt text, skill content, or documentation text is carried over. The product is named **Airlangga**; its config file is `airlangga.yaml` with our own schema (§4.2); its prompts, messages, and documentation are written originally.
- **No licence or attribution entanglement with Hermes.** Because no Hermes code or assets are used, Airlangga does not inherit Hermes' licence terms, does not need to reproduce Hermes' licence or attribution notices, and does not depend on Hermes' release cycle. (If a future contributor proposes importing any third-party agent code, that proposal must be reviewed against this section first — the default answer is no.)
- **Clean-room discipline during implementation.** Implementers work from **this spec** (and from public LLM provider API documentation), not from Hermes source. They do not have Hermes source open while writing Airlangga code. Where a design question arises, the answer is derived from this spec and from first principles, or the question is escalated as an open decision — not resolved by reading the other codebase. This file (`SPEC.md`) is the clean-room boundary document.

### 9.2 Licence and ownership

- Airlangga is released under **our own licence, chosen by the user** (default recommendation: a permissive licence such as MIT or Apache-2.0 for the core, so commercial use is unencumbered; the user picks the final licence before the first public release — see open decision below). The `LICENSE` file at the repo root is ours, not inherited.
- All code, prompts, templates, and documentation in the `airlangga/` package are original works created for this project. Copyright is held by the project owner (the user) unless the user assigns it otherwise.
- Team templates shipped in `airlangga/templates/` are ours; user-created templates belong to their authors.

### 9.3 Dependencies — generic public libraries + LLM provider APIs only

Airlangga depends only on:

| Dependency | Why | Licence class |
|---|---|---|
| Python 3.12+ standard library (`sqlite3`, `hashlib`, `json`, `asyncio`, `http`…) | Ledger, hashing, concurrency, config | PSF (permissive) |
| `httpx` | HTTP client for LLM provider APIs | BSD-3-Clause |
| `pydantic` (v2) | Config / contract / report schema validation | MIT |
| `PyYAML` | `airlangga.yaml` and team templates | MIT |
| `click` (or `argparse` from stdlib) | CLI | BSD-3-Clause |
| `pytest` (dev only) | Test suite in `tests/` | MIT |

- **No agent-framework dependencies.** No Hermes, no LangChain, no AutoGen, no CrewAI, no other multi-agent framework — the team runtime is ours.
- **LLM provider APIs are services, not dependencies.** Anthropic, OpenAI, Google, DeepSeek, OpenRouter, Ollama (local), and any OpenAI-compatible endpoint are called over HTTPS with our own adapters (§4.1); calling an API creates no licence obligation on our code.
- Any additional dependency proposed during implementation must be (a) a generic public library with a permissive licence (MIT / BSD / Apache-2.0 / PSF), (b) justified in the spec or a design note, and (c) approved by the user. Copyleft-licensed libraries (GPL/AGPL) are excluded unless the user explicitly approves one for a named reason.

### 9.4 Commercialisation notes

- Because the core is original, it can be sold, licensed, hosted as a service, or open-sourced under our own terms without seeking permission from any other agent project's authors.
- What is *not* ours and must not be claimed: the LLM providers' models and APIs (used under their terms of service and paid per use), and the generic libraries in §9.3 (used under their permissive licences, with their notices kept where required).
- Before the first public release or first paying customer: (1) user picks the final licence; (2) a dependency audit confirms §9.3 (run a licence check over the lockfile — no copyleft, no agent-framework packages); (3) a short clean-room attestation is recorded (implementers confirm they worked from this spec, not from Hermes source).

### 9.5 Open decision (IP)

| # | Decision | Recommendation |
|---|---|---|
| 1 | **Final licence** — MIT vs Apache-2.0 vs proprietary? | **Apache-2.0** for the core: permissive for commercial use, plus its explicit patent grant, which MIT lacks. Proprietary only if the user plans to sell licences rather than adoption. Decide before the first public release, not before v1 code starts. |

---

## Appendix — sources and how they were used

- `teardown-hermes.md` — Hermes Agent v0.23.2, read-only inspection, 2026-11-20. Used as **learning material only**: it established the *concepts* (provider abstraction, turn loop, ledger, guardrails, delegation limits) and the *gaps* (no persistent team, no per-member model pinning, no team memory, no team-level budget/policy). No code, structure, field list, or text from it is carried into Airlangga's implementation.
- `ag-input.md` — Antigravity/AG design review, `agy` v1.5.13, 2026-11-20. Used as discussion input. Its recommendations were adopted where they survive the from-scratch correction (persistent state not persistent processes; Main Brain vs Team Brain as one runtime in two configurations; Team Brain optional / lead role in v1; must-haves ledger, budget governor, contracts, verifiers, policy engine, capability-tagged router; bounded debate max 2 rounds; v1 6–8 weeks scope and non-goals). Its recommendation to **build as a layer on Hermes was explicitly rejected by the user** and is not part of this spec.
