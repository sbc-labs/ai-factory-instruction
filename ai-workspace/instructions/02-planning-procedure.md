# 02 — Planning procedure (spec → approved plan)

The architect runs this once per project, writing no application code (spec, plan, docs and `START_PROMPT.md` edits only). Each numbered step ends with a commit + push to the planning branch.

## Step 0 — Environment and team size

- Run the inventory in `09-environment-and-tooling.md` §1 (cores, RAM, disk, runtime, package manager, containers, host tools, git identity, remote access, absence of paid keys). Fix what needs no owner; list the rest as owner items with exact commands.
- Derive the agent budget from `08` §1 (total agents, heavy slots); write it into `START_PROMPT.md` State now and into the plan's `00-README.md` when that file exists (Step 5). Every later step plans against this budget: on a small machine tracks cannot all run at once, and the timeline must say so.
- Create now, not at the end: the `docs/` logs (`PROGRESS.md`, `DECISIONS.md`, `BLOCKERS.md`, or the names the spec dictates) with the `.gitattributes` union lines (01 "Append-only logs"); `START_PROMPT.md` (01, skeleton 06 T17); `ai-workspace/in-flight.md` (08 §4); `ai-workspace/tech-debt.md` and `ai-workspace/metrics.md` (empty tables, 10 §6, 11 §3); root `CLAUDE.md` = the spec's agent-conventions block plus the README digest verbatim (harness agents load it automatically); `ai-workspace/plan/tools.json` from `tools/tools.example.json` with only the keys this stack needs.

## Step 1 — Read the whole spec

- Read every line. Do not sample. Summarise it back to the owner in a page: product, core loop, stack, data model size, pipeline, API surface, milestones.
- While reading, keep a list of **inconsistencies**: duplicated or out-of-order changelog entries; sections numbered out of order; tasks that duplicate earlier tasks; tables/env vars/branches referenced but never defined; rules that contradict each other; places where two sections disagree on behaviour.
- Also note the spec's own rules for the agents (mock mode, no spending, commit format, docs to keep) — the plan must inherit them, not restate them differently.

## Step 2 — Fix the spec first

- Present the inconsistency list to the owner. For each item that has exactly one correct fix, fix it. For each item with several reasonable fixes, ask a multiple-choice question (recommended option first). Batch the questions. At autonomy L2/L3 (12 §1) ask only the always-stop items; take the recommended option for the rest and record each as owner-delegated.
- If the spec has no requirement ids, add them in this step (10 §1: `R-<AREA>-<nn> (M<k>) … Accept: …`, one per user-visible behaviour, grouped by area; a glossary section if terms are used inconsistently); the owner approves the batch like any other fix (at L2/L3 per 12 §1). The definition line is the only line that carries `(M<k>)`; mentions elsewhere are references.
- Apply the fixes as a new spec version: bump the version, add a changelog entry that lists the fixes, keep the changelog in strict descending order. A spec with no version or changelog gets both (`v1.0` = the owner's original) in the first fix commit.
- Verify with greps (section numbering monotonic, every cross-reference points at the section whose heading matches, no stale strings). Read the full diff before committing.
- Do **not** restore anything a previous commit deliberately removed; check `git log -p` on the spec before assuming something is missing.

## Step 3 — Decide the split: tracks joined by a contract

The owner's standing structure for any large build:

| Track | Owns (folders) | Produces |
| --- | --- | --- |
| **Infrastructure** | containers, compose/orchestration, root tooling (workspace, lint, test runners, CI), scripts, env templates | a runnable stack in offline/mock mode; the dev/test commands; **per-instance isolation** (compose project name, env-driven ports, `instance` script — `01` shared-machine isolation) delivered in the first infra tasks |
| **Backend** | API server, workers, domain packages (db, queue, engines/providers, pure logic) | the API, the jobs, the data |
| **Frontend** | the web app, E2E specs | the screens, against a mock server first |
| **Contract** (built first by the backend track under the architect's review, then frozen per phase) | a shared types/schema package | the executable API contract both sides compile against |
| **Design** (when the project has a UI) | `ai-workspace/design/**` and the owner's design tool workspace | a design system plus one owner-approved design per screen, produced in a **Design phase (PD) before the build phases**; frontend screen tasks start only after that phase's gate |

Design-track rules:
- **Design is its own phase, before the build phases.** All screens are designed and approved by the owner — or by the architect as delegate at L2/L3 (12 §1) — in a Design phase (PD); frontend screen tasks start only after that phase's gate. Work with no design dependency — infra bootstrap, contract enums/settings, backend data/auth skeletons, frontend scaffold/API client/mock-server skeleton — runs during PD so nobody idles. The API DTOs are finalised at the **end** of PD through a design review pass that lists what each approved screen displays, so the contract does not churn after development starts.
- The designer is a strong model using the design skill(s) the spec names; all design thinking happens in markdown specs in the repo (free); the design tool is the publish step only.
- If the design tool is reached through a rate-limited connector (e.g. a free MCP tier), the plan sets a **per-period budget** with a soft cap (notify the design authority — the owner, or the architect as delegate at L2/L3) and a hard stop (never cross), a ledger that logs every call before it is made, batching rules, and a "no peeking" rule (the design authority looks at the result and replies; at L2/L3 the architect may take one ledgered screenshot per screen version, 12 §1). Exceeding the soft cap defers work to the next period and is reported.
- Approvals are logged (`approvals.md`) with the approved version; the frontend implements that version; later changes are new design tasks with re-approval and matching frontend follow-ups.
- The design track gets its own plan file (`11-design-track.md`) and checklist; the frontend track file carries a dependency table mapping each screen task to its design task.

Rules:
- Separation is by **folder ownership**, written as a table in the plan. A track never edits another track's folders; cross-track needs go through `docs/BLOCKERS.md` and the architect.
- Frontend and backend must be able to progress **without talking to each other**: the contract is executable (schemas), the backend validates responses through it, the frontend parses responses with it and develops against a **mock server generated from it** with scripted state so full flows work offline. Write the mock's behaviour down as part of the contract.
- Infra runs in parallel where its inputs exist (bootstrap first — it is the one sequential bottleneck — then images and test stacks as the apps appear). Where it cannot run in parallel, say so in the timeline rather than inventing busywork.
- Monorepo is fine; the owner wants the code of each track in clearly separate folders. Shared root commands (one compose file, one `check` script) are fine.
- If the spec's layout does not separate infra, propose a minimal amendment (e.g. `infra/`), do not silently restructure.
- **Not a web app?** If the spec's product has no frontend/backend split (a CLI, a library, a data pipeline), keep the method — tracks by folder ownership, joined by an executable contract with a fake of the other side — and name the tracks after the spec's real components; write the mapping into `01-architecture-and-tracks.md` and flag it to the owner at Step 7.
- **One owner for the contract package.** The backend track builds the shared contract package first and owns it from then on; the frontend never edits it. A frontend need becomes a request in its report or BLOCKERS; the backend lands it (additive changes approved by the architect, recorded in the contract doc, mirrored in the mock in the same batch). Two tracks adding the same field independently caused merge conflicts in the first project.
- **Mock parity is a deliverable, not a hope.** Each backend batch report lists every behaviour the mock must mirror (status codes, error payloads, event order, timing-independent outcomes); the architect turns the list into a frontend parity task when the mock differs. Reviewers check parity in both directions. Text and derived values that both the backend and the mock produce (notification copy, progress formulas, error guidance) live as shared functions in the contract package, never re-typed in the mock — a hand-copied string broke a gate in the first project.

## Step 4 — Phases

- For UI projects, a **Design phase PD** precedes the build phases (see Step 3 design rules); it has its own gate (all designs approved, contract finalised, parallel foundation merged, the owner — or the architect as delegate at L2/L3 (12 §1) — says "design finalised").
- One build phase per spec milestone (merge tiny adjacent milestones, e.g. P1 = M1 + M2) so the spec's **gates are reused verbatim**.
- Inside a phase: a table with one row per step and one column per track showing what runs in parallel (‖), what is sequential (→), and the **SYNC** point where tracks must have merged.
- Mark which slice of the contract is **frozen** at each phase.
- Add a **pull-forward rule**: a track with slack pulls its own next phase's first task, never another track's task, never an unfrozen contract.
- Write the critical path per phase so the owner sees where delays would land.
- **Every phase has the same shape**, and the plan budgets time for all of it:
  ```
  build batches (≤ budgeted agents) → per-task diff review + merge → phase reviews (fresh, per track)
    (+ security review when in scope) → follow-ups r<k> → ACCEPTANCE QA (alone; UI/user-facing phases)
    → Q-fixes → hygiene tasks H<n>.<k> → GATE FIXER (alone: real stack, convert mock-only tests, fix integration bugs)
    → architect gate re-run (alone, rebuilt images; trace-audit + perf-compare) → short retro
    → tag phase/P<n> → START_PROMPT state
  ```
  The order shown is for one heavy slot; larger machines overlap steps per 12 §5. The first project needed an integration fix at every gate: tests written against the mock always meet real-stack surprises (seed data, timing, codecs, background work). Plan the gate fixer as a step, not an accident.
- **Order heavy tasks around the budget.** Tasks that need the heavy slot (renders, browsers, load tests) are sequenced, not paralleled; a medium task can run beside a heavy one. Note in the timeline which tasks are heavy.
- **The last phase re-runs every earlier gate** (full regression) and ends with an owner hand-over (06 T15).
- After each closed phase, record its measured duration in the status table; estimates for remaining phases come from these numbers, not from guesses.

## Step 5 — Write the plan files

Standard set in `ai-workspace/plan/` (numbering fixed so prompts can reference them):

| File | Content |
| --- | --- |
| `00-README.md` | index, how tasks are written, phase map, branching, status table, instructions version copied, autonomy level and delegations, machine budget |
| `01-architecture-and-tracks.md` | tracks, ownership table, repo layout, dependency rule, spec amendments, how parallel work is kept safe (contract freeze, mock server, contract test, merge discipline) |
| `02-api-contract.md` | conventions, error catalogue, every DTO, every endpoint (request/response/errors) with a `Frozen: P<n>` tag, events, transition tables, mock-server behaviour contract |
| `03-<contract-package>.md` | exact file layout and tasks for the shared package (built first) |
| `04-infra-track.md`, `05-backend-track.md`, `06-frontend-track.md` | tasks grouped under **one `## Phase P<n> — <title>` heading per phase** — in these files, in `03-<contract-package>.md` and in `11-design-track.md` (`## Phase PD — …`) alike: every file that holds task blocks (hygiene, QA-bug and follow-up tasks of the phase go under the same heading; `checklist-audit.py --phase` selects tasks by these headings and fails on tasks under any other heading); a roll-up tick list under its own `## Tick list` heading at the end (bare tick lines after a task would be read as boxes by the generator) |
| `07-phases-and-integration.md` | the timeline tables, SYNC points, gates, pull-forward rule, integration sequence, risk table |
| `08-coding-agent-playbook.md` | operating manual for implementers (skeleton 06 T23): inputs in priority order, hard rules, task loop, test-command rules, blocked handling, conventions, review hand-off |
| `09-phase-2-….md` | outline only for anything the spec marks as later |
| `10-phase-review-protocol.md` | the end-of-phase review (04-review-and-gates.md, instantiated) |
| `11-design-track.md` | (UI projects) design system + per-screen design tasks, schedule relative to frontend, approval protocol, design-tool budget |
| `checklists/` | `00-universal-task-checklist.md` (06 T3), `<track>-checklist.md` ×3 (+ `design-checklist.md` for UI projects), `phase-gate-checklist.md` (06 T24), `phase-review-checklist.md` (06 T25) |

**The plan must contain a test strategy** (in `01-architecture…` or `08-coding-agent-playbook.md`), because test infrastructure decided late cost the first project the most rework:
- **Test projects and commands:** fast unit (no services), integration (real local services, private queue prefixes so tests never steal jobs from a running stack), contract check, E2E against the mock, E2E against the real stack, and a **separate serial project for expensive real-resource tests** (media renders, real browsers in workers, anything that can exhaust the machine) guarded by a machine-wide lock and an in-code guard so no other test can trigger it (05 "Testing", expensive tests).
- **Offline enforcement:** every test harness builds its config with mock modes and empty keys **after** reading the environment, so a live `.env` can never make tests call paid services; the stack E2E and load-test commands start the mock-forced stack and refuse unless the running app reports mock mode.
- **E2E data independence:** each spec creates the data it needs through API helpers (a shared support module), restores any settings it changes, and never relies on seed contents or on another spec's leftovers; the E2E seed applies fast settings (small counts, short media) so a full flow fits the gate's time limit.
- **Not-yet-built features:** a stack-side assertion for a feature planned in a later phase asserts today's honest behaviour (e.g. "estimate unavailable") with a comment naming the task that will change it, and fails on purpose when that task lands, forcing someone to restore the full assertion.
- **Slow-host settings:** the timeouts for browser-simulating unit tests and stack E2E are sized for the measured machine, and timing-based tests use margins of seconds, not milliseconds.
- **Gate order:** check → build images one at a time → stack E2E → wait until no background work is queued/running → integration → contract → stack down → expensive tests alone → mock E2E → trace-audit → performance measurement + perf-compare (04 "The gate"). Rename the steps to the project's suites and drop the ones it does not have; keep the principles (heavy steps one at a time, idle before the next suite, expensive tests alone).
- **Formatting and lint from the first task:** the `check` command includes the formatter check and the lint rules (dependency rule, banned patterns) from the first infra task; adding them later means a mass reformat across every track (the first project's first review found 83 unformatted files, and the reformat had to wait for its last phase).

**The plan must contain a quality plan** (`10-quality-system.md`; in `07-phases-and-integration.md`):
- **Traceability:** the spec's requirement ids (added in Step 2 if missing) and which milestone each belongs to; every task's `Covers:` line; test titles name the ids they prove.
- **Acceptance QA:** which phases get a QA run, the flows each walks, the demo to record.
- **Security review:** which phases get one (auth, money, files, server-side fetches, AI tools, data export) — always the final gate.
- **Performance budgets:** each metric with its budget, measuring command, environment, number of runs and regression threshold.
- **Visual regression** (UI projects): which screens and states get baselines, at which widths and themes.
- **Hygiene:** one `H<n>.<k>` task per track that has register items (10 §6), written by the architect when QA closes; placeholder rows in the phase table.
- **Pre-push guard:** a local pre-push hook (or the platform's free CI) runs the check and the secret scan so a red build or a key cannot reach the remote even if an agent forgets: `base=$(git rev-parse -q --verify '@{u}' || git merge-base HEAD <integration branch>) && <check command> && python3 -I ai-workspace/instructions/tools/diff-review.py --range "$base...HEAD" --owned '.*' || exit 1` (works on a branch's first push too).
- **Releases** (when the spec has a deploy target): the release phase from `11-change-and-release.md` §2.

**Task format (mandatory, everywhere):**

```
### <Track><Phase>.<n> — <title>
Spec: <sections to read first, incl. the milestone row>
Covers: <requirement ids R-<AREA>-<nn> this task implements, or — >
Depends on: <task ids; a phase or milestone id (`P1` slice, M3) is context, not a task>
Owns: <files/folders this task creates or edits>
Do:   <concrete bullets; copy exact values from the spec, do not paraphrase tables>
Tests: <what must exist and pass>
Done when: <objective check a reviewer can re-run>
```

Task ids are stable once published (`B4.6`); follow-ups get a suffix (`B4.6r1`, `B4.6a`). Track letters are never `M`, `P` or `R` (spec milestones, phases, requirements); `D` is design, `Q` QA bugs, `H` hygiene. Example ids in prose are written in backticks or as `<ID>`: `plan-audit.py` ignores undefined ids inside backticks and flags every other undefined id (and every id in `Depends on:`). Every task cites the spec sections it implements so an implementer reads the source, not the summary.

**Detail level:** written for a weaker model. Exact file paths, exact enum values, exact error codes, exact commands. If the architect would have to make a judgment call while coding, make it now and write it down.

## Step 6 — Checklists

- For every task, expand each `Do:`, `Tests:` and `Done when:` line into a tick-box in `checklists/<track>-checklist.md`, grouped by phase and task. No task without a block; no bullet without a box. **Generate, don't hand-write:** `python3 -I ai-workspace/instructions/tools/checklist-gen.py ai-workspace/plan` derives the body from the track files and keeps each file's preamble for hand-written cross-cutting boxes (budgets, safety). Re-run after every track-file change; `--check` in review.
- A universal per-task checklist (before / while / verify / docs) that every task carries (in the PR body in per-task-PR mode, in the final report otherwise).
- A phase-gate checklist (architect) and a phase-review checklist (reviewer).
- **Cross-check by script**, not by eye: every `### <id>` in the track files must appear in the checklist and vice versa. Commit the check result in the message.

## Step 6a — Readiness gate for weaker models (mandatory before Step 7)

The plan is executed by Sonnet/Haiku-class models. Apply `07-writing-for-implementers.md`:
- `python3 -I ai-workspace/instructions/tools/plan-audit.py ai-workspace/plan` prints `RESULT: PASS` (every task has `Spec / Covers / Depends on / Owns / Do / Tests / Done when`; checklists 1:1; no dangling ids; no thinking-aloud phrasing). Paste the output into the commit message.
- Cold-start test on three random tasks (one per track): could a model with no history start in five minutes and know when it is done? Fix and re-run until yes.
- Terminology pass: grep `Do:` sections for "appropriately", "as needed", "etc.", "similar", "handle" and replace each with a decision; every domain term in `Do:` appears in the spec's glossary, the contract or an earlier task.
- **Fresh-model plan review** (12 §2, 06 T21): mandatory at autonomy L2/L3, recommended at L1. Fix S1 findings before Step 7.

## Step 7 — Publish and get approval

- Commit the plan to the planning branch; push. Give the owner the file list, the decisions made on their behalf (flag each), and the two or three things that need their approval (spec amendments, agent/model mix, start of P0).
- At autonomy L1/L2 (12 §1): do not write code until the owner says so. At L3: the plan reviewer's READY is the approval; send the owner the same summary and continue with `03-execution-procedure.md`.

CHANGELOG
- 2026-10-11 created from the Content Studio planning session.
- 2026-10-11 added the Design track (design-before-implement, owner approval, rate-limited design-tool budget).
- 2026-10-11 design becomes its own phase PD before the build phases; non-UI foundation runs in parallel; DTOs finalised at end of PD.
- 2026-10-11 Step 6a readiness gate (plan-audit.py + cold-start test) added after the first audit found 89/97 tasks incomplete.
- 2026-10-12 infra track must deliver per-instance isolation from its first tasks.
- 2026-10-18 retro: Step 0 (environment inventory, agent budget, START_PROMPT + in-flight register created up front); contract package has one owner; mock parity lists per backend batch; standard phase shape with a planned gate fixer and an architect re-run; heavy tasks sequenced; last phase = full regression + hand-over; measured phase durations drive estimates; mandatory test strategy (projects, offline enforcement, E2E data independence, not-yet-built assertions, slow-host settings, gate order).
- 2026-10-18 review: Step 0 creates the docs/ logs + `.gitattributes` and puts the budget in START_PROMPT until the plan exists; specs without a version get one; the backend builds and owns the contract package from the start; non-web products map the tracks; shared strings between backend and mock; gate order adapts to the project's suites; formatter/lint in `check` from the first task; universal checklist travels in the PR or the report.
- 2026-10-18 quality plan (traceability, QA, security, performance budgets, visual regression, hygiene, pre-push guard, releases); `Covers:` in the task format; phase shape adds security review, acceptance QA, hygiene, trace/perf checks and a short retro.
- 2026-10-18 Step 2 adds requirement ids and a glossary when the spec lacks them; Step 6a adds the fresh-model plan review; Step 7 follows the autonomy level.
- 2026-10-18 review: Step 0 creates CLAUDE.md (conventions + digest), tech-debt, metrics, tools.json; L2/L3 qualifiers; PD gate delegate; phase-shape overlap note; 00-README rows; `## Tick list` heading; playbook/gate-checklist templates; hygiene per track; reserved track letters and example ids.
- 2026-10-19 review 2: hygiene ids `H<n>.<k>`; design approval by the delegate; pre-push hook command; Depends on context ids.
- 2026-10-19 review 3: one `## Phase P<n>` heading per phase (the --phase gate check depends on it); T25 pointer; hook command without an upstream.
- 2026-10-19 verification: phase headings in every task file (contract, design); soft cap notifies the design authority.
