# 03 — Execution procedure (running the phases)

## Set-up (once, after plan approval)

1. Apply the approved (or owner-delegated, 12 §1) spec amendments as a new spec version; commit.
2. Create the integration branch the owner names from the **tip of the planning branch** (the commit that holds the approved plan — the README prompts say the same); push; the architect's session works on it (in its own worktree when sessions are isolated).
3. Set the plan's `00-README.md` status table to the first phase "in progress", with the models and the machine budget (08 §1).
4. Start the watchdog (08 §6) and record the merge mode (01 "Branching": per-task PRs or architect merges) and the autonomy level (12 §1) in the decisions log and START_PROMPT State.

## Per phase

```
spawn implementers within the budget ─▶ each commits per green step ─▶ architect reviews each diff, merges, pushes
  ─▶ phase reviews (04) + security review when in scope (10 §3) ─▶ follow-ups closed
  ─▶ acceptance QA (10 §2) ─▶ Q-fixes ─▶ hygiene tasks H<n>.<k> (10 §6)
  ─▶ gate fixer (heavy slot) ─▶ architect gate re-run (whole machine; trace-audit, perf-compare)
  ─▶ short retro + metrics row (11) ─▶ tag ─▶ next phase        (overlaps on larger machines: 12 §5)
```

### Spawning implementers

- **Within the machine budget** (08 §1): at most the budgeted number of agents, at most one heavy. Prefer pairing one heavy agent (e.g. frontend with a browser) with one medium (e.g. backend with infra containers only). Register every agent in `ai-workspace/in-flight.md` before it starts.
- **One agent per track per batch**, each in its own git worktree/branch. Never more agents than tracks with work; no swarm. A batch is a run of consecutive tasks of one track (e.g. B4.1–B4.6); keep batches to a few hours so reviews stay small.
- **Each agent is its own container instance** (`01` "Shared-machine isolation"): it runs `instance <name>` before any container command and `instance down` when finished.
- Models per `00-operating-model.md`.
- The kickoff prompt follows `06-templates.md` T5 exactly: the **hard-limits block** (weight class, budget, instance, PIDs only, checkpoint rule, push rule, paid-API rule), setup (sync to the integration tip, install, `PATH` line, commit identity and trailers), the reading list, the ordered task list with the stop point, and the final report contents. Weaker models follow what is written, so write it all.
- **Duplicate guard:** the first step of every implementer is the check in 08 §4 (does any branch already hold commits for my task ids?).
- Implementers report per batch (commits, counts, deviations, what other tracks must change). A report that says "contract ready" or "X landed" is the architect's cue to merge it promptly so a waiting track can continue.

### Merging (the architect, every time)

1. Read the agent's report; run `tools/diff-review.py` on its branch (ownership, banned patterns, oversized files, binaries); read the diff against each task's `Do` / `Tests` / `Done when`. (Per-task-PR mode, 01 "Branching": the same steps, with the review written into the PR and the merge done by whoever the mode names.)
2. Merge with `--no-ff` (or `--ff-only` when the branch is a straight continuation). Log conflicts resolve with the union driver or `tools/log-union-resolve.py`; anything else is resolved by reading both sides.
3. Record rulings for everything the report asked (deviations accepted or not, contract changes approved, hand-backs created with ids, follow-ups folded into later tasks) as one `ARCHITECT ·` or `REVIEW ·` line in the decisions log, and edit the plan/contract/checklists accordingly (regenerate checklists; `plan-audit.py` must PASS).
4. Run the check; push only if green (`check && git push`). After a merge that touches the contract package or lands work from two tracks, also run the mock E2E subset for the affected flows on the integration tip, so contract/mock drift is found at the merge, not at the gate.
5. Update `in-flight.md`; tell any waiting agent what landed (one short message: what, where, what to do next).
6. Merge a single finished task **mid-batch** when another track is blocked on it; do not wait for the batch to end.

### Parallel-safety rules (enforced, not advisory)

- **Contract freeze:** endpoints tagged `Frozen: P<n>` change only via a contract change approved by the architect that updates the schema package, the contract document and the mock in one go. Additive changes are allowed any time but still go through the contract owner (02 Step 3).
- **Ownership:** a diff touching folders outside its track is questioned; the only accepted exceptions are named in the task, a ruling, or a minimal stopgap the report calls out (e.g. a one-line mock fill so the other track still compiles).
- **Mock-server parity:** every endpoint the frontend uses has a mock handler that behaves like the backend (02 Step 3). Behaviour that exists only in the mock is a bug.
- **Contract test:** an automated check that every route serialises through a shared schema; part of `check`.
- **Pull-forward:** a track with no remaining tasks pulls its own next-phase first task, provided its contract slice is frozen and the budget allows. Nothing else.
- **Integration branch always runnable** in mock mode via the project's standard up command.

### When an implementer is blocked or idle

Per the playbook: ambiguity → simplest spec-consistent choice + decisions entry; missing contract field → request to the contract owner; cross-track need → BLOCKERS; third-party drift → follow current docs + decisions entry; nothing to do → stop and report. Never skip a failing test, loosen a schema, or comment out a check. A tool or permission denial is reported, never worked around.

### Design agent (UI projects)

- Spawned first, at the start of the Design phase PD, alongside design-independent foundation work (within the budget); strong model; owns `ai-workspace/design/**` and the design tool; never edits app code; the **only** agent allowed to call the design tool's connector.
- PD closes with a design review pass (what each approved screen displays → contract findings), the contract DTOs finalised, and the owner's (or delegate's) "design finalised"; only then do frontend screen tasks start.
- Works screen by screen: markdown spec → planned, batched publish → approval request → stop; revisions only after feedback, batched.
- Keeps the connector budget ledger (connector mode); stops at the soft cap and tells the design authority; never crosses the hard stop.
- Implementation deviations from approved designs are proposed by the frontend in `approvals.md`, accepted or rejected by the design authority with a dated line; the frontend reviewer checks screens against the approved design plus accepted deviations.

## Rate-limited external tools (general rule)

Any connector with a quota (free MCP tiers, API trial limits) gets, in the plan: the limit, a soft cap (~70 %) that triggers an owner notification, a hard stop (~90 %) that is never crossed, a ledger file logging every call **before** it is made with a running per-period total, batching rules, and a no-peeking rule. Agents never discover a quota by hitting it.

## Money and external services

- All development, tests and gates run in the project's offline/mock mode. No paid API is called by any agent, ever, including "just to check".
- Live adapters are built from the provider's current official docs and tested against fakes (local fake servers bound to localhost, injected fetch); record doc URLs and dates.
- Scripts that exercise live services are written, type-checked, refuse to run without an explicit flag (e.g. `--yes`), print the expected cost, and are **left for the owner to run**, listed in BLOCKERS with exact commands.
- CI that costs minutes is proposed to the owner, not enabled by default.

## Reporting to the owner

- At every gate: tasks shipped, review verdicts, gate results table, open BLOCKERS, what the next phase starts with, and an updated estimate (00 "Communication rules", status reports).
- Between gates: when blocked on the owner, when a decision would change scope, when the watchdog found something wrong, or when asked.
- Status lives in the plan's `00-README.md` status table, `docs/PROGRESS.md` and `START_PROMPT.md`; the owner should be able to see progress without asking.
- At the end of a run: the hand-over (06 T15) and the PR into the default branch.

CHANGELOG
- 2026-10-11 created from the Content Studio planning session.
- 2026-10-11 added the design agent and the rate-limited external tools rule.
- 2026-10-11 design agent starts in phase PD (design first); PD closes with contract finalisation.
- 2026-10-12 each agent runs as its own Docker instance (namespaced containers, volumes, ports).
- 2026-10-12 size agent concurrency to the machine RAM (two crashes from memory exhaustion on a 9 GB machine).
- 2026-10-18 retro: budget and recovery moved to 08 and referenced; batches, in-flight register, duplicate guard, kickoff hard-limits block; the architect's merge routine (diff-review tool, union logs, rulings line, green-check push, mid-batch merges to unblock tracks, relaying "landed" messages); ownership exceptions; design-deviation acceptance; live adapters against fakes; smoke scripts need an explicit flag and print costs; end-of-run hand-over.
- 2026-10-18 review: merge routine notes how it applies in per-task-PR mode.
- 2026-10-18 per-phase diagram matches 02 Step 4 (security, QA, hygiene, retro); set-up records the autonomy level.
- 2026-10-18 review: integration branch from the planning tip; mock E2E subset after contract or cross-track merges; heading reference fixed.
- 2026-10-19 review 2: hygiene ids `H<n>.<k>`; owner-delegated amendments.
- 2026-10-19 review 3: designer reports to the design authority.
