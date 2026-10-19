# 12 — Autonomy levels, plan review, escalation, session hygiene, speed

The owner's goal is a run that starts from a spec and ends at a hand-over without waiting on them. The rest of this folder makes each step safe; this file makes the whole run **self-driving**: it says what may proceed without the owner, what replaces the owner's checks, when a run must stop instead of grinding, and how the architect stays coherent across long sessions. The architect is a strong model (Opus 5.5 or stronger, 00); these rules are written for it, not around it — the architect decides, records the decision, and continues.

## 1. Autonomy levels (declared at kickoff, recorded in START_PROMPT State and the decisions log)

| Level | The owner approves | Everything else | Typical use |
| --- | --- | --- | --- |
| **L1 supervised** | the plan; designs; each gate (click-through) | architect decides and records | first project with a new owner; UI-heavy products |
| **L2 plan-approved** | the plan only | after approval the run proceeds to hand-over; designs approved by the architect; gates verified by the acceptance-QA demo (10 §2) | the default for an overnight run |
| **L3 full** | nothing in advance | spec → plan → fresh plan review (§2) → build → hand-over without stopping | the owner is away; the spec came from `BUILD-SPEC-PROMPT.md` and is complete |

At every level the run **always stops** for: spending money or using the owner's accounts (00); changes to the owner's machine; a spec ambiguity whose options change scope, cost or data retention; a security S1 that needs a product decision; a CR (11 §1) that adds, removes or changes a requirement or its `Accept:` criteria, or that affects cost or data retention (smaller CRs — wording, a limit within the spec's stated range, a missing default — are architect-decided at L2/L3). Everything else is decided by the **recommended option**, written as an `ARCHITECT · owner-delegated (L<n>) ·` line in the decisions log, and listed in the hand-over and in START_PROMPT §3 so the owner can overrule later. A decision the owner overrules becomes a CR.

**What "changes to the owner's machine" means:** anything needing root or sudo, system packages, global configuration of tools the owner uses (git global config, shell profiles, the container daemon or its credential config), credentials and accounts. User-level installs that change nothing else — a version-managed runtime under the home directory, static binaries in `~/.local/bin`, a package manager in the user prefix — are allowed at L2/L3, recorded as `ENV ·` lines and listed in the hand-over.

**What "stop" means** (the owner may be asleep or away): *stop* never idles a live session. The architect writes a T22 report headed `STOPPED`, adds the item to `docs/BLOCKERS.md` and START_PROMPT §3, parks every task that depends on it, and continues all independent work within the budget. When nothing independent remains: run the gate of any phase that is complete, write the T15 hand-over with a `### Stopped on` section, open the PR as a draft, commit `state: stopped on <item>`, and end the session. The owner's answer resumes the run through START_PROMPT.

**Design approval at L2/L3** (UI projects): the owner's design tool is used only when the kickoff's "design connector" slot names the connector and its quota; otherwise designs are in-repo HTML/markdown prototypes with screenshots (the publish step is skipped, the design specs stay). The architect approves each screen against the spec's screen states, `DESIGN.md`, 05 "UI" and the contract DTOs, may take one ledgered screenshot per screen version (the "no-peeking" rule protects the owner's quota, not the architect's judgment), records the approval in `approvals.md` with the version, and says "design finalised" itself at the PD gate. Approvals are listed in the hand-over as owner-delegated.

Owner messages during a run: answer first (00), apply what they said, continue. The owner may change the level at any time; record it.

The kickoff prompt for a level-declared run is in the README ("Kickoff for a fully autonomous project"); for L1 use the separate planning and building prompts.

## 2. Fresh-model plan review (replaces the owner's plan approval at L2/L3; recommended at L1)

The plan is the only thing the whole run depends on, and the architect cannot review its own plan cold. Before any implementer is spawned, a **fresh strong agent** (Opus-class, light) with no history reads the spec and the plan and answers (06 T21):
1. **Coverage:** every requirement id has a task (`trace-audit.py` with an empty directory as the test root; read only "requirements without a task"); every spec screen, endpoint, table, job and control appears in exactly one track's tasks; the contract covers what the screens display.
2. **Cold-start test** on five random tasks (at least one per track): could a Sonnet-class model start each in five minutes and know when it is done? Which words hide a decision?
3. **Order and parallel safety:** dependencies are acyclic; the contract slice each phase needs is frozen before it; no two tracks edit one shared file in a phase; heavy tasks are marked and sequenced within the budget.
4. **Gates:** every gate line is runnable and matches the spec's; the test strategy and the quality plan (02 Step 5) are present and specific.
5. **Risk:** the three places this plan is most likely to fail, with a concrete mitigation each.
Verdict READY / NOT READY with findings; the architect fixes the plan (S1 before building, S2 within the first phase), re-runs the audits, records a `REVIEW · plan ·` line. At L3, READY starts the build; at L2 the owner gets the verdict with the plan. A re-review after S1 fixes that is NOT READY again is an escalation (§3, report with options); a third NOT READY is a stop (§1).

## 3. Escalation ladder (so a run never grinds)

| Signal | First response | Then | Stop (§1) and report when |
| --- | --- | --- | --- |
| an implementer fails a task (red check, cannot finish, drifts) | re-spawn once from its last commit with the diagnosis in the prompt | second failure → a stronger model (Opus-class) with the same prompt and the two failure reports | a third failure; or the diagnosis shows the task or the spec is wrong (then a CR or a plan fix, not another attempt) |
| a review hands back more than ~1/3 of a track's tasks | fix per 04 | split the next batch smaller and raise the implementer model for that track | the same track repeats it in the next phase |
| a gate fails after the gate fixer | second gate-fixer round with the first report | — | a third round would be needed; report root causes and options |
| a phase exceeds **2×** its estimate (measured pace, 02 Step 4) | status report (06 T14) with the cause and options (cut scope to a later phase, add a machine, change models) | continue on the owner's answer or, at L2/L3, the recommended option | 3× the estimate |
| a crash or runaway happens twice in one phase | 08 §3 and the budget rule (08 §1): reduce the budget by one agent | — | it recurs after the reduction |
| the same blocker stays open for two phases | the hand-over lists it with what it blocks | — | it blocks the critical path |
| a watchdog finds an agent silent > 45 min twice | ask, then confirm dead and re-spawn (08 §6) | — | a third silence from the same task |

An escalation report is one message: what happened, the measured numbers, the root cause as far as known, 2–4 options with the recommended one first, what continues meanwhile (06 T22). At L2/L3 the architect takes the recommended option unless the row says "stop"; at L1 it waits.

**Park for a systemic row** (3× estimate, a crash recurring after the budget cut, a track repeating a hand-back ratio, a third silence): finish and merge what is in flight, start no new batch of the affected track (machine instability: continue at 1 agent, 1 heavy), then follow the §1 end state. The 2×/3× rows apply only once one phase has a measured duration (02 Step 4); before that, report at 2× of the plan's estimate and continue.

**Never** respond to a failure by weakening the gate, skipping a test, widening a timeout beyond the measured need, or moving the task silently to "later". Scope cuts are CRs.

## 4. Session hygiene for the architect (context compaction, long runs)

Long sessions are summarised by the harness without warning; after a summary, the architect knows *that* things happened, not the details. Rules:
- **After a compaction, before acting** (a new session follows T17 §1 instead): read `START_PROMPT.md` §2–§3, `ai-workspace/in-flight.md`, the plan's `00-README.md` status table, the current phase's table in `07-phases-and-integration.md`, the latest review and QA reports, and `git log -10`. Never act from the summary alone; the summary is a pointer, the repo is the state.
- **Keep the recovery point fresh:** `in-flight.md` at every spawn and merge (08 §4); START_PROMPT §2 at every merge (one `state:` commit, seconds of work) — not only at gates. A compaction can then cost at most one merge of re-orientation.
- **Keep the architect's context lean:** noisy work (log trawls, broad greps, reading many files to answer one question, long test outputs) goes to a light subagent that returns the conclusion; the architect reads reports and diffs, not raw output. Run long commands in the background and read their summary (08 §5).
- **Write decisions down the moment they are made** (decisions log, plan edits), not at the end of the batch; a compaction between the decision and the write-up loses it.
- **Re-read the cited source every time** (05): after a compaction the architect's memory of the spec is a summary too.
- The reading list after a compaction is the short one above, not the whole instructions folder; the folder's digest (README "The rules that matter most") plus the files relevant to the current step is enough.

## 5. Speed: scale with the machine, serialise only what must be

"Alone" in this folder means *takes the heavy slot* (08 §1, which also gives the number of heavy slots). On a machine whose budget allows several heavy agents, overlap what does not contend:

| Step | Contends on | May overlap with |
| --- | --- | --- |
| implementers (one per track) | the budget | each other, light reviewers |
| track reviews (backend medium, frontend heavy) | the budget | each other (separate instances), the security review |
| security review (medium) | the budget | track reviews, QA |
| acceptance QA (heavy) | the budget | security review; not the gate fixer or re-run |
| gate fixer, architect re-run, expensive tests, load tests | the whole machine | nothing — these measure and must not be disturbed |

Other speed rules: batches of a few hours so merges are small and tracks rarely wait; merge a finished task mid-batch when another track needs it (03); pull-forward within the contract freeze; the design phase runs beside foundation work (02 Step 3); never serialise for safety what a separate instance makes safe (01 isolation). On a small machine (2 agents, 1 heavy) the overlap table collapses to the phase shape in 02 Step 4; do not exceed the budget to go faster — the first project's crashes cost more than they saved.

## 6. Keeping the branch sound

- **Flaky tests are quarantined, never tolerated:** a test that fails intermittently is fixed (deterministic data, waits on state not time, 05) or moved to a quarantine list in `ai-workspace/tech-debt.md` with an id, the failure rate and a deadline (the next phase), and marked skipped **with that id in the skip reason**. A quarantined test blocks the final gate until fixed or removed with a ruling. "Retry until green" is not a fix.
- **A merge that breaks the integration branch is reverted** (`git revert`, a new commit), never force-pushed away; the fix comes back as `<id>r<k>`.
- **Migrations are append-only once merged** (05 "Boundaries"): a wrong migration gets a corrective one.

CHANGELOG
- 2026-10-18 created from the fresh-eyes review of the instructions: autonomy levels L1–L3 with the always-stop list and owner-delegated decision lines; fresh-model plan review replacing owner plan approval at L2/L3; escalation ladder (task retries, hand-back ratio, gate rounds, 2×/3× estimates, crashes, blockers, silences) with the escalation report; architect session hygiene after compaction; overlap table for larger machines; flaky-test quarantine, revert-not-force-push, append-only migrations.
- 2026-10-18 review: "stop" defined for an absent owner (STOPPED report, park, continue, draft PR, end); CR always-stop wording matches 11; design approval at L2/L3; compaction vs new-session reading lists.
- 2026-10-19 review 2: owner's-machine definition; L2 escalates like L3; park for systemic rows and first-phase estimates; plan-review test root and re-review bound.
- 2026-10-19 review 3: the 2× row escalates at L2 like L3; connector slot named.
