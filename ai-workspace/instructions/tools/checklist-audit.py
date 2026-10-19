#!/usr/bin/env python3
"""Checklist audit — finds bookkeeping drift the generator cannot see. Run at every gate.

Usage:  python3 -I ai-workspace/instructions/tools/checklist-audit.py ai-workspace/plan [docs/PROGRESS.md] [--phase P<n>]

`--phase P<n>` (the gate, 04 step 4): every task under a track-file heading that names the phase
(`## Phase P3 …`) must have a progress-log line and a block in a GENERATED checklist with no open
box lacking a ` — ` note; otherwise exit 1. Also exit 1 when no task sits under such a heading
(a typo, or a plan that does not group tasks by phase) and for tasks under headings that name no
phase (they would never be checked). Without it the tool only reports drift on tasks the log
calls done.

Reports:
  1. per track: ticked / total boxes (generated track checklists only; hand-written templates
     such as the universal, phase-gate and phase-review checklists are listed, not counted);
  2. tasks recorded as done in the progress log that still have unticked boxes
     (either a box was forgotten, or the box is honestly open and needs a note after ' — ');
  3. task-summary roll-up lines in the track files (`- [ ] <ID> …` lists) whose tick
     disagrees with the progress log.
A task counts as done when a progress-log line starts with its id (or ids, e.g.
'B6.2 + B6.1r1') followed by ' · ' or ':' — keep that log format (01 "Append-only logs").
Exit 1 (the gate step is binary) when a done task has an open box without a ' — ' note, or a
roll-up line disagrees with the log; prints RESULT: PASS / FAIL.

Why: in the first project the generated checklists were current, but finished tasks kept
open boxes for proven work, and the roll-up lines at the bottom of the track files went
stale for whole phases. Fix what this lists with evidence notes; never tick without proof.
"""
import re, sys, pathlib

ID = r'[A-Z]+\d+(?:\.\d+)?(?:[a-z](?!\d))?(?:r\d+)?(?:[a-z](?!\d))?'   # B4.6, B4.6a, B4.6r1, B4.6ar1 — the split letter never eats the r of r<k>; the same pattern in every tool

def key(tid):
    """Sort key for a task id: letters, then the numeric parts (B4.10 after B4.9)."""
    m = re.match(r'([A-Z]+)(\d+)(?:\.(\d+))?', tid)
    return (m.group(1), int(m.group(2)), int(m.group(3) or 0)) if m else (tid, 0, 0)

def known_ids(P):
    ids = set()
    for f in P.glob('[0-9][0-9]-*.md'):
        ids.update(re.findall(r'^### (' + ID + r') — ', f.read_text(), re.M))
    return ids

def done_ids(progress, known):
    """Ids named before the first ' · ' (or ':') of a log line: 'B6.2 + B6.1r1 · …', and ranges
    'D1.1-D4.2' / 'B4.1–B4.6', expanded to the plan's known ids with the same letter prefix."""
    done = set()
    if not progress.exists():
        return done
    for line in progress.read_text().splitlines():
        m = re.match(r'^-?\s*([^·:]{0,80}?)\s*[·:]', line)
        if not (m and re.match(r'^' + ID, m.group(1))):
            continue
        head = m.group(1)
        for a, b in re.findall(r'(' + ID + r')\s*[-–]\s*(' + ID + r')', head):
            lo, hi = key(a), key(b)
            done.update(k for k in known if key(k)[0] == lo[0] and lo <= key(k) <= hi and 'r' not in k[len(lo[0]):])
        done.update(re.findall(r'(?<![A-Za-z0-9.])(' + ID + r')(?![\w.])', head))
    return done

phase = None

def main(plan_dir, progress_path='docs/PROGRESS.md'):
    P = pathlib.Path(plan_dir)
    if not (P / 'checklists').is_dir():
        sys.exit(f'no checklists/ folder in {plan_dir}\n\n{__doc__}')
    if not pathlib.Path(progress_path).exists():
        print(f'WARNING: {progress_path} not found; every task counts as not done')
    done = done_ids(pathlib.Path(progress_path), known_ids(P))
    print(f'tasks done per {progress_path}: {len(done)}')
    failures = 0
    for cl in sorted((P / 'checklists').glob('*-checklist.md')):
        text = cl.read_text()
        boxes = re.findall(r'^\s*- \[([ xX])\]', text, re.M)
        ticked = sum(1 for b in boxes if b in 'xX')
        if 'GENERATED BELOW' not in text:      # universal / gate / review templates: not progress
            print(f'== {cl.name}: template ({len(boxes)} boxes), not counted')
            continue
        print(f'== {cl.name}: {ticked}/{len(boxes)} ticked')
        for block in re.split(r'^### ', text, flags=re.M)[1:]:
            tid = block.split(' ', 1)[0].strip()
            open_ = [l.strip() for l in block.splitlines() if re.match(r'^\s*- \[ \]', l)]
            if tid in done and open_:
                unexplained = [o for o in open_ if ' — ' not in o]
                failures += len(unexplained)
                print(f'  {tid}: done but {len(open_)} open box(es), {len(unexplained)} without a note')
                for o in open_:
                    print('     ', o[:110])
    print('== roll-up lines that disagree with the progress log')
    for f in sorted(P.glob('[0-9][0-9]-*-track.md')):
        for line in f.read_text().splitlines():
            if re.match(r'^- \[[ xX]\] ' + ID, line):
                for mark, tid in re.findall(r'\[([ xX])\] (' + ID + r')', line):
                    if (mark == ' ') == (tid in done):
                        state = 'unticked but done' if mark == ' ' else 'ticked but not in the log'
                        failures += 1
                        print(f'  {f.name}: {tid} {state}')
    if phase:
        print(f'== phase {phase}: every task under a "## … {phase} …" heading must be done and fully ticked/noted')
        # task blocks come from GENERATED checklists only, file by file, and end at the next heading of
        # any level in that file — never running on into a template checklist or another track's file
        blocks = {}
        for cl in sorted((P / 'checklists').glob('*-checklist.md')):
            text = cl.read_text()
            if 'GENERATED BELOW' not in text:
                continue
            for m in re.finditer(r'^### (' + ID + r') — .*?(?=^#{1,3} |\Z)', text, re.M | re.S):
                blocks.setdefault(m.group(1), m.group(0))
        selected, unphased = 0, []
        for f in sorted(list(P.glob('[0-9][0-9]-*-track.md')) + list(P.glob('03-*.md'))):
            sections = re.split(r'^(## .+)$', f.read_text(), flags=re.M)
            for i in range(1, len(sections), 2):
                heading = sections[i]
                ids = re.findall(r'^### (' + ID + r') — ', sections[i + 1], re.M)
                if ids and not re.search(r'\bP(?:\d+|D)\b', heading):      # a phase name is P<n> or PD, not any P-word (PDF, POST)
                    unphased += [f'{f.name}: {t} (under "{heading.strip("# ")}")' for t in ids]
                if not re.search(r'\b' + re.escape(phase) + r'\b', heading):
                    continue
                for tid in ids:
                    selected += 1; problems = []
                    if tid not in done:
                        problems.append('no progress-log line')
                    if tid not in blocks:
                        problems.append('no checklist block')
                    else:
                        open_ = [l for l in blocks[tid].splitlines() if re.match(r'^\s*- \[ \]', l) and ' — ' not in l]
                        if open_:
                            problems.append(f'{len(open_)} open box(es) without a note')
                    if problems:
                        failures += 1; print(f'  {f.name}: {tid}: ' + '; '.join(problems))
        print(f'  tasks selected for {phase}: {selected}')
        if selected == 0:
            failures += 1; print(f'  no task sits under a heading naming {phase} — track files group tasks under "## Phase P<n> …" headings (02 Step 5)')
        if unphased:
            failures += len(unphased); print('  tasks under a heading that names no phase (never checked by --phase):')
            for u in unphased:
                print('    ', u)
    print(f'\nRESULT: {"PASS" if not failures else f"FAIL ({failures} drift item(s): open boxes without a note, roll-up lines disagreeing with the log, or phase tasks not done)"}')
    return 1 if failures else 0

if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__); sys.exit(0 if argv else 2)
    phase = None
    if '--phase' in argv:
        i = argv.index('--phase')
        if i + 1 >= len(argv) or not re.fullmatch(r'P[A-Z0-9]+', argv[i + 1]):
            print('--phase needs a value like P3 (or PD)', file=sys.stderr); sys.exit(2)
        phase = argv[i + 1]; del argv[i:i + 2]
    sys.exit(main(*argv[:2]))
