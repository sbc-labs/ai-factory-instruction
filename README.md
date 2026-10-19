# ai-factory-instruction

The **canonical copy** of the universal instructions an AI team follows to plan, build, review and hand over a product from a build spec. Projects copy the folder from here; improvements flow back here as reviewed pull requests, and the version is bumped (see `ai-workspace/instructions/README.md`, "Keeping this folder universal").

Current version: see the first line of `ai-workspace/instructions/README.md`.

## Start a new project

1. Write the build spec. If you only have a product discussion so far, paste `ai-workspace/instructions/BUILD-SPEC-PROMPT.md` into that chat; it interviews you and writes the spec.
2. In the new repository (default branch created and pushed), copy this repository's `ai-workspace/instructions/` folder **whole and unchanged, at the same path**:
   ```bash
   git clone --depth 1 git@github.com:sbc-labs/ai-factory-instruction.git /tmp/ai-factory-instruction
   mkdir -p ai-workspace && cp -r /tmp/ai-factory-instruction/ai-workspace/instructions ai-workspace/instructions
   rm -rf /tmp/ai-factory-instruction
   ```
3. Put the spec at `product-documents/BUILD_SPEC.md`. Commit and push both.
4. Decide the autonomy level (`ai-workspace/instructions/12-autonomy-and-escalation.md` §1): L1 (you approve plan, designs and gates), L2 (you approve the plan once; recommended for a first run), L3 (spec to hand-over without stopping).
5. Open a session with the strongest available model (Opus 5.5 or stronger) in the repository root and paste **one** kickoff prompt from `ai-workspace/instructions/README.md`: "Kickoff prompt for a new project" (L1) or "Kickoff for a fully autonomous project" (L2/L3), with the `<…>` placeholders filled in.
6. Answer its batched questions. At L1/L2 reply "Plan approved" when it shows the plan; at L3 it continues on its own.
7. To resume in a later session, paste §1 of the project's `START_PROMPT.md`, not the kickoff.

## What is in here

| Path | Content |
| --- | --- |
| `ai-workspace/instructions/README.md` | the index, the 20-rule digest, the tools table and the kickoff prompts |
| `ai-workspace/instructions/BUILD-SPEC-PROMPT.md` | the prompt that turns a product discussion into a complete build spec |
| `ai-workspace/instructions/00-…12-….md` | the standing rules: roles, repo conventions, planning, execution, reviews and gates, quality rules, templates, writing for weaker models, resources and recovery, environment, quality system, change and release, autonomy and escalation |
| `ai-workspace/instructions/tools/` | the audit tools (plan, checklists, traceability, performance, diff review, log merge) with a self-test |

## Improving it

Every project holds a short retro after each gate and a full one at the end. A change to a rule is made here, in a pull request that a fresh model cold-reads before merge, with the version line in `ai-workspace/instructions/README.md` bumped and a `CHANGELOG` line in each edited file. After editing any tool: `python3 -I ai-workspace/instructions/tools/selftest.py` must print `SELFTEST: PASS`.

Origin: extracted from the first AI-built project (Content Studio, sbc-labs) after its Phase 1 retro and four fresh-review rounds (v1.3–v1.7, 2026-10-18/19).
