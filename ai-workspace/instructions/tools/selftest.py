#!/usr/bin/env python3
"""Self-test for the instruction tools — run after editing any tool and in every retro PR.

Usage:  python3 -I ai-workspace/instructions/tools/selftest.py

Builds a tiny fixture project in a temporary directory (a spec with requirement ids and a
changelog, a plan with track files and a contract file, a progress log, test files, a perf
table, git-style diffs for several ecosystems, conflicted logs) and runs every tool against it,
asserting exit codes and the key output lines — one case per defect a review ever found, so a
regression in a tool is caught before it reaches a gate. Prints `SELFTEST: PASS` or every failing
assertion with the tool's output. Needs only python3; no network, no git.
"""
import pathlib, subprocess, sys, tempfile, shutil

TOOLS = pathlib.Path(__file__).resolve().parent
FAILS = []

def run(tool, *args, cwd=None):
    r = subprocess.run([sys.executable, '-I', str(TOOLS / tool), *map(str, args)], capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout + r.stderr

def section(out, title):
    """Lines of the report section whose header contains `title` (headers start with '--- ')."""
    lines, grab, got = out.splitlines(), False, []
    for l in lines:
        if l.startswith('--- '):
            grab = title in l; continue
        if grab:
            got.append(l)
    return '\n'.join(got)

def in_block(text, tid, old, new):
    """Replace `old` with `new` inside the `### <tid>` block of a checklist only."""
    head = f'### {tid} — '
    i = text.index(head); j = text.find('\n### ', i + 1); j = len(text) if j < 0 else j
    return text[:i] + text[i:j].replace(old, new, 1) + text[j:]

def check(name, cond, out):
    if not cond:
        FAILS.append(name); print(f'FAIL: {name}\n{out}\n')

def task(tid, title, covers='—', deps='—', owns='apps/api/src', do='implement it', tests='int: it works', done='`check` green'):
    return (f"### {tid} — {title}\nSpec: §5\nCovers: {covers}\nDepends on: {deps}\nOwns: {owns}\n"
            f"Do:\n  - {do}\nTests:\n  - {tests}\nDone when:\n  - {done}\n\n")

TICKS = "- [x] B1.1 · done\n- [ ] B1.2 · pending\n- [ ] B1.3 · pending\n- [ ] B3.1 · pending\n"

def backend_track(**over):
    t = dict(b11=task('B1.1', 'Auth endpoints', 'R-AUTH-01, R-AUTH-02', do='POST /auth/signup returns 201'),
             b12=task('B1.2', 'Tooling', '—', 'B1.1', owns='scripts/'),
             b13=task('B1.3', 'Cap', 'R-PAY-02', 'B1.1'),
             b31=task('B3.1', 'Monthly cap', 'R-PAY-01', 'B1.3'),
             ticks='## Tick list\n' + TICKS)
    t.update(over)
    return f"# Backend track\n\n## Phase P1\n\n{t['b11']}{t['b12']}{t['b13']}## Phase P3\n\n{t['b31']}{t['ticks']}"

SPEC = ("# Product — Build Specification\nSpec version 1.1 · CHANGELOG: 1.1 — added R-PAY-02 (cap warning) · 1.0 — initial\n\n"
        "## 1a. Requirements\n- **R-AUTH-01** (M1) — Sign up with email. Accept: 201 and a session cookie.\n"
        "- **R-AUTH-02** (M1) — Lock after 10 failed logins. Accept: the 11th attempt gets 429.\n"
        "| **R-PAY-01** | (M3) | Monthly cap. Accept: 409 when the cap is reached. |\n"
        "- **R-PAY-02** (M1) — Warn at 80 % of the cap. Accept: a warning notification exists.\n"
        "## 7. Flows\nThe lockout (R-AUTH-02) resets after 15 minutes.\n")

DIFF = """diff --git a/apps/api/src/big.ts b/apps/api/src/big.ts
index 1111111..2222222 100644
--- a/apps/api/src/big.ts
+++ b/apps/api/src/big.ts
@@ -1 +1,3 @@
+const a: any = 1; // TODO later
+fetch('https://api.vendor.com/v1/x')
+ok
diff --git a/apps/web/src/old.tsx b/apps/web/src/old.tsx
deleted file mode 100644
index 1111111..0000000
--- a/apps/web/src/old.tsx
+++ /dev/null
@@ -1 +0,0 @@
-gone
diff --git a/apps/web/src/a.tsx b/apps/web/src/b.tsx
similarity index 100%
rename from apps/web/src/a.tsx
rename to apps/web/src/b.tsx
diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
@@ -1,8 +1,10 @@
 {
   "name": "x",
-  "version": "1.1.0",
+  "version": "1.2.0",
   "scripts": {
+    "test": "vitest run"
   },
   "dependencies": {
+    "left-pad": "1.3.0",
     "zod": "4.0.0"
   }
 }
diff --git a/pyproject.toml b/pyproject.toml
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -1,6 +1,8 @@
 [project]
 name = "svc"
-version = "0.1.0"
+version = "0.2.0"
 dependencies = [
+  "httpx>=0.27",
   "pydantic>=2",
 ]
diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1 +1,2 @@
 pydantic>=2
+requests
diff --git a/go.mod b/go.mod
--- a/go.mod
+++ b/go.mod
@@ -1,4 +1,5 @@
 module example.com/svc
 require (
+\tgithub.com/pkg/errors v0.9.1
 \tgolang.org/x/text v0.3.0
 )
diff --git a/Cargo.toml b/Cargo.toml
--- a/Cargo.toml
+++ b/Cargo.toml
@@ -1,4 +1,5 @@
 [package]
 name = "svc"
 [dependencies]
+serde = { version = "1", features = ["derive"] }
diff --git a/build.gradle b/build.gradle
--- a/build.gradle
+++ b/build.gradle
@@ -1,2 +1,3 @@
 dependencies {
+    implementation 'com.squareup.okhttp3:okhttp:4.12.0'
 }
"""
SECRET_DIFF = "diff --git a/apps/api/src/k.ts b/apps/api/src/k.ts\n--- a/apps/api/src/k.ts\n+++ b/apps/api/src/k.ts\n@@ -1 +1 @@\n+const key = 'sk-abcdefghijklmnopqrstuvwxyz123456'\n"
PERF_HEAD = "date,gate,metric,value,unit,budget,direction,notes\n"
PERF = (PERF_HEAD + "2026-10-01,P3,api.p95,84,ms,200,lower,\n2026-10-01,P3,mem,2000,MB,2600,lower,\n2026-10-01,P3,errors,0,count,,lower,\n"
        "2026-10-08,P4,api.p95,120,ms,200,lower,\n2026-10-08,P4,mem,2700,MB,2600,lower,\n2026-10-08,P4,errors,4,count,,lower,\n")

def main():
    if any(a in ('-h', '--help') for a in sys.argv[1:]):
        print(__doc__); return 0
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp); plan = root / 'ai-workspace' / 'plan'; plan.mkdir(parents=True)
        docs = root / 'docs'; docs.mkdir(); src = root / 'src'; src.mkdir()
        (root / 'spec.md').write_text(SPEC)
        (plan / '05-backend-track.md').write_text(backend_track())
        (plan / '03-contract.md').write_text("# Contract package\n\n## Phase P1\n\n" + task('C1.1', 'Schemas', '—', owns='packages/shared'))
        (plan / '10-phase-review-protocol.md').write_text("# Review protocol\n\nExample heading format: `### <ID> — <title>` is how tasks look; see B1.1 in the track file.\n")
        (docs / 'PROGRESS.md').write_text("B1.1 · 2026-10-18 · auth endpoints\n")

        # ---- checklist-gen
        rc, out = run('checklist-gen.py', plan)
        check('checklist-gen writes the backend checklist with exactly one box per item (tick list under its own heading ignored)',
              rc == 0 and 'wrote backend-checklist.md: 5 tasks, 15 boxes' in out, out)
        rc, out = run('checklist-gen.py', plan, '--check')
        check('checklist-gen --check reports up to date', rc == 0 and 'up to date' in out, out)
        (plan / '05-backend-track.md').write_text(backend_track(ticks=TICKS))          # tick list right after the last task, no heading
        rc, out = run('checklist-gen.py', plan)
        check('checklist-gen does not turn a headingless roll-up tick list into Done boxes', '5 tasks, 15 boxes' in out and 'Done: [x]' not in (plan / 'checklists/backend-checklist.md').read_text(), out)
        (plan / '05-backend-track.md').write_text(backend_track())
        cl = plan / 'checklists' / 'backend-checklist.md'
        cl.write_text(cl.read_text().replace('- [ ] POST /auth/signup returns 201', '- [x] POST /auth/signup returns 201 — int green', 1))
        rc, out = run('checklist-gen.py', plan)
        check('checklist-gen keeps a tick and its note across regeneration', '- [x] POST /auth/signup returns 201 — int green' in cl.read_text(), out + cl.read_text())

        # ---- plan-audit
        rc, out = run('plan-audit.py', plan)
        check('plan-audit PASS on a complete plan (example heading in a non-track file ignored)', rc == 0 and 'RESULT: PASS' in out, out)
        rc, out = run('plan-audit.py', plan, '--no-covers')
        check('plan-audit --no-covers still PASS', rc == 0 and 'RESULT: PASS' in out, out)
        variants = {
            'missing Covers': (backend_track(b12=task('B1.2', 'Tooling', '—', 'B1.1').replace('Covers: —\n', '')), 'missing: Covers'),
            'empty Do': (backend_track(b12=task('B1.2', 'Tooling', '—', 'B1.1').replace('Do:\n  - implement it\n', 'Do:\n')), 'empty: Do'),
            'Covers: TBD': (backend_track(b12=task('B1.2', 'Tooling', 'TBD', 'B1.1')), 'Covers must be'),
            'undefined Depends on': (backend_track(b12=task('B1.2', 'Tooling', '—', 'B9.9r1')), 'Depends on undefined ids'),
            'dependency cycle': (backend_track(b12=task('B1.2', 'Tooling', '—', 'B1.3'), b13=task('B1.3', 'Cap', 'R-PAY-02', 'B1.2')), 'dependency cycles'),
            'thinking aloud': (backend_track(b12=task('B1.2', 'Tooling', '—', 'B1.1', do='Use redis? No, keep it in memory')), 'thinking-aloud phrasing ==\n  ['),
        }
        for name, (text, expect) in variants.items():
            (plan / '05-backend-track.md').write_text(text); run('checklist-gen.py', plan)
            rc, out = run('plan-audit.py', plan)
            check(f'plan-audit FAIL on {name}', rc == 1 and expect in out and 'RESULT: FAIL' in out, out)
        (plan / '05-backend-track.md').write_text(backend_track(b12=task('B1.2', 'Tooling', '—', 'B1.1', do='| cache | No — out of scope |')))
        run('checklist-gen.py', plan); rc, out = run('plan-audit.py', plan)
        check('plan-audit does not flag "No — out of scope" inside a table cell', rc == 0, out)
        (plan / '05-backend-track.md').write_text(backend_track(b12=task('B1.2', 'Tooling', '—', 'B1.1; the P1 contract slice (frozen); M3 milestone context')))
        run('checklist-gen.py', plan); rc, out = run('plan-audit.py', plan)
        check('plan-audit: phase/milestone ids inside Depends on are context, not undefined tasks', rc == 0, out)
        (plan / '01-architecture.md').write_text("# Architecture\n\n- No — the queue stays in Redis (a decision note outside Do:)\n")
        rc, out = run('plan-audit.py', plan)
        check('plan-audit: a "No —" decision note outside a Do: block is not flagged', rc == 0, out)
        (plan / '01-architecture.md').unlink()
        hyg = (backend_track(ticks='## Tick list\n' + TICKS + '- [x] B1.2r1 · done\n') + "\n## Phase P1 hygiene and follow-ups\n\n"
               + task('H1.1', 'Hygiene: split big files', '—', 'B1.1') + task('B1.1ar1', 'Follow-up of a split task', 'R-ZZZ-01', 'B1.1') + task('B1.2r1', 'Review follow-up', '—', 'B1.2'))
        (plan / '05-backend-track.md').write_text(hyg); rc, out = run('checklist-gen.py', plan)
        check('checklist-gen writes boxes for hygiene (H1.1), split-follow-up (B1.1ar1) and follow-up (B1.2r1) ids', rc == 0 and '8 tasks, 24 boxes' in out, out)
        rc, out = run('plan-audit.py', plan)
        check('plan-audit sees H1.1, B1.1ar1 and B1.2r1: 8 tasks, none incomplete', rc == 0 and 'tasks: 8, incomplete: 0' in out, out)
        (docs / 'PROGRESS.md').write_text("B1.1 · 2026-10-18 · auth endpoints\nB1.2r1 · 2026-10-18 · review follow-up\n")
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md')
        check('checklist-audit parses r<k> ids whole: a ticked B1.2r1 roll-up line with a log line is not drift', 'B1.2r' not in section(out, 'roll-up lines') and 'B1.2r1 ticked' not in out, out)
        (docs / 'PROGRESS.md').write_text("B1.1 · 2026-10-18 · auth endpoints\n")
        (root / 'empty').mkdir(exist_ok=True)
        rc, out = run('trace-audit.py', root / 'spec.md', plan, root / 'empty')
        check('trace-audit scans the B1.1ar1 task (its bogus Covers id is reported) and runs with an empty test root', rc == 1 and 'R-ZZZ-01' in section(out, 'never defined'), out)
        (plan / '05-backend-track.md').write_text(backend_track()); run('checklist-gen.py', plan)
        (plan / '10-phase-review-protocol.md').write_text("# Review protocol\n\nExample: `B9.9` is how an id looks; real references look like B1.1.\n")
        rc, out = run('plan-audit.py', plan)
        check('plan-audit ignores an undefined id written in backticks (an example)', rc == 0, out)
        (plan / '10-phase-review-protocol.md').write_text("# Review protocol\n\nSee B9.9 for details.\n")
        rc, out = run('plan-audit.py', plan)
        check('plan-audit flags an undefined id outside backticks', rc == 1 and 'B9.9' in out, out)
        (plan / '10-phase-review-protocol.md').write_text("# Review protocol\n\nExample heading format: `### <ID> — <title>`.\n")
        (plan / '07-mobile-track.md').write_text("# Mobile\n\n## Phase P1\n\n" + task('M1.1', 'App shell', '—'))
        run('checklist-gen.py', plan); rc, out = run('plan-audit.py', plan)
        check('plan-audit FAIL on a reserved track letter (M)', rc == 1 and 'reserved ids' in out, out)
        (plan / '07-mobile-track.md').unlink(); (plan / 'checklists' / 'mobile-checklist.md').unlink()
        (plan / '05-backend-track.md').write_text(backend_track()); run('checklist-gen.py', plan)
        rc, out = run('plan-audit.py', root / 'nowhere')
        check('plan-audit FAIL on a wrong path', rc != 0 and 'RESULT: PASS' not in out, out)

        # ---- checklist-audit (binary)
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md')
        check('checklist-audit FAIL: done task with open boxes without a note', rc == 1 and 'B1.1: done but' in out and 'without a note' in out and 'RESULT: FAIL' in out, out)
        text = in_block(cl.read_text(), 'B1.1', '- [ ] Test: int: it works', '- [x] Test: int: it works — int green')
        text = in_block(text, 'B1.1', '- [ ] Done: `check` green', '- [ ] Done: `check` green — waits for Gate P1')
        cl.write_text(text)
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md')
        check('checklist-audit PASS once every open box of a done task has a note', rc == 0 and 'RESULT: PASS' in out and 'backend-checklist.md: 2/15 ticked' in out, out)
        (plan / '05-backend-track.md').write_text(backend_track(ticks='## Tick list\n' + TICKS.replace('- [ ] B3.1', '- [x] B3.1')))
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md')
        check('checklist-audit FAIL: roll-up line ticked but not in the log', rc == 1 and 'B3.1 ticked but not in the log' in out, out)
        (plan / '05-backend-track.md').write_text(backend_track())
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase', 'P1')
        check('checklist-audit --phase P1 FAIL: tasks of the phase with no progress line', rc == 1 and 'B1.2: no progress-log line' in out and 'C1.1: no progress-log line' in out, out)
        (docs / 'PROGRESS.md').write_text("B1.1 · 2026-10-18 · auth endpoints\nB1.2 · 2026-10-18 · tooling\nB1.3 · 2026-10-18 · cap\nC1.1 · 2026-10-18 · schemas\n")
        (plan / '05-backend-track.md').write_text(backend_track(ticks='## Tick list\n' + TICKS.replace('- [ ] B1.2', '- [x] B1.2').replace('- [ ] B1.3', '- [x] B1.3')))
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase', 'P1')
        check('checklist-audit --phase P1 FAIL: logged tasks still have open boxes without a note', rc == 1 and 'open box(es) without a note' in out, out)
        text = cl.read_text()
        for t in ['B1.2', 'B1.3', 'C1.1']:
            for box in ['- [ ] implement it', '- [ ] Test: int: it works', '- [ ] Done: `check` green']:
                text = in_block(text, t, box, box.replace('- [ ]', '- [x]') + ' — green')
        cl.write_text(text)
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase', 'P1')
        check('checklist-audit --phase P1 PASS once every P1 task is logged and ticked or noted', rc == 0 and 'RESULT: PASS' in out, out)
        (plan / 'checklists' / 'phase-gate-checklist.md').write_text("# Gate checklist (template)\n- [ ] check green\n- [ ] images built\n")
        (docs / 'PROGRESS.md').write_text((docs / 'PROGRESS.md').read_text() + "B3.1 · 2026-10-18 · cap\n")
        (plan / '05-backend-track.md').write_text(backend_track(ticks='## Tick list\n' + TICKS.replace('- [ ]', '- [x]')))
        text = cl.read_text()
        for box in ['- [ ] implement it', '- [ ] Test: int: it works', '- [ ] Done: `check` green']:
            text = in_block(text, 'B3.1', box, box.replace('- [ ]', '- [x]') + ' — green')
        cl.write_text(text)
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase', 'P3')
        check('checklist-audit --phase: the last block of a checklist never runs on into the template file that sorts after it', rc == 0 and 'RESULT: PASS' in out, out)
        (docs / 'PROGRESS.md').write_text("B1.1 · 2026-10-18 · auth endpoints\nB1.2 · 2026-10-18 · tooling\nB1.3 · 2026-10-18 · cap\nC1.1 · 2026-10-18 · schemas\n")
        (plan / '05-backend-track.md').write_text(backend_track(ticks='## Tick list\n' + TICKS.replace('- [ ] B1.2', '- [x] B1.2').replace('- [ ] B1.3', '- [x] B1.3')))
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase', 'P9')
        check('checklist-audit --phase P9 (no such phase) fails instead of passing silently', rc == 1 and 'no task sits under a heading naming P9' in out, out)
        (plan / '05-backend-track.md').write_text(backend_track(ticks='## Tick list\n' + TICKS.replace('- [ ] B1.2', '- [x] B1.2').replace('- [ ] B1.3', '- [x] B1.3')) + "\n## PDF export and POST endpoints\n\n" + task('B9.1', 'Orphan under a heading that names no phase', '—'))
        run('checklist-gen.py', plan); rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase', 'P1')
        check('checklist-audit --phase lists tasks under headings that name no phase (a P-word like PDF is not a phase)', rc == 1 and 'B9.1' in out and 'names no phase' in out, out)
        (plan / '05-backend-track.md').write_text(backend_track(ticks='## Tick list\n' + TICKS.replace('- [ ] B1.2', '- [x] B1.2').replace('- [ ] B1.3', '- [x] B1.3'))); run('checklist-gen.py', plan)
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase', 'P3')
        check('checklist-audit --phase P3 FAIL: B3.1 not done', rc == 1 and 'B3.1: no progress-log line' in out, out)
        rc, out = run('checklist-audit.py', plan, docs / 'PROGRESS.md', '--phase')
        check('checklist-audit: --phase without a value exits 2', rc == 2, out)
        (docs / 'PROGRESS.md').write_text("B1.1 · 2026-10-18 · auth endpoints\n")
        (plan / '05-backend-track.md').write_text(backend_track())

        # ---- trace-audit
        (src / 'auth.test.ts').write_text("it('R-AUTH-01: signs up', () => {})\nit.skip('R-AUTH-02: locks after 10 failures', () => {})\n// R-PAY-07 typo in a comment\n")
        rc, out = run('trace-audit.py', root / 'spec.md', plan, src, '--milestone', 'M1')
        check('trace-audit: a requirement first named in the changelog is still in M1 scope (definition line wins)', '3 in scope (≤ M1)' in out, out)
        check('trace-audit: skipped test is not proof; comment typo reported; exit 1',
              rc == 1 and 'proven by a test: 1/3' in out and 'R-PAY-07' in out
              and 'R-AUTH-02' in section(out, 'proven only by skipped tests'), out)
        check('trace-audit: tasks in the plan all have Covers; non-track files are not scanned', 'tasks without a Covers: line: 0' in out, out)
        (src / 'auth.test.ts').write_text("it('R-AUTH-01: signs up', () => {})\nit('R-AUTH-02: locks after 10 failures', () => {})\n")
        (src / 'test_pay.py').write_text("def test_R_PAY_02_warns_at_80_percent():\n    assert True\n")
        rc, out = run('trace-audit.py', root / 'spec.md', plan, src, '--milestone', 'M1')
        check('trace-audit PASS once every M1 requirement is proven (ts and python test names)', rc == 0 and 'proven by a test: 3/3' in out, out)
        rc, out = run('trace-audit.py', root / 'spec.md', plan, src)
        check('trace-audit without --milestone: M3 requirement has no test, exit 1', rc == 1 and 'R-PAY-01' in section(out, 'without a (non-skipped) test'), out)
        (src / 'test_skipped.py').write_text("import pytest\n\n@pytest.mark.skip(reason='QUAR-1 flaky')\ndef test_R_PAY_01_cap_409():\n    assert True\n")
        (src / 'block.test.ts').write_text("describe.skip('cap', () => {\n  it('R-PAY-01: returns 409', () => {})\n})\nit('R-AUTH-01: still proven', () => {})\n")
        (src / 'ignored_test.rs').write_text("#[test]\n#[ignore]\nfn test_R_PAY_01_cap() {}\n")
        rc, out = run('trace-audit.py', root / 'spec.md', plan, src)
        check('trace-audit: a decorator above the test, a describe.skip block and #[ignore] do not count as proof',
              rc == 1 and 'R-PAY-01' in section(out, 'proven only by skipped tests') and 'proven by a test: 3/4' in out, out)
        (src / 'test_more_skips.py').write_text(
            "import pytest\n\n@pytest.mark.skip(reason='whole class')\nclass TestCap:\n    def test_R_PAY_01_first(self):\n        assert True\n\n    def test_R_PAY_01_second(self):\n        assert True\n\n"
            "@pytest.mark.skip(reason='flaky')\n@pytest.mark.parametrize('x', [\n    1,\n    2,\n    3,\n    4,\n])\ndef test_R_PAY_01_param(x):\n    assert True\n")
        (src / 'fixme.spec.ts').write_text("test.describe.fixme('cap', () => {\n  test('R-PAY-01: cap', async () => {})\n})\n")
        (src / 'test_comment_gap.py').write_text("import pytest\n\n@pytest.mark.skip(reason='flaky')\n# BUG-12: re-enable after the fix\ndef test_R_PAY_01_commented():\n    assert True\n")
        (src / 'DisabledTest.java').write_text("@Disabled(\"quarantined\")\npublic class DisabledTest {\n  @DisplayName(\"R-PAY-01: cap\")\n  @Test\n  void cap() {}\n}\n")
        (src / 'CapTest.java').write_text("class CapTest {\n  @DisplayName(\"R-PAY-02: warns at 80 percent\")\n  @Test\n  void warns() {}\n}\n")
        (src / 'test_pay.py').unlink()                      # now only the Java @DisplayName line proves R-PAY-02
        rc, out = run('trace-audit.py', root / 'spec.md', plan, src)
        check('trace-audit: skipped class (also `public class`), skip above a multi-line decorator or a comment line, describe.fixme: not proof; an id in @DisplayName above @Test counts',
              rc == 1 and 'R-PAY-01' in section(out, 'proven only by skipped tests') and 'proven by a test: 3/4' in out, out)
        (src / 'test_pay.py').write_text("def test_R_PAY_02_warns_at_80_percent():\n    assert True\n")
        for f in ['test_skipped.py', 'block.test.ts', 'ignored_test.rs', 'test_more_skips.py', 'fixme.spec.ts', 'CapTest.java', 'test_comment_gap.py', 'DisabledTest.java']:
            (src / f).unlink()
        rc, out = run('trace-audit.py', root / 'spec.md', plan, src, '--milestone')
        check('trace-audit: --milestone without a value exits 2', rc == 2, out)
        bad = SPEC.replace('1.0 — initial', '1.0 — initial; R-AUTH-09 dropped').replace('- **R-PAY-02** (M1)', '- **R-AUTH-01** (M1) — dup.\n- **R-UI-01** — no milestone.\n- **R-PAY-02** (M1)')
        (root / 'spec_bad.md').write_text(bad)
        rc, out = run('trace-audit.py', root / 'spec_bad.md', plan, src)
        check('trace-audit: undefined reference, duplicate definition and missing milestone all fail',
              rc == 1 and 'R-AUTH-09' in section(out, 'never defined') and 'R-AUTH-01' in section(out, 'defined twice')
              and 'R-UI-01' in section(out, 'without a (M<k>) tag'), out)

        # ---- perf-compare
        (docs / 'perf.csv').write_text(PERF)
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: over budget fails, regression flagged, zero baseline is a regression',
              rc == 1 and 'mem: 2700 MB (budget 2600)  <-- OVER BUDGET' in out and 'api.p95: 120 ms (budget 200)  <-- REGRESSION' in out and 'errors: 4 count  <-- REGRESSION vs 0 (from 0)' in out, out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,mem,2700,MB,2600,lower,', '2026-10-08,P4,mem,2500,MB,2600,Lower,'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: direction typo is rejected (exit 2)', rc == 2 and 'direction must be' in out, out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,mem,2700,MB,2600,lower,', '2026-10-08,P4,mem,2700,MB,3000,lower,'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: a raised budget without a ruling fails', rc == 1 and 'BUDGET CHANGED' in out, out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,mem,2700,MB,2600,lower,', '2026-10-08,P4,mem,2700,MB,3000,lower,ruling 2026-10-08 render cache').replace('2026-10-08,P4,errors,4,count,,lower,', '2026-10-08,P4,errors,0,count,,lower,'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare PASS: budget change with a ruling, regression only printed', rc == 0 and 'BUDGET CHANGED' not in out and 'REGRESSION' in out, out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,errors,4,count,,lower,\n', ''))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: a dropped metric fails', rc == 1 and 'errors' in section(out, 'missing now'), out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,mem,2700,MB,2600,lower,', '2026-10-08,P4,mem,2700,MB,,lower,'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: a budget removed between gates fails', rc == 1 and 'BUDGET CHANGED 2600 -> (none)' in out, out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,mem,2700,MB,2600,lower,', '2026-10-08,P4,mem,2700,MB,3000,lower,no ruling yet'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: "no ruling yet" is not a ruling', rc == 1 and 'BUDGET CHANGED' in out, out)
        rc, out = run('perf-compare.py', docs / 'perf.csv', '--threshold')
        check('perf-compare: --threshold without a value exits 2', rc == 2, out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,mem,2700,MB,2600,lower,', '2026-10-08,P4,mem,retired,MB,,lower,ruling 2026-10-08 CR-003 removed rendering').replace('2026-10-08,P4,errors,4,count,,lower,', '2026-10-08,P4,errors,0,count,,lower,'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: a retired metric with a ruling is neither compared nor expected', rc == 0 and 'mem: retired' in out and 'BUDGET CHANGED' not in out, out)
        (docs / 'perf.csv').write_text(PERF.replace('2026-10-08,P4,mem,2700,MB,2600,lower,', '2026-10-08,P4,mem,retired,MB,,lower,'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: retiring without a ruling is rejected (exit 2)', rc == 2 and 'retired metric needs' in out, out)
        (docs / 'perf.csv').write_text(PERF.replace('120', 'n/a'))
        rc, out = run('perf-compare.py', docs / 'perf.csv')
        check('perf-compare: non-numeric value names the row (exit 2)', rc == 2 and 'row 5' in out, out)

        # ---- diff-review
        tree = root / 'tree'; (tree / 'apps/api/src').mkdir(parents=True); (tree / 'apps/api/src/big.ts').write_text('x\n' * 20)
        (tree / 'package.json').write_text('{\n  "name": "x",\n  "version": "1.2.0",\n  "scripts": {\n    "test": "vitest run"\n  },\n  "dependencies": {\n    "left-pad": "1.3.0",\n    "zod": "4.0.0"\n  }\n}\n')
        (tree / 'pyproject.toml').write_text('[project]\nname = "svc"\nversion = "0.2.0"\ndependencies = [\n  "httpx>=0.27",\n  "pydantic>=2",\n]\n')
        (tree / 'requirements.txt').write_text('pydantic>=2\nrequests\n')
        (tree / 'go.mod').write_text('module example.com/svc\nrequire (\n\tgithub.com/pkg/errors v0.9.1\n\tgolang.org/x/text v0.3.0\n)\n')
        (tree / 'Cargo.toml').write_text('[package]\nname = "svc"\n[dependencies]\nserde = { version = "1", features = ["derive"] }\n')
        (tree / 'build.gradle').write_text("dependencies {\n    implementation 'com.squareup.okhttp3:okhttp:4.12.0'\n}\n")
        (root / 'change.diff').write_text(DIFF)
        rc, out = run('diff-review.py', '--diff', root / 'change.diff', '--tree', tree, '--owned', '^apps/api/', '--max-lines', '10')
        deps, outside = section(out, 'new dependencies'), section(out, 'outside owned paths')
        check('diff-review: deletion and rename outside owned paths are reported',
              rc == 0 and 'deleted: apps/web/src/old.tsx' in outside and 'renamed: apps/web/src/a.tsx -> apps/web/src/b.tsx' in outside and 'big.ts' not in outside, out)
        check('diff-review: banned patterns, host and oversized file', 'any' in out and 'TODO' in out and 'api.vendor.com' in out and '20 apps/api/src/big.ts' in out, out)
        check('diff-review: dependencies detected per ecosystem, scripts/version not flagged',
              all(s in deps for s in ['package.json: "left-pad": "1.3.0"', 'pyproject.toml: httpx>=0.27', 'requirements.txt: requests',
                                      'go.mod: github.com/pkg/errors v0.9.1', 'Cargo.toml: serde = {', "build.gradle: implementation 'com.squareup.okhttp3"])
              and '"test"' not in deps and '"version": "1.2.0"' not in deps and 'version = "0.2.0"' not in deps and '"zod"' not in deps and 'pydantic' not in deps, deps)
        (tree / 'pyproject.toml').write_text('[project]\nname = "svc"\ndependencies = [\n' + ''.join(f'  "dep{i}>=1",\n' for i in range(10)) + '  "evil-pkg>=0.1",\n]\n')
        (root / 'deep.diff').write_text('diff --git a/pyproject.toml b/pyproject.toml\n--- a/pyproject.toml\n+++ b/pyproject.toml\n@@ -11,3 +11,4 @@\n   "dep8>=1",\n   "dep9>=1",\n+  "evil-pkg>=0.1",\n ]\n')
        rc, out = run('diff-review.py', '--diff', root / 'deep.diff', '--tree', tree, '--owned', '.*')
        check('diff-review: a dependency added far below its section header is found (full-file parse)', 'pyproject.toml: evil-pkg>=0.1' in section(out, 'new dependencies'), out)
        (tree / 'pyproject.toml').write_text('[project]\nname = "svc"\ndependencies = ["httpx>=0.27"]\n\n[project.optional-dependencies]\ndev = [\n  "pytest>=8",\n  "ruff>=0.5",\n  "evil-devtool>=0.1",\n]\n')
        (root / 'extra.diff').write_text('diff --git a/pyproject.toml b/pyproject.toml\n--- a/pyproject.toml\n+++ b/pyproject.toml\n@@ -7,3 +7,4 @@\n   "pytest>=8",\n   "ruff>=0.5",\n+  "evil-devtool>=0.1",\n ]\n')
        rc, out = run('diff-review.py', '--diff', root / 'extra.diff', '--tree', tree, '--owned', '.*')
        check('diff-review: an entry added to a multi-line optional-dependencies list is found', 'pyproject.toml: evil-devtool>=0.1' in section(out, 'new dependencies'), out)
        (root / 'fixture.diff').write_text("diff --git a/apps/api/src/x.test.ts b/apps/api/src/x.test.ts\n--- a/apps/api/src/x.test.ts\n+++ b/apps/api/src/x.test.ts\n@@ -1 +1 @@\n+const password = 'demo-password-12345678' // secret-scan: allow demo fixture\n")
        rc, out = run('diff-review.py', '--diff', root / 'fixture.diff', '--tree', tree, '--owned', '.*')
        check('diff-review: an allowed fixture hit is listed separately and does not fail', rc == 0 and 'demo-password' in section(out, 'marked allowed') and not section(out, 'POSSIBLE SECRETS').strip(), out)
        rc, out = run('diff-review.py', '--diff', root / 'fixture.diff', '--tree', tree, '--owned', '.*', '--max-lines', 'ten')
        check('diff-review: --max-lines without an integer exits 2', rc == 2, out)
        (root / 'secret.diff').write_text(SECRET_DIFF)
        rc, out = run('diff-review.py', '--diff', root / 'secret.diff', '--tree', tree, '--owned', '^apps/api/')
        check('diff-review: a possible secret exits 1', rc == 1 and 'POSSIBLE SECRETS' in out and 'sk-abcdef' in out, out)

        # ---- tools.json
        (plan / 'tools.json').write_text('{"contract_track": "core"}')
        rc, out = run('checklist-gen.py', plan)
        check('tools.json contract_track routes 03-* tasks to that checklist', rc == 0 and 'wrote core-checklist.md: 1 tasks' in out, out)
        (plan / 'tools.json').unlink(); (plan / 'checklists' / 'core-checklist.md').unlink()

        # ---- log-union-resolve
        (docs / 'DECISIONS.md').write_text("<<<<<<< ours\nA · 2026-10-18 · ours\n=======\nB · 2026-10-18 · theirs\n>>>>>>> theirs\n")
        (docs / 'perf.csv').write_text(PERF_HEAD + "<<<<<<< ours\n2026-10-08,P4,a,1,ms,,lower,\n=======\n2026-10-08,P4,b,2,ms,,lower,\n>>>>>>> theirs\n")
        rc, out = run('log-union-resolve.py', 'docs/DECISIONS.md', 'docs/perf.csv', cwd=root)
        check('log-union-resolve keeps both sides, also in docs/perf.csv',
              rc == 0 and (docs / 'DECISIONS.md').read_text() == "A · 2026-10-18 · ours\nB · 2026-10-18 · theirs\n" and '<<<' not in (docs / 'perf.csv').read_text(), out)
        (root / 'notes.md').write_text("<<<<<<< ours\nx\n=======\ny\n>>>>>>> theirs\n")
        rc, out = run('log-union-resolve.py', 'notes.md', cwd=root)
        check('log-union-resolve refuses a non-log file', rc != 0 and 'refusing' in out and '<<<<<<<' in (root / 'notes.md').read_text(), out)

        # ---- -h for every tool
        for tool in ['plan-audit.py', 'checklist-gen.py', 'checklist-audit.py', 'trace-audit.py', 'perf-compare.py', 'diff-review.py', 'log-union-resolve.py', 'selftest.py']:
            rc, out = run(tool, '--help')
            check(f'{tool} --help prints usage and exits 0', rc == 0 and 'Usage' in out, out)

    if FAILS:
        print(f'SELFTEST: FAIL ({len(FAILS)}): ' + '; '.join(FAILS)); return 1
    print(f'SELFTEST: PASS (all tools, fixture project)'); return 0

if __name__ == '__main__':
    sys.exit(main())
