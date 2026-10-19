# 10 — Quality system: traceability, acceptance QA, security, performance, visual regression, tech debt

Code review and tests prove the code does what the tasks say. They do not prove that every requirement was built, that the product feels right to a user, that it is secure, or that it stays fast. Good teams still ship bad products through those four gaps. This file closes them. It is planned in `02` Step 5 (quality plan), run at the gates in `04`, and uses the templates in `06` (T18–T19) and the tools `trace-audit.py` and `perf-compare.py`.

## 1. Requirement traceability (spec → task → test → gate)

**Goal:** no requirement is forgotten, and every requirement has a test that proves it.

- **In the spec:** every user-visible requirement has an id and a milestone: `- **R-<AREA>-<nn>** (M<k>) — <requirement>. Accept: <observable acceptance criteria>.` Areas are short and stable (`AUTH`, `RUN`, `PAY`, `UI`…). Acceptance criteria are observable outcomes (a status code, a visible state, a file produced), never "works well". The build-spec prompt (`BUILD-SPEC-PROMPT.md`) writes specs this way. If a spec arrives without ids, the architect adds them in the spec-fix step (02 Step 2) as part of the new spec version, with the owner's approval (at L2/L3 per 12 §1). **The definition line is the only line that carries `(M<k>)`**; the changelog, cross-references and milestone tables mention ids without it, and `trace-audit.py` reads only definition lines.
- **In the plan:** every task has a `Covers:` line listing the R-ids it implements, or `Covers: —` for work that implements no user-visible requirement (tooling, refactors, infrastructure). A requirement may be covered by several tasks (backend + frontend).
- **In the tests:** a test that proves a requirement names its id in the test title: `it('R-AUTH-02: locks the account after 10 failed logins', …)`. End-to-end specs name the requirements of the flow they walk. One requirement may be proven by several tests; every requirement needs at least one.
- **At every gate:** `tools/trace-audit.py <spec> ai-workspace/plan <test roots> --milestone M<k>` must report no requirement in scope without a task, none without a test, and no task without `Covers:`. Its summary line goes into the gate line in `docs/PROGRESS.md`. Ids used but not defined (typos, removed requirements) are fixed, not ignored.
- **Reviewers** check that tests named after a requirement really assert its acceptance criteria (a test titled `R-AUTH-02` that never logs in eleven times is a finding).

## 2. Acceptance QA agent (a user, not a code reviewer)

**Goal:** catch what works but feels broken — confusing states, dead ends, unclear copy, flows that need a reload, edge cases nobody scripted.

- **Who and when:** a fresh agent (Opus-class for judgment), **heavy** (it drives a browser or the product's real interface), running **alone**, at every phase with user-visible work: after the phase reviews' follow-ups are merged and **before** the gate fixer, against the running product in mock mode. Non-UI products: it uses the CLI or API exactly as a user or client would.
- **Inputs (not the code):** the spec's user-facing sections and the phase's requirements with their acceptance criteria; the approved designs and accepted deviations; the previous QA report.
- **Method:**
  1. **Scripted acceptance:** walk every in-scope requirement's acceptance criteria through the product; record pass/fail per R-id.
  2. **Exploratory charters**, time-boxed (~10 minutes each): empty and very long input; double-click and double submit; back, refresh and deep links; two tabs at once; slow or failing network (mock-mode failure triggers); permission boundaries (another user's data); interrupting long work (cancel, pause, navigate away); error recovery (does the user know what to do next?); copy (is every message clear, consistent, free of internal jargon?).
  3. **Cross-cutting pass:** keyboard only; smallest supported width; the other theme; screen-reader names on key controls.
- **Output:** `ai-workspace/reviews/P<n>-qa.md` (06 T18): verdict (ACCEPTED / NOT ACCEPTED), an acceptance table (R-id → pass/fail/evidence), a bug table (id `Q<n>.<k>`, severity S1/S2/S3, steps to reproduce, expected, actual, screenshot path), and UX notes. **Demo artifacts** in `ai-workspace/reviews/demos/P<n>/`: a short recording (GIF/video) of the phase's main flow plus screenshots of key states, so the owner can review asynchronously instead of doing a live click-through.
- **Bugs become tasks:** S1/S2 bugs are added to the owning track file as tasks `Q<n>.<k>` (full task format, `Covers:` the failing R-id) and fixed before the gate fixer runs; S3 go to the tech-debt register (§6) or a later phase. The QA agent does not fix product code. The verdict changes only through the re-check in 04 "The review" (Re-check).

## 3. Security review

**Goal:** security is reviewed on purpose, not discovered by luck inside general reviews.

- **When:** a fresh Opus-class security reviewer (medium weight: code reading, dependency audit, live probing in mock mode) runs in every phase that touches authentication or authorization, money or spending, file upload/download, server-side fetching of URLs, webhooks, AI agents or tool use, data export or deletion — and always at the final gate. The plan's quality section marks which phases get one (02 Step 5).
- **Checklist (adapt to the stack; ASVS-style):**
  - **Authentication:** password hashing parameters; session creation, rotation and expiry; cookie flags (`HttpOnly`, `Secure`, `SameSite`); brute-force limits; sign-up policy as specified; no user enumeration in error messages.
  - **Authorization:** an endpoint matrix — every route, who may call it, and a test that another user gets the specified denial (often 404 rather than 403, to avoid leaking existence); background jobs re-check ownership.
  - **Input and injection:** schema validation at every boundary; parameterised queries only; no shell or command interpolation of user input; path traversal on any file path built from input; template/HTML injection where user content is rendered.
  - **Server-side fetches:** any URL from a user or a provider is checked against an allow-list of origins before it is fetched or before a key is attached (SSRF and credential leaks).
  - **Files:** type and size limits, content sniffing, storage paths not derived from user input, downloads with correct `Content-Type` and `Content-Disposition`, no side effects on `HEAD` or range requests.
  - **Secrets:** environment only; never logged, never in the client bundle, never in error messages, never sent to another host; test harnesses force empty keys.
  - **Web:** CORS policy; CSRF protection for cookie-authenticated mutations; security headers; rate limits on expensive or abusable endpoints.
  - **Money and AI:** spend caps enforced server-side; every paid call ledgered; model-controllable parameters allow-listed; prompt-injection exposure from user content considered (what can user text make an agent do?); tool permissions minimal.
  - **Dependencies:** run the ecosystem's audit (`npm audit`, `pnpm audit`, `pip-audit`…); high/critical findings are S1 unless shown unreachable and recorded; licences of new dependencies checked.
  - **Data:** personal data in logs, retention as specified, backups as sensitive as the database, error responses without stack traces.
- **Output:** `ai-workspace/reviews/P<n>-security.md` (06 T19): verdict SECURE-FOR-GATE / BLOCKED, the endpoint authorization matrix, findings with severity, the audit output summary. Small fixes (≤ ~40 lines, with a failing test first) are made directly; larger ones are handed back as `<task-id>r<k>`. Any S1 blocks the gate; the verdict changes only through the re-check in 04 "The review" (Re-check).

## 4. Performance and resource budgets

**Goal:** performance is a gate with numbers, not a surprise found under load.

- **In the spec:** budgets with numbers for what matters to the product: e.g. p95 latency of key endpoints, initial page weight / largest contentful paint, background job duration, memory per process against its container limit, throughput under the load-test shape, cost per unit of work. The build-spec prompt asks for them.
- **In the plan:** a performance section listing each metric, the exact command that measures it, the environment (mock mode, which machine), how many runs (median of 3), and the regression threshold (default 10 %).
- **At every gate** (architect re-run, machine otherwise idle): measure, append one row per metric to `docs/perf.csv` (format in `tools/perf-compare.py`), then run `tools/perf-compare.py docs/perf.csv`. A budget changes or disappears only with `ruling <YYYY-MM-DD>` in the row's notes and a decisions line; a metric whose feature a CR removed is retired with a `retired` row carrying the same ruling note; the tool fails otherwise. **Over budget** blocks the gate unless the architect records a ruling (with a task to fix it); a **regression** beyond the threshold is investigated before tagging (re-measure first — host noise is a reason to re-measure, not to ignore). A metric measured before but missing now is a finding.
- **Claims are re-measured:** a task or review that claims a performance or memory improvement includes before/after numbers, and the reviewer reproduces them independently (the first project found an implementer's stated cause wrong on re-measurement).

## 5. Visual regression (UI projects)

- Screenshot baselines for every screen and key state, in both themes, at the smallest and a desktop width, taken in the mock E2E project with deterministic data (fixed clock, seeded ids, animations disabled, fonts loaded).
- A difference beyond a small threshold fails the run; the diff images are kept as test artifacts.
- Baselines change only with the screen change that causes them, in the same commit, and only when the change matches an approved design or an accepted deviation; the reviewer checks updated baselines against the design.
- Visual tests run in the mock project only (stable data); they do not replace the QA agent's judgment.

## 6. Tech-debt budget

- **Register:** `ai-workspace/tech-debt.md`, one line per item: `<id> · <source: review/QA/gate> · <file or area> · <problem> · <size S/M/L>`. Reviewers' and QA's S3 items land here instead of being lost in reports.
- **Budget:** when acceptance QA closes — or, in a phase without a QA run, when the review follow-ups close — the architect writes one hygiene task per track that has register items, numbered `H<n>.<k>` across the phase (`H3.1` backend, `H3.2` frontend …; full task format, `Covers: —`, owning only that track's folders; plan edit → `checklist-gen.py` → `plan-audit.py`), taking the most valuable items up to ~400 changed lines — oversized files split, duplicated helpers merged, stale comments fixed, flaky tests made deterministic. It lands before the gate fixer, through the merge routine, and is inside the gate fixer's scope; it never mixes with feature work and keeps every test green.
- At the final gate the register is either empty or each remaining item is listed in the hand-over as a known follow-up.

## 7. How this fits the phase

```
build batches → merges → phase reviews (+ security review when in scope) → follow-ups
  → acceptance QA (alone) → Q-fixes → hygiene tasks H<n>.<k>
  → gate fixer (alone) → architect re-run (alone) incl. trace-audit + perf-compare
  → phase retro → tag
```

## 8. Optional strengtheners (the plan says yes or no to each)

- **Mutation testing on pure logic** (e.g. Stryker, mutmut) at the final gate, or at phases that add core rules: a surviving mutant in a state machine or money calculation means a test cannot fail when it should. Target a mutation score for the pure packages only; never on I/O shells.
- **Generated API documentation** from the shared schemas (e.g. OpenAPI), built by a root script and checked in the contract check so it cannot drift.
- **Property-based tests** for parsers, state transitions and money arithmetic.
- **Pre-push hook** running the check and the secret scan (02 Step 5) — recommended for every project; it costs nothing.

## 9. Evals for AI features (prompts, agents, model calls)

Prompts cannot be unit-tested like code, and nobody may call the paid model to find out. The plan gives every prompt or agent:
- **A golden set:** 10–30 inputs with the expected properties of the output (schema validity, required fields, forbidden content, length and language limits, decisions the prompt must make on each input), run through the **mock engine** inside `check`. The mock returns scripted outputs per input so the parsing, validation and repair paths are exercised; the golden set is a fixture file next to the prompt, named after the requirement ids it proves.
- **Recorded live samples:** the owner's smoke script (03 "Money") saves each real request and response as a fixture (secrets stripped, ids anonymised). Later prompt or parser changes are checked against those recordings (the parser still accepts them; the repaired output still validates). Recordings are refreshed only by the owner running the script again; their cost is printed first.
- **A prompt is a contract:** prompt text, output schema and the allow-list of parameters the model may set live in the contract package; a change to any of them is a contract change (approved, mock updated in the same batch, golden set and recordings re-run, decisions line with the reason).
- **Evaluation of quality** (does the output read well, is the decision right) is the acceptance-QA agent's job in mock mode (§2) and the owner's with live samples; it is never a gate step that costs money.
- **Guard rails are tested like security:** a golden case per prompt where the input tries to change the instructions, point at another URL or widen a parameter, asserting the allow-list holds (05).

CHANGELOG
- 2026-10-18 created from the Phase 1 retro discussion: requirement traceability with ids, a user-perspective acceptance QA agent with demo artifacts, a planned security review, performance budgets as gate metrics, visual regression baselines, a tech-debt register and per-phase hygiene task.
  Optional strengtheners: mutation testing, generated API docs, property-based tests, pre-push hook.
- 2026-10-18 §9 evals for AI features: golden sets in the mock engine, recorded live samples as fixtures, prompts as contract, guard-rail cases.
- 2026-10-18 review: definition line carries the milestone; verdicts change only via the re-check; hygiene task per track written when QA closes; references fixed.
- 2026-10-19 review 2: hygiene ids `H<n>.<k>` (tool-visible), trigger without a QA run; budget changes need a dated ruling; re-check citation.
- 2026-10-19 review 3: retiring a metric.
