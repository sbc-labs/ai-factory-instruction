# 07 — Writing plans and checklists for weaker models

The owner's standing requirement: plans and checklists are written by the strongest model but **executed by Sonnet/Haiku-class models**, and later reviewed. A plan that only a strong model can follow has failed. This file is the standard a plan must meet before implementers are spawned; `tools/plan-audit.py` enforces the mechanical part.

## 1. What makes a task executable by a weaker model

| Property | Rule | Why |
| --- | --- | --- |
| **Complete fields** | every task has `Spec:`, `Covers:`, `Depends on:`, `Owns:`, `Do:`, `Tests:`, `Done when:` — exact labels, each on its own line (audit rule 1) | the model never has to infer where to look, what to touch, which requirement it proves, or when to stop |
| **Reading order** | `Spec:` lists the exact sections (and milestone row) to read *before* coding | weaker models skip reading unless told exactly what |
| **Exact values** | copy enum values, column names, port names, error codes, paths, limits, commands from the spec into `Do:` — never "as per spec" alone | paraphrase is where values drift |
| **One decision per task, pre-made** | any judgment call the architect can foresee is decided in the plan and written down; the task says *what*, not *consider* | "pick a sensible approach" produces inconsistent code across tasks |
| **Bounded scope** | ≤ ~400 non-test lines; if larger, split with suffixes (`B4.6a/b`) in the plan, not ad hoc | long tasks lose the thread |
| **Explicit dependencies** | `Depends on:` names task ids; a contract slice or phase is named by its phase id (`P1` slice), which the audit treats as context; nothing implicit | prevents starting on unmerged foundations |
| **Explicit ownership** | `Owns:` lists the files/folders the task creates or edits | prevents edits outside the track |
| **Observable tests** | `Tests:` names what each test asserts, with its kind (`unit:` / `int:` / `e2e:` / `manual:`) | "add tests" yields tautologies |
| **Objective done** | `Done when:` is a command + expected result or a verifiable artefact, never "works" | the reviewer can re-run it |
| **No forward references to unwritten things** | every file, function, schema or endpoint a task uses either exists (earlier task) or is created in this task | otherwise the model invents it |
| **Stop condition** | the kickoff prompt says where to stop (end of phase, or when blocked) | prevents scope creep into the next phase |

## 2. Checklist standard

- One block per task, headed `### <id> — <title>` (same id and title as the track file).
- One box per `Do:` bullet, one per `Tests:` item, one per `Done when:` condition — **generated** from the track file by `tools/checklist-gen.py` so it cannot drift; cross-cutting rules (budget, safety) live as hand-written boxes in the checklist's preamble.
- Because the checklist is derived, a task's `Do:` bullets must each be a single verifiable action (one box = one thing to prove); a bullet that bundles three actions produces one box hiding two of them.
- Boxes describe **evidence**, not intent: "`pnpm test:int` green incl. the 11th-login 429 case", not "auth tested".
- A universal per-PR checklist carries the process boxes so track checklists stay about the task.
- Ticked in the same commit as the work; a reviewer treats ticks as claims.

## 3. The readiness gate (before spawning implementers)

1. `python3 -I ai-workspace/instructions/tools/plan-audit.py ai-workspace/plan` → `RESULT: PASS` (all fields present, checklist coverage 1:1, no dangling ids, no thinking-aloud phrasing).
2. **Cold-start test:** the architect picks three random tasks (one per track) and asks: "Could a model with *no* conversation history, given only the kickoff prompt, start this in five minutes and know when it is done?" If any answer is no, fix the task and recheck.
3. **Terminology pass:** every term in `Do:` appears in the spec (its glossary), the contract or an earlier task; grep for words like "appropriately", "as needed", "etc.", "similar", "handle" — each is a hidden decision; replace it.
4. Record the audit output in the planning commit message.
5. **Fresh-model plan review** (12 §2, 06 T21) — mandatory at autonomy L2/L3.

## 4. Kickoff prompts for weaker models

- Order the reading list; say "read fully"; cap it at ~6 documents plus the cited spec sections.
- Restate the rules that are most often broken: no placeholders, no paid calls, stay inside owned folders, commit every green step, never push when told not to, only your own PIDs and instance.
- Give the **hard-limits block** with the agent's weight class and what that weight allows (`08` §1); weaker models will otherwise start a browser beside another agent's render.
- Tell the model what to produce at the end (commits, counts, a live demo, what other tracks must change, deviations) and the exact stop condition.
- Give the model the branch/worktree it works in, the tip to sync to, and the integration branch it targets.
- Name the rulings and earlier reviews that apply; a weaker model does not go looking for them.
- Say which shared files it must **not** edit (e.g. the contract package) and how to ask for a change instead.
- Templates: `06-templates.md` T5 (implementer), T6 (reviewer), T11 (designer), T12 (gate fixer).

## 5. Signs a plan is still too thin (fix before spawning)

- A task's `Do:` fits in one line.
- `Tests:` says "unit tests" without naming an assertion.
- `Done when:` repeats the title.
- Two tasks could both reasonably create the same file.
- The frontend task says "per the design" without naming the approved design artefact.
- A table from the spec is summarised instead of referenced with "copy verbatim from §x.y".
- An E2E task relies on seed data or another spec's leftovers instead of creating its own data.
- A task needs an expensive resource (renders, browsers, load) but does not say it is heavy, or its tests would run real expensive work outside the serial test project.
- A test task has no "fails without the change" evidence requirement.
- A task depends on a later phase's feature but does not say what the test asserts until then.
- Two tracks could both edit the same shared file (contract package, compose file) in the same phase.

CHANGELOG
- 2026-10-11 created after the readiness audit of the Content Studio plan showed 89/97 tasks missing at least one field.
- 2026-10-18 retro: kickoff rules (hard-limits block with weight class, sync tip, rulings and reviews to read, files not to edit, end-of-batch report contents, T12); more thin-plan signs (seed-dependent E2E, unmarked heavy tasks, no failing-test evidence, later-phase dependencies, shared-file contention).
- 2026-10-18 `Covers:` in the complete-fields rule; glossary in the terminology pass; the fresh plan review as readiness step 5.
- 2026-10-19 review 2: how contract slices are named in Depends on.
