#!/usr/bin/env python3
"""Plan readiness audit — run before declaring a plan ready for implementers.

Usage:  python3 -I ai-workspace/instructions/tools/plan-audit.py ai-workspace/plan [--no-covers]

Checks (exit code 1 on any failure):
 1. Every task heading `### <ID> — <title>` in the track files has ALL fields, each NON-EMPTY
    (inline text or at least one bullet): Spec:, Covers:, Depends on:, Owns:, Do:, Tests:,
    Done when:  (exact labels, one per line). `Covers:` is `—` or a comma list of requirement
    ids R-<AREA>-<nn> (10-quality-system.md §1) — nothing else (no "TBD").
    `--no-covers` audits a plan written before requirement ids existed.
 2. Every task id in a track file has a block in its checklist file and vice versa.
 3. No task id is referenced anywhere in the plan that is not defined — including follow-up
    forms (B4.6r1, B4.6a) and every id named in `Depends on:`; `Depends on:` has no cycles.
    An undefined id inside backticks is an example, not a reference (write examples that way).
 4. No thinking-aloud phrasing ("? No", a line starting with "No —" / "No:") inside `Do:` blocks.
    Phase and milestone ids (P1, M3) inside `Depends on:` are context ("`P1` slice"), not tasks.
 5. Track letters never collide with reserved ids: M (spec milestones), P (phases),
    R (requirements).
Project-specific file names are discovered, not hard-coded: a track file is any
`NN-*-track.md` or `03-*.md`; its checklist is `checklists/<track>-checklist.md`
where <track> is taken from the file name (`04-infra-track.md` -> `infra`).
A missing plan directory, no track files or no task headings is a FAIL (a wrong path must
never print PASS). Without an argument it audits ai-workspace/plan.
"""
import re, sys, pathlib

FIELDS = ['Spec:', 'Covers:', 'Depends on:', 'Owns:', 'Do:', 'Tests:', 'Done when:']
ID = r'[A-Z]+\d+(?:\.\d+)?(?:[a-z](?!\d))?(?:r\d+)?(?:[a-z](?!\d))?'   # B4.6, B4.6a, B4.6r1, B4.6ar1, S1, H2.1 — the split letter never eats the r of r<k>; the same pattern in every tool
HEAD = re.compile(r'^### (' + ID + r') — (.+)$', re.M)

COVERS = re.compile(r'^(—|-|R-[A-Z][A-Z0-9]*-\d{2,3}(\s*,\s*R-[A-Z][A-Z0-9]*-\d{2,3})*)$')
RESERVED = {'M', 'P', 'R'}

def tasks_in(text):
    parts = HEAD.split(text)
    out = []
    for i in range(1, len(parts), 3):
        tid, title, body = parts[i], parts[i+1], parts[i+2]
        body = re.split(r'^## ', body, flags=re.M)[0]
        out.append((tid, title, body))
    return out

def field_text(body, label, lines=False):
    """Inline text of a field plus its following bullet/continuation lines ('' if empty);
    with lines=True the raw lines instead."""
    body_lines = body.splitlines()
    for i, l in enumerate(body_lines):
        if re.match(r'^\s*' + re.escape(label), l):
            parts = [l.split(':', 1)[1].strip()]
            for n in body_lines[i + 1:]:
                if any(re.match(r'^\s*' + re.escape(f), n) for f in FIELDS + ['Covers:']) or n.startswith('#') or re.match(r'^\s*- \[[ xX]\]', n):
                    break
                parts.append(n if lines else n.strip())
            return parts if lines else ' '.join(p for p in parts if p).strip()
    return [] if lines else ''

def main(plan_dir):
    P = pathlib.Path(plan_dir)
    if not P.is_dir():
        sys.exit(f'plan directory not found: {plan_dir}\n\n{__doc__}')
    ok = True
    track_files = sorted(list(P.glob('[0-9][0-9]-*-track.md')) + list(P.glob('03-*.md')))
    if not track_files:
        print(f'no track files (NN-*-track.md / 03-*.md) in {plan_dir}\n\nRESULT: FAIL')
        return 1
    defined = set(); deps = {}
    # 1. field completeness
    print('== field completeness ==')
    total = 0; bad = 0
    for f in track_files:
        for tid, title, body in tasks_in(f.read_text()):
            total += 1; defined.add(tid)
            missing = [fl for fl in FIELDS if not re.search(r'^\s*' + re.escape(fl), body, re.M)]
            empty = [fl for fl in FIELDS if fl not in missing and not field_text(body, fl)]
            problems = []
            if missing:
                problems.append('missing: ' + ', '.join(m.rstrip(':') for m in missing))
            if empty:
                problems.append('empty: ' + ', '.join(e.rstrip(':') for e in empty))
            if 'Covers:' in FIELDS and 'Covers:' not in missing and not COVERS.match(field_text(body, 'Covers:')):
                problems.append(f'Covers must be — or R-ids, got {field_text(body, "Covers:")!r}')
            dep_text = re.sub(r'`[^`]*`', '', field_text(body, 'Depends on:'))      # backticked ids are mentions, not dependencies
            deps[tid] = [d for d in re.findall(r'\b' + ID + r'\b', dep_text)
                         if d != tid and re.match(r'[A-Z]+', d).group(0) not in RESERVED]   # P1 (a phase/slice), M3 (a milestone) are context, not tasks
            if problems:
                bad += 1; ok = False
                print(f'  {f.name:34} {tid:8} ' + ' · '.join(problems))
    print(f'  tasks: {total}, incomplete: {bad}')
    if total == 0:
        ok = False; print('  no task headings `### <ID> — <title>` found')
    reserved = sorted({re.match(r'[A-Z]+', t).group(0) for t in defined} & RESERVED)
    if reserved:
        ok = False; print(f'  track letters collide with reserved ids (M milestones, P phases, R requirements): {reserved}')
    # 1b. dependencies: defined, acyclic
    print('== dependencies ==')
    undefined_deps = sorted({f'{t} -> {d}' for t, ds in deps.items() for d in ds if d not in defined})
    if undefined_deps:
        ok = False; print(f'  Depends on undefined ids: {undefined_deps}')
    def cycle_from(start):
        stack, seen = [(start, [start])], set()
        while stack:
            node, path = stack.pop()
            for d in deps.get(node, []):
                if d == start:
                    return path + [d]
                if d not in seen:
                    seen.add(d); stack.append((d, path + [d]))
        return None
    cycles = [c for t in sorted(deps) for c in [cycle_from(t)] if c]
    if cycles:
        ok = False; print(f'  dependency cycles: {[" -> ".join(c) for c in cycles[:5]]}')
    if not undefined_deps and not cycles:
        print('  all defined, no cycles')
    # duplicate task ids across all track files
    seen = {}
    for f in track_files:
        for tid, _, _ in tasks_in(f.read_text()):
            seen.setdefault(tid, []).append(f.name)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    if dups:
        ok = False
        print(f'  DUPLICATE task ids: {dups}')
    # 2. checklist coverage
    print('== checklist coverage ==')
    for f in track_files:
        m = re.match(r'\d\d-(.+?)-track\.md', f.name)
        if not m:  # contract package file: its tasks are checked in the backend checklist
            continue
        track = m.group(1)
        cl = P / 'checklists' / f'{track}-checklist.md'
        if not cl.exists():
            ok = False; print(f'  {cl.name} missing'); continue
        t_ids = {t for t, _, _ in tasks_in(f.read_text())}
        c_ids = set(re.findall(r'^#{2,3} (' + ID + r') — ', cl.read_text(), re.M))
        miss, extra = sorted(t_ids - c_ids), sorted(c_ids - t_ids - defined)
        if miss or extra:
            ok = False
        print(f'  {track:10} track={len(t_ids)} checklist={len(c_ids)} missing={miss} extra={extra}')
    # contract-package tasks (03-*.md) must appear in some checklist
    for f in P.glob('03-*.md'):
        t_ids = {t for t, _, _ in tasks_in(f.read_text())}
        all_cl = '\n'.join(p.read_text() for p in (P / 'checklists').glob('*-checklist.md'))
        miss = sorted(t for t in t_ids if not re.search(r'^#{2,3} ' + re.escape(t) + r' — ', all_cl, re.M))
        if miss:
            ok = False
        print(f'  {f.name:10} contract tasks={len(t_ids)} missing in checklists={miss}')
    # 3. dangling references
    print('== dangling task references ==')
    all_text = '\n'.join(p.read_text() for p in P.rglob('*.md'))
    prose = re.sub(r'`[^`\n]*`', '', all_text)          # ids inside backticks are examples (02 Step 5), not references
    refs = set(re.findall(r'\b([A-Z]+\d+\.\d+(?:[a-z](?!\d))?(?:r\d+)?(?:[a-z](?!\d))?)\b', prose))
    letters = {re.match(r'[A-Z]+', t).group(0) for t in defined}
    # only ids whose letter prefix is a defined track prefix count; spec milestones (M0.1 …) and
    # plan phases (P0 …) are not task ids; follow-up suffixes must be defined too
    dangling = sorted(r for r in refs if re.match(r'[A-Z]+', r).group(0) in letters and r not in defined)
    if dangling:
        print(f'  undefined ids referenced: {dangling}'); ok = False
    else:
        print('  none')
    # 4. phrasing
    print('== thinking-aloud phrasing ==')
    hits = []                                   # only inside Do: blocks — decision notes elsewhere may legitimately start with "No —"
    for f in track_files:
        for tid, _, body in tasks_in(f.read_text()):
            for l in field_text(body, 'Do:', lines=True):
                if re.search(r'\? No\b|^\s*(?:[-*]\s*)?No(?: —|:)\s', l):
                    hits.append((f.name, tid, l.strip()[:60]))
    if hits:
        ok = False; print(f'  {hits}')
    else:
        print('  none')
    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print(__doc__); sys.exit(0)
    args = [a for a in sys.argv[1:] if a != '--no-covers']
    if '--no-covers' in sys.argv[1:]:
        FIELDS.remove('Covers:')
    sys.exit(main(args[0] if args else 'ai-workspace/plan'))
