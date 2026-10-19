# Build-spec authoring prompt (universal)

**What this is.** A paste-ready prompt for the chat where you have been discussing a new product idea (features, tech, constraints). It turns that discussion into a complete **build spec**: the single document an AI architect reads, together with this instructions folder, to plan and build the project autonomously. It is project-agnostic: it works for a web app, an API, a CLI, a mobile app, a data pipeline or a library.

**How to use it.**
1. Copy everything inside the block below into the chat that holds the product discussion.
2. Answer its questions. It asks in batches and recommends an option each time, so you can reply quickly.
3. When it delivers the spec, save it as `product-documents/BUILD_SPEC.md` in the new repository, copy `ai-workspace/instructions/` next to it, and paste the README's planning kickoff (autonomy L1) or its fully autonomous kickoff (L2/L3) into a new session.

```
You are a senior product engineer and technical writer. Using everything we have discussed
in this chat about the product, write its BUILD SPEC: one Markdown document that an
autonomous AI coding team (a strong architect model planning for Sonnet-class implementers)
will build the whole product from, unattended, starting from an empty repository. The team
follows separate standing instructions for process (planning, tracks, reviews, gates); the
spec supplies everything about WHAT to build and the decisions behind it. Anything the spec
leaves vague becomes a guess, a contradiction, or a question that blocks the build.

=== HOW TO WORK ===
1. First, inventory what we have already decided in this chat against the REQUIRED CONTENT
   list below. Show me a short table: area | decided | missing or vague.
2. Interview me for the gaps. Ask in batches of at most 8 questions, grouped by area. Each
   question has 2–4 options, the recommended one first marked "(Recommended)", with one
   line on the consequence of each. Never invent a product decision silently; if I say
   "you decide", choose, and list it under "Decisions made on the owner's behalf".
3. Repeat until every REQUIRED CONTENT item is settled or explicitly marked out of scope.
4. Then write the spec in the REQUIRED STRUCTURE, run the SELF-CHECK, fix what it finds,
   and give me the final document in one block (or in clearly numbered parts if too long),
   followed by: the self-check results, decisions made on my behalf, and open questions
   (should be none).
5. Verify third-party facts (API endpoints, auth, model ids, rate limits, pricing, package
   names, licences, current stable versions) against current official sources if you can
   browse; cite them in the Sources section with the date checked. If you cannot verify,
   say so per item and mark it "verify at implementation time".

=== REQUIRED CONTENT (ask until each is settled) ===
Product
- One-paragraph purpose; who uses it (single user? teams? public?); the core loop step by
  step; what "done" looks like for a user; explicit non-goals.
- Primary flows, end to end, including the unhappy paths (failures, cancellation, retry,
  undo, partial results).
- Lifecycle/state machines for every important object: every state, every transition, who
  or what triggers it, and what is forbidden. Interactions between controls (e.g. what
  happens to in-flight work when the user pauses, cancels, rejects, or edits an input).
- Requirements with ids: every user-visible behaviour becomes a numbered requirement
  `R-<AREA>-<nn> (M<k>) — <requirement>. Accept: <observable acceptance criteria>`
  (AREA short and stable, e.g. AUTH, BILLING, UI; M<k> = the milestone that delivers it;
  acceptance = a status code, a visible state, a file produced — never "works well").
  The build team traces every id to a task and a test, so nothing may be left un-numbered.
  Format rules the tools depend on: each requirement is exactly one line that STARTS with
  its id (a list bullet or table row), the milestone in parentheses right after it; no other
  line in the spec starts with an id — cross-references put the id mid-sentence.
- A glossary: every domain term with one definition, used identically everywhere (the
  build team's weaker models drift on terminology; the glossary is what they are checked
  against).
- Edge semantics that are easy to leave open: when a batch/run counts as complete; what
  counts as a duplicate; what is retried and how often; idempotency; time zones and
  schedules; limits (sizes, counts, rates); empty states.
Users, access, security
- Accounts and auth (sign-up open or closed? invite? single owner?), sessions, roles,
  ownership and isolation of data between users; password/credential rules.
- Secrets handling (where keys live), what must never be logged, data retention, backups
  and restore, privacy constraints.
Architecture and stack
- Runtime(s) and languages, frameworks, database, queue/background jobs, storage, search,
  real-time updates, external services. Version policy: name the minimum versions and say
  "use the latest stable at build time, pin exact versions, record them".
- Deployment target and how it runs locally (e.g. containers, one command to start).
  Target machine for development (CPU cores, RAM, disk) — the build team sizes itself to it.
- Repository layout with clearly separated areas for infrastructure, backend, frontend
  (or the product's real components), and a shared contract/types package.
- Configuration: every environment variable with name, purpose, default, and which modes
  need it; an offline "mock" mode as the default for development and tests.
Data
- Every table/entity with every field (name, type, nullability, default, constraints),
  relations, indexes, and which milestone first needs it (prefer creating the full schema
  early). Migrations approach; seed/demo data and a demo account.
- Shared schemas for every boundary payload (requests, responses, events, job payloads,
  stored JSON, AI outputs), with exact enum values.
Integrations (for EACH third-party API, model or service)
- What it is used for; auth; exact endpoints/SDK calls; request and response shapes;
  model ids; rate limits and concurrency; polling/webhooks; idempotency; error mapping
  (which errors are retryable vs fatal); timeouts; pricing and how cost is computed.
- A mock/fake implementation that behaves realistically (async, failures, busy states) so
  the whole product works offline with zero cost.
- How live use is first exercised: smoke scripts the OWNER runs, with expected cost.
AI features (if any)
- Every prompt/agent: purpose, inputs, exact output schema, prompt text or prompt-building
  rules, examples, how outputs are validated and repaired, cost/usage tracking, and which
  parameters the model is allowed to change (allow-list).
- Per prompt, a golden set: 10–30 representative inputs with the expected properties of the
  output (schema validity, required decisions, forbidden content, limits), plus a few inputs
  that try to change the instructions — the build team runs these in the mock engine.
Money and limits
- Every paid action; a budget/cap model if spending is possible; a ledger of every paid
  call (including calls that fail after billing); dry-run or preview options; warnings.
User interface (if any)
- Every screen/route with its purpose, data shown, actions, and all states (loading,
  empty, error, success); navigation; responsive minimum width; light/dark; accessibility
  target; design system direction or the design skill/tool to use; whether designs must be
  approved before building.
API surface
- Every endpoint (method, path, request, response, errors with stable codes), real-time
  event types and payloads, pagination, auth requirements, and the error catalogue.
Heavy or special resources
- Anything CPU/RAM-heavy or slow (media rendering, ML inference, large builds, browsers),
  with how it is limited (concurrency, memory caps) and how it is tested without
  exhausting the dev machine; native tools required on the host or in images; licences of
  key libraries (some need a commercial licence).
Quality, testing, operations
- Testing rules: unit, integration (real local services), end-to-end (against a mock and
  against the real stack), contract tests, coverage targets; FAST test settings for
  end-to-end runs (small counts, short media) so a full flow fits a few minutes; tests must
  never call paid services even if keys are present.
- Logging and error classification; observability; health checks; backups and restore;
  load expectations and a load test target; data volumes and growth (records per table,
  file sizes) and concurrent users — these size the budgets and the test data.
- Performance budgets with numbers (they become gate checks): p95 latency of key
  endpoints, page weight / load time, background job duration, memory per process,
  throughput under the load-test shape, cost per unit of work.
- Security expectations: threat model in a few lines (who might attack, what is valuable),
  authorization rule per resource, data-protection or compliance needs.
- Engineering conventions for the coding agents: root scripts (check, test, dev, e2e),
  commit message format, the agent conventions file content, documentation to keep
  (progress, blockers, decisions logs), branch names (integration and default branch).
Delivery
- Milestones in build order, each with numbered tasks and a GATE: objective, runnable
  checks (commands and expected results) that must pass before the next milestone.
- What is phase 1 versus later phases. Scope control: if phase 1 needs more than ~8
  milestones, propose what moves to phase 2 before writing them out.
- A walking skeleton early: the earliest milestone that produces the product's core output
  end to end in mock mode (the thinnest slice through every layer) is M2 or M3 at the latest;
  integration surprises are found there, not at the end.
- Deployment and releases, if it runs anywhere but the owner's machine: environments
  (staging, production), hosting, domain, secrets store, versioning, migration and rollback
  expectations, monitoring and alerts; otherwise state "local only" explicitly.
- Decisions that are easy to forget (answer each, even if "not needed"): internationalisation
  and locales; analytics/telemetry and consent; email or notifications delivery; generated
  API documentation (e.g. OpenAPI from the schemas); CI (free tier or local pre-push hook);
  accessibility level; supported browsers/devices/OS versions; data import/export; admin tools.
- Owner-only actions (keys, paid smoke tests, accounts, licences) and decisions still open.

=== REQUIRED STRUCTURE ===
# <Product> — Build Specification
Header: audience line (autonomous AI coding team), "read this whole file first",
spec version 1.0 + date, and a CHANGELOG kept in strictly descending order.
## 0. How to use this document (rules for the coding agents)
   build milestone by milestone, gates are binary; check after every task; never spend money
   (mock mode; owner runs live smoke scripts); keep progress/blockers/decisions logs; never
   change a spec decision (propose in the decisions log); verify third-party details against
   current docs; no placeholders; small files; simplest option for ambiguities; version
   policy; repository conventions (product-documents/ holds this spec — do not copy it;
   ai-workspace/ is the AI's working area; docs/ holds the logs).
# PART A — REFERENCE
## 1. Product overview (purpose, users, core loop, non-goals)
## 1a. Requirements (every R-<AREA>-<nn> (M<k>) with Accept: criteria, grouped by area)
## 1b. Glossary (every domain term, one definition each)
## 2. Decisions already made (a table: decision | choice | reason) — incl. owner-delegated ones
## 3. Architecture (services, data flow, repository layout with separate infra/backend/
   frontend/shared areas)
## 4. Configuration (full .env.example with every variable; config loading and validation;
   modes)
## 5. Data model (every table and field; migrations; seed and demo data)
## 6. Shared schemas (enums, settings, payloads, AI output schemas — exact values)
## 7. Domain model and workflows (state machines, transition tables, orchestration, jobs,
   retries, idempotency, controls and how they interact, notifications, real-time events)
## 8. AI agents and prompts (if any)
## 9. Integrations (one subsection per external service, plus its mock)
## 10. Heavy/special subsystems (if any: rendering, inference, files)
## 11. API (endpoints table, error catalogue, events)
## 12. Frontend (design direction/skills, routes and screens with states, data layer)
## 13. Engineering conventions (root scripts, agent conventions file, testing rules incl.
    fast E2E settings and offline enforcement, security basics, logging, performance
    budgets with measuring commands, deployment and releases or "local only")
## 14. Later phases (outline only)
## 15. Sources (every doc cited, with the date checked)
# PART B — BUILD PLAN
Milestones M0 … Mn. Each milestone: a table of tasks (id like M3.2 | work | covers R-ids | done when) and a
"Gate Mn" line listing runnable checks. M0 = foundation (repo, tooling, containers in mock
mode, one-command start, test runners, CI optional). Last phase-1 milestone = hardening:
backups, load test, README (setup, modes, first live run with a costs warning,
troubleshooting).

=== SELF-CHECK (run before delivering; fix every failure) ===
Consistency
[ ] Section numbers are monotonic; every cross-reference (§x.y) points at the section whose
    heading matches its content.
[ ] The changelog is strictly descending with no duplicate versions.
[ ] Every environment variable used anywhere is defined in §4 with a default; every table/
    field used anywhere is defined in §5; every enum value used is defined in §6.
[ ] No two sections disagree on behaviour (search for every control — pause, cancel,
    reject, retry, edit — and confirm one consistent rule for in-flight work).
[ ] No milestone task duplicates or undoes an earlier one; a later milestone that "adds"
    schema says whether the schema already exists from an earlier milestone.
[ ] Branch names, script names, file paths and service names are identical everywhere.
[ ] Numbers that must agree do agree (limits, sizes, timeouts, layout dimensions vs the
    sizes of the things laid out).
Completeness
[ ] Every REQUIRED CONTENT item is answered or explicitly out of scope.
[ ] Every user-visible behaviour has a requirement id with a milestone and observable
    Accept: criteria; every milestone's work lists the ids it delivers; no id is defined twice.
[ ] Every requirement is one line starting with its id and `(M<k>)`; no other line starts
    with an id.
[ ] Performance budgets have numbers and a way to measure them.
[ ] Every domain term used in the spec is in the glossary with one meaning; no two terms
    name the same thing.
[ ] The core output is produced end to end (mock mode) by M3 at the latest; phase 1 has
    ≤ ~8 milestones or the overflow is explicitly moved to phase 2.
[ ] Every state machine lists all states and all allowed transitions; "what counts as
    complete" is defined for every batch-like object.
[ ] Every external service has auth, endpoints, errors (retryable vs fatal), limits,
    pricing, a realistic mock, and an owner-run smoke script.
[ ] Every paid action is covered by the cost/budget model and the ledger.
[ ] Tests can run fully offline at zero cost; fast E2E settings are specified; a test-mode
    environment variable exists if E2E needs behaviour changes (e.g. rate limits off).
[ ] Heavy subsystems have concurrency/memory limits and a way to test them safely.
[ ] Every screen lists its states; minimum width, themes and accessibility are stated.
[ ] Every gate is runnable: commands and expected results, not "works well".
[ ] Licences of key libraries are checked; anything needing a commercial licence is flagged
    for the owner.
[ ] Owner-only actions and open decisions are listed (open decisions should be zero).
Executability by AI agents
[ ] Exact values are written out (enums, codes, paths, limits), never "as appropriate",
    "etc.", "handle errors", "similar to".
[ ] Each task names what it builds and how it is checked; nothing depends on an
    unwritten file, function, or endpoint.
[ ] The repository layout separates infrastructure, backend, frontend and the shared
    contract so parallel teams never edit the same folders.

Start now with step 1 (the inventory table) and your first batch of questions.
```

## Why each part is there (lessons from the first AI-built project)

The first project's spec was strong and still needed two corrective versions plus amendments before building, and several questions during the build. Each item below cost time and is now part of the prompt:

| Gap found | Where it is covered now |
| --- | --- |
| Out-of-order sections and changelog entries, cross-references pointing at the wrong section | Self-check: numbering, cross-references, changelog order |
| An environment variable used by the test setup but never defined | Self-check: every variable defined; test-mode variable for E2E |
| A later milestone re-creating schema an earlier one had to build anyway | Required content: full schema early; self-check on duplicate tasks |
| Two controls (pause and revisions) with contradictory rules for in-flight work | Required content: interactions between controls; self-check search per control |
| An unnamed integration branch | Required content: branch names; self-check identical names |
| Layout numbers that did not fit the size of the things laid out | Self-check: numbers that must agree |
| "When is a run complete?" and "should sign-up close after the first user?" left open until late | Required content: edge semantics and access policy |
| Full-flow E2E too slow until fast test settings were added | Required content and self-check: fast E2E settings |
| Test harnesses that could have spent money once real keys were present | Required content: tests never call paid services even with keys present |
| A heavy subsystem (rendering) exhausting a small dev machine | Required content: heavy resources, limits, safe testing; target machine size |
| A library needing a commercial licence noticed only at hand-over | Required content and self-check: licences |
| Infrastructure files mixed into app folders | Required structure: separate infra / backend / frontend / shared areas |
| Paid calls that failed after billing not counted in the budget | Required content: ledger of every paid call incl. failed-after-billing |
| Model output able to change parameters it should not | Required content: allow-list of model-changeable parameters |

CHANGELOG
- 2026-10-18 created from the Phase 1 retro: a universal prompt for writing a build spec in another chat, with an interview loop, a required structure, and a self-check built from the first project's spec corrections.
- 2026-10-18 quality system: requirement ids with acceptance criteria (section 1a, traced to tasks and tests), performance budgets, security expectations, deployment/releases, and the easy-to-forget decisions (i18n, analytics, notifications, API docs, CI, devices).
- 2026-10-18 fresh-eyes review: glossary section, data volumes and concurrent users, walking-skeleton rule, phase-1 scope control; matching self-check lines.
- 2026-10-18 review: kickoff choice by autonomy level; golden set per prompt.
- 2026-10-19 review 2: requirement-line format rules the tools depend on; matching self-check line.
