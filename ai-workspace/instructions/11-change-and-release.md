# 11 — Change requests, releases and deployment, factory metrics, retros

A product keeps changing after the first plan. Without a defined path, mid-build spec changes arrive as chat messages, land half-way, and leave the plan, contract, designs and tests disagreeing. And anything that is deployed needs a release discipline the local-only build never exercised. This file covers both, plus how the factory measures and improves itself.

## 1. Change requests (CR)

**Any change to product behaviour after the plan is approved** goes through a change request — whether the owner asks in chat or an agent finds the spec wrong. Clarifications that change no behaviour (typos, wording, a missing default that the code already uses) are a spec patch version without a CR.

1. **Capture:** the architect writes `product-documents/changes/CR-<nnn>.md` (06 T20) from the owner's words: what, why, priority, and the owner's exact request quoted. Agents never edit the spec directly for a behaviour change.
2. **Impact analysis** (architect, appended to the CR): affected requirements (R-ids added, changed, removed); spec sections; contract endpoints, DTOs, events and the mock; data model and migrations; designs needing re-approval; tasks already done that must change (become `<id>r<k>`), tasks pending that change, new tasks; tests to change first; effect on the current phase's gate; estimate in phase-days from measured pace; risks; a recommendation (do now / next phase / later).
3. **Decision:** the owner approves, defers or rejects (one multiple-choice question, recommendation first). At autonomy L2/L3 (12 §1) the architect decides CRs that add, remove or change no requirement or `Accept:` criterion and affect neither cost nor data retention (wording, a limit within the spec's stated range, a missing default), recording them as owner-delegated; every other CR goes to the owner (and stops the run per 12 §1).
4. **Apply** (only after approval, in this order): spec new version with a changelog line citing the CR; requirement ids updated; contract and mock in one contract change; designs re-approved if screens change; plan tasks reopened or added with `Covers:` the affected R-ids; checklists regenerated; `plan-audit.py` and `trace-audit.py` pass. The CR file gets a final "Applied in spec v<x>, tasks <ids>" line.
5. **Timing:** an approved CR lands in the next batch, not in the middle of a running agent's task; a safety or money S1 may interrupt. A CR never silently weakens a gate.

## 2. Releases and deployment (when the spec has a deploy target)

The plan adds a **release phase template** for any product that runs anywhere but the owner's machine:

- **Environments:** local (mock), staging (production-like, test data), production. Configuration per environment from the environment, never from code; secrets from the platform's secret store, never from the repo; the mock mode is impossible in production (startup refuses).
- **Versioning:** semantic versions; a user-facing `CHANGELOG.md` per release written from the progress and decisions logs (what changed for users, not task ids); images and artifacts tagged with the version and the commit.
- **Database migrations:** forward-only and **backward compatible for one release** (expand → migrate data → contract in a later release), so the previous app version still runs against the new schema during a rollout or rollback. Every release rehearses the upgrade on a copy of the previous release's database snapshot. A backup is taken immediately before migrating production.
- **Release checklist** (per release): the gate for the release passed; trace-audit and perf-compare clean; security review done for the release scope; changelog written; migration rehearsed; rollback tested on staging (previous image tag + restore point); staging smoke run (the owner runs any paid smoke); monitoring and alerts in place for the new paths; the owner approves the release.
- **Rollout and watch:** deploy to staging, smoke, then production; watch error rates and key metrics for an agreed period; feature flags for risky features so they can be turned off without a redeploy.
- **Rollback:** a documented, tested command path (previous version + database restore point if a migration cannot be reversed) that the owner can run.
- **Hotfixes:** branch from the release tag; a CR-lite (problem, fix, risk); review by a fresh reviewer; the regression subset for the affected area; release as a patch version; merge back into the integration branch.
- **Operations hand-over:** a runbook (how to start, stop, back up, restore, rotate keys, read logs, common alerts and what to do).

## 3. Factory metrics (so the owner can tune cost and quality)

Recorded per phase in `ai-workspace/metrics.md` (one row per closed phase; template: 06 T9 "Metrics row"):

| Metric | Source |
| --- | --- |
| wall-clock duration, from phase start to tag | progress log |
| agents run, per role and model | in-flight register history |
| tokens or cost per agent, when the harness reports usage | agent completion notices |
| review findings per track, by severity (S1/S2/S3), and fixed-by-reviewer vs handed back | review reports |
| QA bugs by severity; security findings by severity | QA / security reports |
| gate-fix commits (integration problems the mock hid) | gate-fixer report |
| crashes, restarts, duplicate agents | decisions log `ENV` / `PROCESS` lines |
| requirements covered / tested; perf metrics over budget | trace-audit, perf-compare |

Use them: many S1/S2 findings for one implementer model → stronger model or smaller tasks for that track; many gate fixes → more real-stack testing earlier; long phases → smaller batches or a bigger machine. Report the trend at each gate (00 "Communication rules", status reports).

## 4. Retros

- **After every gate — a short retro** (the architect, ~10 minutes): what slowed us down, what broke, what a rule would have prevented. Write 2–5 `PROCESS ·` lines in the decisions log. Apply project-level fixes to the plan immediately. If the owner states a new standing rule, add it to these instructions immediately (README "Keeping this folder universal").
- **After every project or run — the full retro:** compare the decisions log's `PROCESS`, `ENV`, `GATE` and `REVIEW` lines, the metrics and the crash history with these instructions, and update them in a reviewed PR (a fresh reviewer cold-reads the folder before merge).

CHANGELOG
- 2026-10-18 created from the Phase 1 retro discussion: change-request process with impact analysis, release/deployment template (environments, expand-contract migrations, rehearsal, rollback, hotfixes, runbook), factory metrics, per-gate and per-project retros.
- 2026-10-18 CR decisions per autonomy level.
- 2026-10-18 review: CR delegation wording matches 12 §1; metrics row template; reference fixed.
