# 00 — Operating model: roles, models, decision rights

## Roles

| Role | Who | Responsibilities |
| --- | --- | --- |
| **Owner** | the human | Writes/approves the build spec; approves the plan and spec amendments; decides anything the spec leaves open; runs anything that costs money (live smoke tests); does a short manual check at phase gates (or delegates it); merges or delegates merging |
| **Architect** | the strongest available model (Opus-class or better; never below the owner's stated minimum) | Reads the spec in full; fixes spec inconsistencies (with owner decisions); writes the plan, the contract, the checklists; spawns and coordinates all other agents; reviews every diff before merging; makes rulings; runs gates; keeps the plan, the logs and `START_PROMPT.md` current; reports to the owner |
| **Implementers** | Sonnet-class models | One agent per track per batch; execute tasks in order from the track file; commit each green step; tick checklists; report; never merge, never change decisions |
| **Reviewers** | a strong model in a **fresh context** (Opus-class) | One per track at the end of each phase (or per part, 04); audit the phase diff against spec + plan + checklists; fix small gaps; hand back large ones; verdict GATE-READY / BLOCKED |
| **Gate fixer** | a strong model in a fresh context (Opus-class), running **alone** | At each gate: makes the full test suite pass on the real stack — converts tests that only ran against mocks, fixes integration bugs with tests, never loosens an assertion — then proves every gate step (04 "The gate") |
| **Acceptance QA** | a strong model in a fresh context (Opus-class), heavy, running **alone** | Each phase with user-visible work, before the gate fixer: uses the product as a user would (scripted acceptance per requirement id + exploratory charters), records demo recordings for the owner, files bugs; never fixes product code (10 §2) |
| **Security reviewer** | a strong model in a fresh context (Opus-class) | Phases touching auth, money, files, server-side fetches, AI tools or data export, and the final gate: authorization matrix, injection, secrets, dependency audit; fixes small issues with a failing test first, hands back larger ones (10 §3) |
| **Plan reviewer** | a strong model in a fresh context (Opus-class), light | Before any implementer is spawned: cold-reads spec + plan, runs the audits, cold-starts five tasks, verdict READY / NOT READY (12 §2, 06 T21); replaces the owner's plan approval at autonomy L2/L3 |
| **Designer** (projects with a UI) | a strong model using the project's design skill(s) and the owner's design tool | Produces the design system and one design per screen **before** the frontend builds it; publishes to the design tool; requests approval; keeps the tool-call budget ledger; never edits app code |

Design is approved by the **owner** (or the architect when the owner delegates it); frontend reviewers check implemented screens against the approved design.

The architect does not implement tasks itself except plan/spec/doc edits and small fixes (≤ a few lines, with a test) found during its own gate run or merge check. Keeping the planner out of the code keeps its review honest.

## Model assignment rules

- **Architect:** the strongest model available — **Opus 5.5 or stronger** is the expected default; the owner's stated minimum is a floor. It plans for *weaker* models, so the plan must be concrete (file paths, spec refs, tests, done-when), not a list of intentions.
- **Implementers:** Sonnet-class for all build tasks. Haiku-class only for purely mechanical edits with no judgment and a cheap redo — in practice a failed cheap task costs more than it saves on a constrained machine, so default to Sonnet.
- **Reviewers and gate fixers:** always at least as strong as the implementer and **never the same conversation**. A model switch inside the implementer's session is not a review; spawn a new agent with no history.
- Record the models used per phase in the plan's status table so the owner can correlate quality with cost.

## Decision rights

| Decision | Who decides |
| --- | --- |
| Product behaviour, features, scope | Owner, via the spec. Agents never change a spec decision; they propose in `docs/DECISIONS.md` |
| Spec inconsistencies that have one correct resolution | Architect fixes, records in the spec changelog |
| Spec inconsistencies with more than one reasonable resolution | Owner picks from options the architect presents (multiple choice, recommended option first); at L2/L3 the architect takes the recommended option and records it as owner-delegated unless it is on the always-stop list (12 §1) |
| Repo layout, package boundaries, task split, phase order, review rulings, hand-back priority | Architect, recorded in the plan or the decisions log; owner can veto |
| Ambiguity inside a task not settled by spec or plan | Implementer picks the simplest option consistent with the spec, records it in `docs/DECISIONS.md`, continues |
| Third-party API drift from the spec | Implementer follows current official docs, records the difference |
| Merge to the integration branch | Architect (or owner); implementers never merge |
| Spending money (paid APIs, live services, CI minutes, paid tool tiers) | Owner only, explicitly, every time |
| Changes to the owner's own machine or accounts (tool config, credentials, global settings) | Owner; the architect asks first, backs up, changes the minimum, records it |
| Everything else during a run | Depends on the **autonomy level** declared at kickoff (12 §1): at L2/L3 the architect takes the recommended option, records it as owner-delegated, and continues; the always-stop list still stops the run |

**Delegation.** The autonomy level (12 §1) is the standing delegation; the owner may additionally delegate a decision class to the architect (e.g. "you approve the designs", "you decide"). Record each delegation in the decisions log with the owner's words and date; decisions taken under it are marked "owner-delegated" so the owner can review or override them later. Delegation never covers spending money or acting on the owner's accounts.

## Communication rules

- Agents narrate briefly (one line before acting, one line after) and state results in their own words; tool output alone is not a report.
- "Done" is only said with evidence (the command run and its result).
- Blocked is normal and is written down in `docs/BLOCKERS.md`; hiding it is not acceptable.
- Questions to the owner are batched, multiple-choice where possible, recommended default first (06 T10).
- **Status reports** (when asked, at every gate, and at hand-over) use one table: phases (passed / in progress / remaining), checklist completion per track **computed from the checklists** (never estimated), what is running now, what is next, what waits on the owner, and an ETA derived from the measured pace of the completed phases (06 T14). Percentages are honest: report items done and effort remaining separately when they differ.
- When the owner sends a message while work runs, answer it first, in the first sentence, then continue.

CHANGELOG
- 2026-10-11 created from the Content Studio planning session.
- 2026-10-11 added the Designer role (design-before-implement, owner approves).
- 2026-10-18 retro: added the Gate fixer role; implementers default to Sonnet-class (Haiku rarely paid off); architect minimum = owner's stated minimum; delegation rules; owner-machine changes need consent; status-report and percentage rules.
- 2026-10-18 roles: acceptance QA and security reviewer (10 §2–§3).
- 2026-10-18 Opus 5.5 named as the expected architect; autonomy level as the standing delegation (12 §1).
- 2026-10-18 review: plan reviewer role; spec-fix decisions per autonomy level.
