#!/usr/bin/env python3
"""Requirement traceability audit: spec requirement -> plan task -> test. Run at every gate.

Usage:
  python3 -I ai-workspace/instructions/tools/trace-audit.py <spec.md> <plan_dir> <test_root> [<test_root> ...]
          [--milestone M3]      only requirements tagged M0..M3 must be covered (default: all;
                                the final gate runs without it)

Conventions it checks (10-quality-system.md §1):
  * Spec: a requirement is DEFINED by exactly one line that starts with its id and carries its
    milestone:  `- **R-AUTH-03** (M1) — Ten failed logins lock the account. Accept: …`
    (list bullet or table row, bold optional). Any other mention of the id — in the changelog,
    a cross-reference, a milestone table — is a reference, not a definition.
  * Plan: every task in the track files (`NN-*-track.md`, `03-*.md`, the same set plan-audit.py
    reads) has a `Covers:` line listing the R-ids it implements, or `Covers: —` for work that
    implements no user-visible requirement (tooling, refactors).
  * Tests: a test proves a requirement when its id is in the title of a test call
    (`it('R-AUTH-03: locks after 10 failed logins', …)`, `def test_R_AUTH_03_…`, `func TestR_AUTH_03`,
    `it 'R-AUTH-03 …'`, `t.Run("R-AUTH-03 …")`). Ids in comments or helpers do not count, nor do
    skipped tests: a marker on the test line (`it.skip`, `xit`, `.todo`, `t.Skip`), a skip in the
    run of decorator/attribute lines directly above it (`@pytest.mark.skip` even above a
    multi-line `@parametrize`, `@Disabled`, `#[ignore]`), a skip-decorated class or a module-level
    `pytestmark = pytest.mark.skip`, or a `describe.skip(` / `describe.fixme(` / `xdescribe(` block
    around it (lines indented deeper than the block's opening line, until the indentation returns).
    Ids in the decorator run count for the test below it (`@DisplayName("R-…")` above `@Test`).
  * Optional `ai-workspace/plan/tools.json` keys: "test_file" (regex on file names),
    "skip_dirs" (list), "test_call" (regex for a test-call line), "skip_markers" (regex),
    "skip_blocks" (regex for a line that opens a skipped block).
  * A plan reviewer (12 §2) runs it with an empty directory as the test root and reads only
    "requirements without a task".

Exit 1 when any of these is non-empty for the requirements in scope:
  1. requirements with no task covering them;
  2. requirements with no (non-skipped) test naming them;
  3. tasks without a `Covers:` line;
  4. ids referenced (spec text, plan, tests) that no definition line defines — typos or removed
     requirements;
  5. ids defined twice, or defined without a milestone tag `(M<k>)`;
  6. requirements proven only by skipped tests.
Exit 2 on unusable input (missing spec or plan directory, no definitions at all).
"""
import re, sys, json, pathlib

RID = r'R-[A-Z][A-Z0-9]*-\d{2,3}'
DEF = re.compile(r'^\s*(?:[-*+]|\d+\.|\|)?\s*\**(' + RID + r')\**\s*\|?\s*(\(M(\d+)\))?', re.M)
ANY = re.compile(r'\b' + RID + r'\b')
TASK = re.compile(r'^### ([A-Z]+\d+(?:\.\d+)?(?:[a-z](?!\d))?(?:r\d+)?(?:[a-z](?!\d))?) — ', re.M)   # the same id pattern in every tool
DEFAULTS = {
    'test_file': r'(\.test\.|\.spec\.|_test\.|_spec\.|(^|/)test_|Tests?\.(java|kt|swift|cs)$|(^|/)tests?/)',
    'skip_dirs': ['node_modules', '.git', 'dist', 'build', '.next', 'coverage', 'test-results',
                  '.venv', 'venv', 'target', 'vendor', '__pycache__'],
    'test_call': r'\b(it|test|describe|context|scenario|Scenario|example|specify)(\.(skip|only|todo|fixme|each|concurrent|failing))*\s*[\(\'"]|^\s*(async\s+)?def\s+test_|^\s*func\s+Test|\bt\.Run\s*\(|^\s*fn\s+\w*test\w*\s*\(|@Test\b|\[Fact\]|\[Theory\]|^\s*it\s+[\'"]',
    'skip_markers': r'\.skip\s*\(|\bxit\s*\(|\bxtest\s*\(|\bxdescribe\s*\(|\.todo\s*\(|\.fixme\s*\(|@pytest\.mark\.skip|@unittest\.skip|\bt\.Skip\b|#\[ignore\]|@Disabled|@Ignore\b|\bpending\s*\(|\bskip\s*:\s*true',
    'skip_blocks': r'\b(describe|context|suite|test\.describe)\.(skip|fixme)\s*\(|\bxdescribe\s*\(|\bxcontext\s*\(',
}

def die(msg, code=2):
    print(msg, file=sys.stderr); sys.exit(code)

def load_cfg(*starts):
    """Optional ai-workspace/plan/tools.json (02 Step 0) with stack-specific patterns; {} otherwise."""
    for s in starts:
        for d in [pathlib.Path(s)] + list(pathlib.Path(s).resolve().parents):
            for c in (d / 'tools.json', d / 'ai-workspace' / 'plan' / 'tools.json'):
                if c.is_file():
                    try:
                        return json.loads(c.read_text())
                    except json.JSONDecodeError as e:
                        die(f'{c}: invalid JSON ({e})')
    return {}

def spec_requirements(spec_text):
    """{rid: milestone|None}, duplicates, and ids referenced but never defined."""
    defs, dups = {}, []
    for m in DEF.finditer(spec_text):
        rid, ms = m.group(1), m.group(3)
        if rid in defs:
            dups.append(rid)
        else:
            defs[rid] = int(ms) if ms else None
    refs = set(ANY.findall(spec_text))
    return defs, sorted(set(dups)), sorted(refs - set(defs))

def plan_coverage(plan_dir):
    P = pathlib.Path(plan_dir)
    files = sorted(list(P.glob('[0-9][0-9]-*-track.md')) + list(P.glob('03-*.md')))
    covered, missing_covers, refs = {}, [], set()
    for f in files:
        parts = TASK.split(f.read_text())
        for i in range(1, len(parts), 2):
            tid, body = parts[i], re.split(r'^## ', parts[i + 1], flags=re.M)[0]
            m = re.search(r'^\s*Covers:(.*)$', body, re.M)
            if not m:
                missing_covers.append(f'{f.name}: {tid}')
                continue
            for rid in ANY.findall(m.group(1)):
                covered.setdefault(rid, []).append(tid); refs.add(rid)
    return covered, missing_covers, refs, bool(files)

def test_coverage(roots, cfg):
    test_file = re.compile(cfg.get('test_file', DEFAULTS['test_file']))
    skip_dirs = set(cfg.get('skip_dirs', DEFAULTS['skip_dirs']))
    call = re.compile(cfg.get('test_call', DEFAULTS['test_call']))
    skip = re.compile(cfg.get('skip_markers', DEFAULTS['skip_markers']))
    block_skip = re.compile(cfg.get('skip_blocks', DEFAULTS['skip_blocks']))
    proven, skipped_only, mentioned = {}, set(), set()
    for root in roots:
        for p in pathlib.Path(root).rglob('*'):
            if not p.is_file() or (set(p.parts) & skip_dirs) or not test_file.search(p.relative_to(root).as_posix()):
                continue
            deco, deco_depth, block_indent = [], 0, None   # decorator run above the current line; indent of an open skipped block
            text = p.read_text(errors='ignore')
            if re.search(r'^\s*pytestmark\s*=.*\bskip\b', text, re.M):
                block_indent = -1                          # a module-level skip mark skips the whole file
            for line in text.splitlines():
                indent = len(line) - len(line.lstrip())
                s = line.strip()
                if block_indent is not None and block_indent >= 0 and s and indent <= block_indent:
                    block_indent = None                    # the skipped block closed
                if block_indent is None and block_skip.search(line):
                    block_indent = indent
                deco_text = ' '.join(deco)
                deco_skipped = bool(skip.search(deco_text))
                if block_indent is None and deco_skipped and re.match(r'^\s*(?:\w+\s+)*class\s', line):   # also `public class`, `final class`
                    block_indent = indent                  # a skip-decorated class skips every test in it
                ids = set(ANY.findall(line)) | {x.replace('_', '-') for x in re.findall(r'R_[A-Z][A-Z0-9]*_\d{2,3}', line)}
                if call.search(line):
                    ids |= set(ANY.findall(deco_text))     # e.g. @DisplayName("R-…") above @Test / the method line
                if ids:
                    mentioned |= ids
                    if call.search(line):
                        # skipped when: a marker on the line, inside a skipped block (describe.skip, a skipped
                        # class, pytestmark), or a skip in the decorator/attribute run directly above
                        if skip.search(line) or (block_indent is not None and indent > block_indent) or deco_skipped:
                            skipped_only |= ids
                        else:
                            for rid in ids:
                                proven.setdefault(rid, set()).add(str(p))
                # maintain the decorator run: lines starting with @ or #[ (and the continuation lines of an
                # unclosed decorator call) stack up; blank and comment lines keep the run; anything else resets it
                if s.startswith('@') or s.startswith('#['):
                    deco.append(s); deco_depth += s.count('(') - s.count(')')
                elif deco and deco_depth > 0:
                    deco.append(s); deco_depth += s.count('(') - s.count(')')
                elif s and not re.match(r'^(#(?!\[)|//|/\*|\*)', s):
                    deco, deco_depth = [], 0
    return proven, skipped_only - set(proven), mentioned

def main(argv):
    if len(argv) < 3 or any(a in ('-h', '--help') for a in argv):
        print(__doc__); sys.exit(0 if any(a in ('-h', '--help') for a in argv) else 2)
    milestone = None
    if '--milestone' in argv:
        i = argv.index('--milestone')
        if i + 1 >= len(argv) or not re.fullmatch(r'[Mm]?\d+', argv[i + 1]):
            die('--milestone needs a value like M3')
        milestone = int(argv[i + 1].lstrip('Mm')); del argv[i:i + 2]
    spec, plan_dir, roots = pathlib.Path(argv[0]), argv[1], argv[2:]
    if not spec.is_file() or not pathlib.Path(plan_dir).is_dir():
        die(f'spec file or plan directory not found: {spec} / {plan_dir}')
    cfg = load_cfg(plan_dir)
    defs, dups, spec_undefined = spec_requirements(spec.read_text())
    if not defs:
        die('no requirement definition lines (`- **R-<AREA>-<nn>** (M<k>) — …`) found in the spec — see 10-quality-system.md §1')
    covered, missing_covers, plan_refs, has_tracks = plan_coverage(plan_dir)
    if not has_tracks:
        die(f'no track files (NN-*-track.md / 03-*.md) in {plan_dir}')
    proven, skipped_only, test_refs = test_coverage(roots, cfg)
    no_ms = sorted(r for r, m in defs.items() if m is None)
    scope = {r for r, m in defs.items() if milestone is None or (m is not None and m <= milestone)}
    no_task = sorted(r for r in scope if r not in covered)
    no_test = sorted(r for r in scope if r not in proven)
    undefined = sorted((plan_refs | test_refs | set(spec_undefined)) - set(defs))
    skipped = sorted(r for r in skipped_only if r in scope)
    print(f'requirements: {len(defs)} defined in the spec, {len(scope)} in scope'
          f'{f" (≤ M{milestone})" if milestone is not None else ""}')
    print(f'covered by a task: {len(scope) - len(no_task)}/{len(scope)} · proven by a test: {len(scope) - len(no_test)}/{len(scope)}')
    report = [('requirements without a task', no_task), ('requirements without a (non-skipped) test', no_test),
              ('tasks without a Covers: line', missing_covers),
              ('ids referenced but never defined (typo or removed requirement)', undefined),
              ('ids defined twice', dups), ('definitions without a (M<k>) tag', no_ms),
              ('requirements proven only by skipped tests', skipped)]
    for title, items in report:
        print(f'--- {title}: {len(items)}')
        for x in items:
            print('  ', x)
    sys.exit(1 if any(items for _, items in report) else 0)

if __name__ == '__main__':
    main(sys.argv[1:])
