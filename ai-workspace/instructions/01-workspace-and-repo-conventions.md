# 01 — Workspace and repository conventions

## Folder roles (same in every project)

```
<repo>/
├── product-documents/        # OWNER'S documents: the build spec (source of truth), product notes
│   ├── <BUILD_SPEC>.md
│   └── changes/              #   change requests CR-<nnn>.md (11 §1)
├── ai-workspace/             # THE AI'S PLACE TO WORK — plans, reviews, notes, these instructions
│   ├── instructions/         #   universal rules (this folder; copied between projects unchanged)
│   ├── plan/                 #   the engineering plan for THIS project (02-planning-procedure.md)
│   │   ├── checklists/       #   per-task tick lists + gate/review checklists
│   │   └── tools.json        #   optional stack patterns for the tools (tools/tools.example.json)
│   ├── design/               #   (UI projects) design system, screen specs, approvals, tool ledger
│   ├── reviews/              #   plan-review.md, phase reports P<n>-<track>.md, P<n>-qa.md, P<n>-security.md (+ screenshots/, demos/P<n>/)
│   ├── tech-debt.md          #   tech-debt register (10 §6)
│   ├── metrics.md            #   factory metrics per phase (11 §3)
│   ├── in-flight.md          #   who is running what right now (08 §4)
│   ├── notes/                #   scratch investigations, dated, one topic per file
│   └── memory/               #   durable facts not derivable from the repo, one fact per file
├── docs/                     # BUILD LOG (names may be dictated by the spec)
│   ├── PROGRESS.md           #   one line per completed task; gate results
│   ├── BLOCKERS.md           #   anything needing a human or another track; owner hand-over items
│   ├── DECISIONS.md          #   ambiguities resolved, rulings, deviations, spec proposals, versions, ENV
│   └── perf.csv              #   performance measurements per gate (10 §4)
├── START_PROMPT.md           # session hand-off (below)
├── CLAUDE.md                 # conventions for coding agents (content usually dictated by the spec)
├── .gitattributes            # union merge for the append-only logs (below)
└── <code>                    # apps/, packages/, infra/ … per the plan's ownership table
```

Rules:
- `product-documents/` is the owner's. Agents edit the spec **only** as the architect, with the owner's approval (or delegation), as a new version with a changelog line. The spec is never copied elsewhere; other files link to it by path.
- `ai-workspace/` is the agents'. Humans read it; agents write it. Plans are living documents: an agent that finds a plan error fixes the plan file in the same commit as the code and says so.
- `docs/` is the implementers' log. Append-only: never rewrite another agent's lines.
- Never put secrets anywhere in the repo. Keys live in a git-ignored `.env`.
- Remove junk files (`.DS_Store`, editor swap files) in the first infra task and git-ignore them, along with local data dirs, test output, scratch logs.

## Append-only logs

- One entry per line, starting with the task id(s), a ` · ` separator and the date: `B4.2 · 2026-10-12 · …`, `GATE P3 · 2026-10-12 · PASS · …`, `ARCHITECT · …`, `REVIEW · …`, `ENV · …`, `PROCESS · …`. The audit tools parse this format.
- Add to `.gitattributes` when the logs are created (planning Step 0 — the first `ENV` lines are written then):
  ```
  docs/PROGRESS.md merge=union
  docs/DECISIONS.md merge=union
  docs/BLOCKERS.md merge=union
  docs/perf.csv merge=union
  ```
  Every agent appends to these files, so without the union driver nearly every merge conflicts on them. Where a conflict still appears, `tools/log-union-resolve.py` keeps both sides; never resolve a log conflict by dropping a side.

## Spec handling

1. **Read it fully** before anything else, every section, no skimming. The architect confirms by summarising it and listing inconsistencies.
2. **Fix inconsistencies before planning.** Duplicate changelog entries, out-of-order sections, tasks that would be no-ops, undefined tables/env vars/branch names, contradictory rules — all fixed in a new spec version. Decisions with more than one reasonable answer go to the owner as multiple-choice questions (at L2/L3 per 12 §1: the recommended option, recorded as owner-delegated).
3. **The spec wins** over the plan; the plan wins over an agent's memory. If they disagree, fix the lower one. When a screen spec or plan table contradicts the spec's behaviour rules, the spec wins and the screen/plan text is corrected (with a note).
4. **Amendments the plan needs** are listed in the plan's architecture file under "Spec amendments" and applied only after the owner approves (or, at L2/L3, as owner-delegated per 12 §1).

## Branching

| Stage | Branch | Rule |
| --- | --- | --- |
| Planning | the repo's default branch (e.g. `develop`) | Plan and spec commits go straight there, as the owner directs |
| Building | an integration branch the owner names (e.g. `development-1`, `development-2` for the next run) | Phase gates run here; tagged `phase/P<n>` at each gate |
| Agent work | one branch/worktree per agent, from the integration branch | merged into the integration branch by the architect only |
| Follow-ups after a run | a new branch from the integration branch (e.g. `development-3`, `<topic>-retro-1`) | its own PR, reviewed and regression-tested |

- **Architect merges (default) vs per-task PRs.** By default — and always in an autonomous run — the architect reviews each agent's diff against the task block and checklist (03 "Merging") and merges directly into the integration branch; one PR (integration branch → default branch) goes to the owner at the end of the run, with the description in 06 T15. Only when the owner asks for per-task PRs (a human reviewing during the day): the agent's branch reaches the remote (its own push, or the architect pushes it), the architect opens one PR per task with the same review routine in the PR body, and the owner (or the architect, if delegated) merges. Record which mode is in force in the decisions log.
- Never push to `main`/`master` without the owner's explicit instruction; never force-push; never merge your own work as an implementer.

## Commits and pushing

- Commit messages: `<task-id>: <imperative summary>` for tasks; `<task-id> wip: <what works now>` for checkpoints; `spec: …`, `plan: …`, `review(P<n>/<track>): …`, `GATE-P<n>-fix: …`, `state: …` for the other kinds. Include any attribution lines the environment requires.
- **Checkpoint often (crash safety).** Commit at every green step inside a task and at least every ~30 minutes of work. Never leave more than ~30 minutes uncommitted; a crash must cost minutes, not hours.
- **Back up to the remote when allowed.** If agents may push, each pushes its branch to a backup branch `wip/<phase>-<track>` after each commit (never merged, never force-pushed; deleted after merge). If the environment denies agents `git push` (a permission layer may), agents commit locally only and the architect merges finished tasks promptly — including a single finished task mid-batch when another track waits on it — and pushes. Agents never try to work around a denied push; the architect does not push agents' backup branches for them — agent work reaches the remote only through the architect's reviewed merge.
- **Push only after a green check**, chained with `&&` (`check && git push`), never with `;`. A red test pushed "because it was probably flaky" is a process failure.
- **Pushing large changes.** If the remote resets the connection (common with many binary files), push in steps through a temporary branch (`git push origin <commit>:refs/heads/tmp/<name>`, advancing the commit), then push the real branch and delete the temporary one.
- **Resume, don't restart.** After a crash, read the branch's last commit, the progress log and the checklist ticks, verify with the check command, and continue (08 §3).
- If git has no identity configured, use the repository's existing author identity via `git -c user.name=… -c user.email=…` per commit (also for annotated tags) and tell the owner, rather than writing global config.
- The integration branch must always start in the project's offline/mock mode with the project's standard "bring it all up" command.

## Shared-machine isolation (containers and ports)

Several agents and several projects run on the same machine; each may start its own databases, queues and stores. Every project that runs local services must provide, from the first infra task (written here for Docker Compose; apply the same rules — namespaced instances, no fixed ports, own data — to any other runtime):

- **A Compose project name per instance:** `COMPOSE_PROJECT_NAME=<project-slug>-<instance>`. Compose prefixes all containers, networks, volumes and images with it, so instances never share or clobber state. `main` is the owner's checkout; each agent worktree is its own instance named after its track or task.
- **No fixed host ports anywhere:** compose binds `127.0.0.1:${X_PORT:-<default>}:<container-port>`; scripts and tests read ports from the environment.
- **Per-instance data directories** (bind mounts under `data/<instance>/`), created before `up` so the container runtime does not create them as root.
- **One script that derives an instance:** `instance <name>` writes a git-ignored `.env.local` (project name, deterministic port block, data dirs, host URLs); `instance down [--images]` removes only that instance's containers, volumes, data and (optionally) images; `instance ls` lists the project's instances via labels.
- **A mock-forced stack command** (e.g. `stack:mock`): a compose override that forces every paid integration into mock mode with empty keys, used by E2E and load tests, which also refuse to run unless the running stack reports mock mode (05 "Safety and money").
- **Never:** `container_name:` in compose; `docker system prune`, `docker rm`/`volume rm`/`rmi` on resources the agent did not create; assuming default ports are free.

## Session hand-off: `START_PROMPT.md` at the repo root

Sessions end (machine restarts, context limits). Nothing may depend on chat memory. Every project keeps **`START_PROMPT.md`** at the repository root (skeleton: 06 T17) with:
1. a paste-ready first message for a new architect session: reading order (this file's State → instructions → spec → plan → checklists → latest reviews), verification steps (`git`, `plan-audit.py`, `checklist-audit.py`), how to resolve pending owner decisions, how to start/resume the current phase, and the hard rules;
2. a **State** table: branch of record and head commit, phase tags, spec version, phase and what is running (link `ai-workspace/in-flight.md`), machine budget and toolchain line (exact `PATH` export), tools/connectors status, delegations in force;
3. a **Pending owner decisions** list, batched as multiple-choice questions;
4. an "if the repo looks different" section — including the crash-recovery check (08 §3) — so a stale State is detected, not trusted.

The architect updates §2/§3 at every merge and every gate and before ending a session (12 §4), committing `state: <summary>`. Implementer agents do not edit this file.

## Memory

- `ai-workspace/memory/` (or the harness's memory store) holds one fact per file with a one-line description, and an index. Store: owner preferences, standing rules given mid-project, external constraints, machine facts. Do not store what the repo already records; update a fact when it changes instead of adding a second one.
- When the owner states a new standing rule, add it to `ai-workspace/instructions/` (universal) as well as memory (this project).

CHANGELOG
- 2026-10-11 created from the Content Studio planning session.
- 2026-10-12 added shared-machine isolation (Compose project name per instance, no fixed host ports, instance script).
- 2026-10-12 added the START_PROMPT.md session hand-off convention.
- 2026-10-12 checkpoint commits every green step / ≤ 30 min, backup branches, resume-don't-restart.
- 2026-10-18 retro: append-only log format + `.gitattributes` union merge (hundreds of log conflicts in the first run); architect-merge mode for autonomous runs; backup push only when allowed (agents were denied push); push only after green check with `&&`; stepwise pushes for large binary changes; per-instance data dirs; mock-forced stack command; in-flight register; follow-up branches; hand-off includes crash check and delegations.
- 2026-10-18 review: `.gitattributes` created with the logs in planning Step 0 (ENV lines are written before any infra task); architect merges are the default and the per-task-PR mode is spelled out; clarified that agent work reaches the remote only through the architect's merge; isolation rules apply to any local-service runtime, not only Compose.
- 2026-10-18 layout: product-documents/changes/, QA/security reports and demos, tech-debt register, metrics, docs/perf.csv (union merge).
- 2026-10-18 review: tools.json and plan-review.md in the tree; START_PROMPT State at every merge.
- 2026-10-19 review 2: spec-handling steps carry the autonomy qualifier.
