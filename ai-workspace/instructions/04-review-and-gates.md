# 04 — Phase-end review and gates

The owner's rule: implementers build; at the end of every phase a **stronger, fresh** model reviews each track's work against the spec and the checklists, fixes what is missing, and only then does the phase gate run. The same applies to any later change (a follow-up branch gets a fresh review and a full regression before its PR).

## The review

| Aspect | Rule |
| --- | --- |
| Who | one reviewer per track that had tasks in the phase; model at least as strong as the implementer (Opus-class) |
| Context | **a new agent with no conversation history** — never a model switch inside the implementer's session. It gets only: the spec, the plan, the track checklist, the phase diff, the previous phase's review (so it does not re-report closed items) |
| Scope | `git diff phase/P<n-1>..HEAD -- <track's owned folders>`; only that track |
| Weight | backend reviewers are usually **medium** (infra containers, no browsers, no expensive tests — the gate runs those); frontend reviewers are **heavy** (one dev server, one browser). Schedule them within the machine budget (08 §1) |
| Method | re-derive from the spec what *should* exist **before** reading the code; verify every `Do` / `Tests` / `Done when` in the diff; re-run the checks and the track's suites itself **in its own instance**; do a **live walk** of the phase's main flow in mock mode (backend: real API + worker against curl; frontend: own screenshots, light/dark, smallest and largest width, compared with the approved designs); treat ticked boxes as claims to verify, and **re-measure** any performance or resource claim (memory, timing, throughput) instead of trusting the report's numbers or rationale |
| Hunt list | spec sentences with never / always / exactly / verbatim / before / immediately; error paths; concurrency (locks, semaphores, idempotency, races between two jobs or a job and a timeout); side effects on safe methods (HEAD, range requests); paid calls in any test path, including harnesses that read a live `.env`; model output that can set prompts, URLs or parameters it was not offered; secrets leaving their provider's host; contract drift (hand-built responses); mock-only behaviour and backend-only behaviour; focus and keyboard on every dialog; placeholders; oversized files |
| Severity | S1 blocks the gate (spec violation, missing task item, absent/failing test, safety, money) · S2 must close before the next phase (contract drift, error path, missing state, parity gap) · S3 quality |
| Fix vs hand back | **Fix directly** when ≤ ~40 lines, unambiguous, inside the track's folders, keeps the check green — commit `review(P<n>/<track>): …` with a test that fails without the fix. **Hand back** anything larger, judgment-laden, cross-track or contract-changing as `<task-id>r<k>` in the track file **and** its checklist, with the options written out when the architect must decide |
| Output | `ai-workspace/reviews/P<n>-<track>.md` (06 T7): scope, commands re-run, verdict GATE-READY / BLOCKED, findings table, checklist audit ("boxes ticked without evidence"), decisions needed, notes |
| Limits | no feature work, no refactors beyond fixes, no edits outside the track's folders (except rulings the architect hands it), no paid calls, never loosen a test or schema |
| Size | if a track's phase diff exceeds ~3,000 changed lines, or a task is still in flight, split the review into parts (part 1 now, part 2 for the late tasks) rather than let one reviewer skim or wait |

**Architect rulings.** The reviewer's "decisions needed" are answered by the architect the same day as one `REVIEW ·` decisions line (accept / reject / option chosen), and the plan, contract and design files are edited to match. A ruling the reviewer can implement in ≤ 40 lines may be handed to the next reviewer or the gate fixer as part of its prompt.

**Re-check (how a verdict changes).** A BLOCKED (track or security), NOT ACCEPTED or NOT READY verdict is never edited away. When the hand-backs are closed, the architect verifies each against its `Done when`, and appends `## Re-check <date> — <model>` to the report with the evidence (commands, counts) and the new verdict. A **fresh re-review agent** scoped to the follow-up diffs is mandatory when an S1 touched money, security or the contract, or when the report had more than two S1s; the plan reviewer (12 §2) is re-spawned on the changed plan files whenever it found S1s. A report's effective verdict is its last Re-check section, or its Verdict section when it has none; only a passing effective verdict satisfies gate step 3.

Implementers close S1/S2 hand-backs before any pull-forward work. "Boxes ticked without evidence" is a process failure, named in the report.

## The gate

Gates run on the integration branch after all reviews read GATE-READY, **with no other agent running**.

1. **Gate fixer** (00 roles, 06 T12): a fresh strong agent, alone, in its own instance. It makes every phase spec run on the real stack: converts tests that only ran against the mock (own data via API helpers, settings restored, real-stack branches for not-yet-built features — 02 Step 5 "test strategy"); a spec that can only run against the mock (it tests mock-only fixtures or providers) stays mock-only with the reason in the decisions log; fixes integration bugs in code with a test that would have caught them, never loosens a real assertion, then proves every step below and reports per-spec times. Changes only tests? Fine. Changes app code? Each fix has its own commit, a progress line and a decisions line (root cause + why).
2. **Architect re-run** on freshly rebuilt images from a clean state (the project's standard up command brings everything healthy), in the architect's own instance (`instance gate`), in this order (02 Step 5 "Gate order"; adapt the names to the project's suites):
   - the check (lint, types, unit);
   - build images **one service at a time**;
   - stack E2E (through the mock-forced stack); grep the service logs for deprecation warnings and errors;
   - **wait until no background work is queued or running** (query the stack's job store) — leftover work from E2E fights the next suite for the CPU;
   - integration suite;
   - contract check;
   - stack down; **expensive tests alone** (infra containers only);
   - mock E2E with retries disabled.
   - **trace-audit** (`tools/trace-audit.py … --milestone M<k>`, k = the highest milestone this phase delivers; the final gate runs without `--milestone`): every requirement in scope has a task and a non-skipped test;
   - **performance**: measure the plan's metrics on the idle machine, append to `docs/perf.csv`, run `tools/perf-compare.py`; over budget blocks unless ruled (10 §4).
   - A phase that delivers no milestone (PD) records `trace-audit: n/a (no milestone)`; a gate before the plan's first measurable metric records `perf: n/a (first metric at P<k>)` — both in the gate line, nowhere silently skipped.
   A failure that passes alone under load is still investigated: either fix the cause (wider timing margins, a missing wait, an isolation gap) as a gate-run fix, or make it deterministic before tagging. Gates are binary. A gate that still fails after a second gate-fixer round is escalated, not retried (12 §3).
3. Review reports present for every active track, GATE-READY; no S1 open; S2 closed or scheduled with an id. Where the plan schedules them: the security report SECURE-FOR-GATE and the acceptance QA report ACCEPTED, with every S1/S2 `Q<n>.<k>` fixed (10 §2–§3).
4. Checklists for the phase fully ticked, including `…r<k>` follow-ups: `tools/checklist-audit.py ai-workspace/plan docs/PROGRESS.md --phase P<n>` prints `RESULT: PASS` (every task of the phase has a progress line; an honestly open box carries a ` — ` note; roll-up lines agree with the log).
5. Owner's click-through of the phase's main flow (minutes, not hours) at autonomy L1; at L2/L3 the acceptance-QA demo recording in `ai-workspace/reviews/demos/P<n>/` stands in for it and the owner reviews asynchronously (12 §1); when the owner is away at L1 and has said to keep going, record it as deferred to the hand-over.
6. Short retro (11 §4): 2–5 `PROCESS ·` lines; metrics row in `ai-workspace/metrics.md` (11 §3).
7. Gate line in `docs/PROGRESS.md` (every count, the trace-audit summary, perf verdict), status flipped in the plan's `00-README.md`, `START_PROMPT.md` State updated, integration branch tagged `phase/P<n>` (annotated, same commit identity), pushed.

## The last phase and the hand-over

- The final gate re-runs **every earlier gate** (full regression), plus whatever the spec's last milestone adds (e.g. a load test, backup/restore), and a check that the owner-run smoke scripts are listed in BLOCKERS.
- Owner-facing docs (README, run and cost instructions) are read against the code at the final gate: every safety or cost statement must match what the guards actually do. A cost warning written before a later guard landed was wrong in the first project.
- The hand-over (06 T15) goes to the owner and into the PR description: what was built, the final gate table, safety fixes found by reviews, owner to-dos (review the README, click through, run paid smokes, open decisions), known notes, where to look.
- **Fresh-clone bring-up:** a fresh agent (light/medium) clones the repository into a new directory and, following only the README, brings the product up in mock mode in a new instance, runs the check and the main flow. Any step the README does not say is S1; the first project's environment surprises (09) would otherwise reach the owner.
- Stop the watchdog and leave no running containers.

## Per-task review (continuous)

Separate from the phase review: the architect reads every agent diff against the task block before merge (03 "Merging"). This catches drift early; the phase review catches what the per-task read misses.

CHANGELOG
- 2026-10-11 created from the Content Studio planning session.
- 2026-10-12 reviewers and gate runs use their own Docker instance.
- 2026-10-18 retro: reviewer weight classes and live walks; previous review as input; expanded hunt list (HEAD side effects, live `.env` in harnesses, model-controlled parameters, secrets to other hosts, focus); fix-with-a-failing-test rule; split reviews when tasks are in flight; same-day architect rulings; the gate fixer as gate step 1; architect re-run order (images one at a time, wait for idle, expensive tests alone); load flakes investigated, not waved through; checklist audit at gates; deferred click-through; last-phase full regression and hand-over.
- 2026-10-18 review: reviewers re-measure performance/resource claims; mock-only-by-design specs recorded instead of forced onto the stack; architect re-run starts from a clean state and adapts the step names; last-phase extras come from the spec; owner-facing docs checked against the guards; fixed the test-strategy reference.
- 2026-10-18 gate adds trace-audit and performance checks, security and QA verdicts where scheduled, demo review as a click-through option, a short retro and metrics row.
- 2026-10-18 click-through per autonomy level; a third gate-fixer round is an escalation.
- 2026-10-18 review: Re-check procedure for verdicts; trace-audit milestone rule; binary checklist-audit; fresh-clone bring-up at the final gate; stack-neutral wording.
- 2026-10-19 review 2: effective-verdict rule; n/a records for trace-audit and perf at early gates; checklist-audit --phase at step 4.
