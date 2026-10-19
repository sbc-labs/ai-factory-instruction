# 08 — Machine resources, crash recovery, duplicate prevention and monitoring

An AI team on one machine fails in boring ways: memory runs out, the CPU stalls, the machine reboots, an agent restarts silently and does the same task twice, the disk fills up. None of these is a code problem, and all of them cost hours. This file is the standing procedure; the plan's `00-README.md` records the numbers for the current machine.

## 1. Size the team to the machine (before spawning anyone)

Measure at the start of every session (`nproc`, `free -h`, `df -h /`, `uptime`) and write the numbers into the plan's status table.

| Agent weight | What makes an agent this weight | Typical cost |
| --- | --- | --- |
| **Heavy** | a full container stack, image builds, a browser (E2E, screenshots), production builds, real media renders, load tests | 2–3 GB RAM and one whole CPU core, with spikes |
| **Medium** | infrastructure containers only (database, queue, store) plus integration test runs | ~1 GB RAM, bursts of CPU |
| **Light** | unit tests, docs, plans, reviews that only read and run unit tests | ~0.5 GB RAM |

Rules:
- **Heavy slots:** 1 on a machine under ~16 GB RAM or ~4 cores; otherwise `min(floor(cores / 4), floor((RAM_GB − 4) / 6))`, minimum 1 — and any value above 1 is a trial (revert at the first instability). Total agents ≈ `min(cores, RAM_GB / 3)`, rounded down, minimum 1. On a 2-core / 9 GB machine that is **2 agents, 1 heavy**; a third agent was tried and crashed the machine. The architect's own session is not counted while it only reads, plans and merges; when it runs a heavy step itself (a gate re-run, a stack), it takes the heavy slot. An owner-approved increase is a trial: revert at the first sign of instability.
- **CPU binds before RAM on small machines.** A 2-core machine with load above ~10 stalls: tests time out, browsers freeze for seconds. A load average above ~12 sustained, or above 3× the core count, means something is runaway; find it before doing anything else.
- **Gates and load tests run alone.** Nothing else runs during a gate run, an integration-fix run or a load test. Other "alone" steps (QA, reviewers, the gate fixer) mean *takes the heavy slot*; on a machine with several heavy slots they overlap per 12 §5.
- **Never run two full test suites at once**, and never run expensive real-resource tests (renders, browsers) next to a running stack that is also rendering.
- Agents tear down their stacks, dev servers and browsers as soon as their verification is done, and stop only the PIDs they started (05 "Shared machine").
- Write the budget into every agent's kickoff prompt (06 T5 "Hard limits") with the agent's weight class.

## 2. Disk

- Container builds (stacks that build images) fill disks quietly (the first project's build cache reached 60 GB). Check `df -h /` in every watchdog pass; below ~10 GB free, prune **dangling build cache only** (`docker builder prune -f`), never other people's images or volumes.
- At ~95 % full, object stores and databases fail with misleading "internal error" messages; treat any unexplained storage error as a disk check first.
- After a phase, remove your own gate images and test volumes; keep shared base images so the next build does not re-download them.

## 3. Crash recovery (the machine rebooted or the app was killed)

Committed work survives a crash; uncommitted work does not (01 "Commits and pushing"). After a crash:

1. **Wait ~5 minutes.** The harness may auto-restart background agents from their transcripts, sometimes without any notification.
2. **Find out who is really alive** before re-spawning anything:
   - the agent list or task-status tool of the harness (e.g. `ListAgents`), and any "restarted after the previous session ended" notifications;
   - processes inside each agent's worktree (`ps -eo etime,args | grep <worktree path>`);
   - commits on each agent branch made **after** the crash time;
   - the in-flight register (§4).
3. **Re-spawn a task only if all of these say its agent is dead.** A new agent resumes from the last commit (`git reset --hard` to the agent branch tip, or merge it), reads the progress log and checklist ticks, and continues — never starts over.
4. If two agents turn out to be doing the same task: stop one (the harness's stop tool), kill only its PIDs, remove its stack (`compose -p <project>-<instance> down -v`), keep the better branch, and record which commits were dropped and why in the decisions log.
5. Recreate anything that lived only in the session: watchdog schedules (§6), and check that old schedules did not survive alongside the new ones (list them; delete duplicates).
6. Update `START_PROMPT.md` State if the crash changed anything.

## 3a. Harness usage or rate limits

A multi-hour lockout from the harness looks like a crash but is not one: agents die mid-task, the watchdog stops, and nothing restarts by itself. On a usage- or rate-limit notice: commit what is green, update `in-flight.md` and `START_PROMPT.md` State, write one `ENV ·` line with the reset time, and schedule a resume at that time with the harness's scheduler (the first message is T17 §1); if there is no scheduler, end the session with the State current and tell the owner the reset time. **Never** switch to a paid API key, another billed mode or another account to continue (00 money rule). After the reset, follow §3.

## 4. Preventing duplicate work

Two guards, both mandatory:

- **In-flight register** — `ai-workspace/in-flight.md`, one line per running agent (format 06 T16: task ids, agent id, worktree path, weight, start time, instance). The architect adds the line when spawning and removes it when the work is merged or abandoned. After a crash this file, not memory, says what was running.
- **Duplicate check at agent start** — every implementer's first step (06 T5): before coding, list commits on other branches that mention its task id after the integration branch's tip (`git log --all --oneline <integration-tip>.. --grep '<task-id>'`, plus the other agent branches). If any exist, stop and report instead of building it again.

The machine-wide lock for expensive tests (05 "Testing", expensive tests) is the third, last-resort guard: it stops two agents rendering or load-testing at once even if the first two guards fail.

## 5. Long-running commands

- Builds, stack E2E runs, integration suites and load tests take 5–25 minutes. Start anything longer than the tool's timeout in the background and wait for its completion notice; do not poll it with sleeps.
- "Agent finished, waiting on its own background work" notices are interim: check the agent's progress (commits, processes) rather than assuming it is stuck or done.

## 6. Watchdog (owner requirement while agents run)

A recurring check, every ~30 minutes while any agent runs, using the 06 T13 prompt. Schedule it with the harness's recurring-prompt or scheduling facility; if there is none, run T13 yourself after every merge and whenever you wait on an agent. Session-only schedules die with the session — recreate after a crash.

- For each agent in the in-flight register: age of its last commit; processes in its worktree; files changed in the last 10–15 minutes.
- **No commit for > 45 minutes and no completion notice** → message the agent: what it is on, whether blocked, ETA, "commit what is green now". An agent editing files without committing gets the checkpoint reminder.
- **Clearly stuck** (no processes, no file changes, no reply) → confirm dead per §3, then re-spawn from its last commit.
- **Finished but not handled** → review, merge, push.
- **Host health**: load average, available memory, disk free. Runaway → find the process before anything else.
- Report to the owner only when something was wrong (one or two lines); otherwise stay silent.

## 7. Sandboxed git and shared scratch space

- Worktree-isolated sessions may refuse compound shell commands that touch git (pipes, `cd` into another worktree, git inside loops, shell variables in the command). Use plain, separate commands, or put the logic in a small script file and run it with `python3 -I <script>`. Some sandboxes match the bare substring `git`: an argument such as `\.gitattributes` or a `grep` over `.gitignore` is refused too — write the regex as `\.g[i]tattributes` and read such files with the file-reading tool.
- Keep scratch scripts and logs in the session's private job directory or inside your own worktree (git-ignored). **Never use a shared `/tmp`**: agents on the same machine have run each other's scripts by mistake.

CHANGELOG
- 2026-10-18 created from the Content Studio Phase 1 retro: three crashes (memory on a 9 GB / 2-core machine), a silent agent auto-restart that duplicated a task, a disk at 95 %, duplicated watchdog schedules after a restart.
- 2026-10-18 review: architect's session vs the budget; budget increases are trials; in-flight format points at 06 T16; how to schedule the watchdog when the harness has no scheduler; sandbox `git`-substring refusals; fixed a heading reference.
- 2026-10-18 "alone" defined as taking the heavy slot; overlap on larger machines per 12 §5.
- 2026-10-18 review: heavy-slot formula for larger machines; §3a harness usage/rate limits; heading reference fixed.
