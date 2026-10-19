#!/usr/bin/env python3
"""Generate per-track checklists from the track files, so every Do / Tests / Done-when
line is exactly one tick-box and the checklist can never drift from the plan.

Usage:  python3 -I ai-workspace/instructions/tools/checklist-gen.py ai-workspace/plan [--check]

For each `NN-<track>-track.md` (plus `03-*.md`, whose tasks are appended to the backend
checklist) it writes `checklists/<track>-checklist.md`:
  * PREAMBLE: everything in the existing checklist file above its first task block or
    first `## Phase` heading is kept verbatim (hand-written cross-cutting boxes such as a
    budget section live there). If the file does not exist, a default header is written.
  * BODY (generated): one `## <phase heading>` per `## ` section of the track file that
    contains tasks, then one `### <id> — <title>` block per task with:
      - [ ] <each Do bullet>
      - [ ] Test: <each Tests item>
      - [ ] Done: <each Done-when item>
    A field written inline (`Tests: (int) a; b`) is split on "; " into separate boxes.
  * A generated-marker line so humans know not to edit the body by hand.
  * Ticks survive regeneration: a box whose (task id, text) was `- [x]` before stays ticked;
    a box whose text changed in the track file comes back unticked (it must be re-verified).
  * Implementers may append a note to a box after ' — ' (em dash with spaces); the note and the
    tick are preserved as long as the box text before the separator still matches.
  * Roll-up tick lists (`- [ ] B1.1 …`) and prose after a task block are not boxes: put the
    tick list under its own `## Tick list` heading (02 Step 5).
  * Optional `ai-workspace/plan/tools.json` key "contract_track" names the track whose checklist
    receives the `03-*.md` contract-package tasks (default "backend").
`--check` exits 1 if any generated file differs from what is on disk (use in review); it
writes nothing. Without a plan argument it uses ai-workspace/plan; `-h` prints this text.
"""
import re, sys, json, pathlib

ID = r'[A-Z]+\d+(?:\.\d+)?(?:[a-z](?!\d))?(?:r\d+)?(?:[a-z](?!\d))?'   # the same pattern in every tool (plan-audit, checklist-audit, trace-audit)
HEAD = re.compile(r'^### (' + ID + r') — (.+)$', re.M)
FIELDS = ['Spec:', 'Covers:', 'Depends on:', 'Owns:', 'Do:', 'Tests:', 'Done when:']
MARK = '<!-- GENERATED BELOW by instructions/tools/checklist-gen.py — edit the track file, not this body -->'

def load_cfg(start):
    """Optional ai-workspace/plan/tools.json (02 Step 0): e.g. "contract_track" (default backend)."""
    for d in [pathlib.Path(start)] + list(pathlib.Path(start).resolve().parents):
        for c in (d / 'tools.json', d / 'ai-workspace' / 'plan' / 'tools.json'):
            if c.is_file():
                try:
                    return json.loads(c.read_text())
                except json.JSONDecodeError as e:
                    sys.exit(f'{c}: invalid JSON ({e})')
    return {}

def field_items(body, label):
    """Return the list of items for a field: inline text split on '; ' plus following '- ' bullets.
    Collection stops at the next field, a heading, a tick-box line (`- [ ]` roll-up lists), or a
    blank line followed by an unindented non-bullet line (prose after the task block)."""
    lines = body.splitlines()
    out, i = [], 0
    while i < len(lines):
        if re.match(r'^\s*' + re.escape(label), lines[i]):
            inline = lines[i].split(':', 1)[1].strip()
            if inline:
                out += [s.strip() for s in re.split(r';\s+', inline) if s.strip()]
            i += 1
            prev_blank = False
            while i < len(lines):
                l = lines[i]
                if any(re.match(r'^\s*' + re.escape(f), l) for f in FIELDS) or l.startswith('#'):
                    break
                if re.match(r'^\s*- \[[ xX]\]', l):
                    break
                if prev_blank and l.strip() and not l[0].isspace() and not re.match(r'^[-*] ', l):
                    break
                prev_blank = not l.strip()
                m = re.match(r'^\s*[-*] (.+)$', l)
                if m:
                    out.append(m.group(1).strip())
                elif out and l.strip():            # continuation line of the previous bullet
                    out[-1] += ' ' + l.strip()
                i += 1
            break
        i += 1
    return out

def tasks_by_phase(text):
    """Yield (phase_heading, [(id, title, body), ...]) for each '## ' section with tasks."""
    sections = re.split(r'^(## .+)$', text, flags=re.M)
    result = []
    for i in range(1, len(sections), 2):
        heading, content = sections[i].lstrip('# ').strip(), sections[i+1]
        parts = HEAD.split(content)
        tasks = [(parts[j], parts[j+1].strip(), parts[j+2]) for j in range(1, len(parts), 3)]
        if tasks:
            result.append((heading, tasks))
    return result

NOTE_SEP = ' — '

def ticked_lines(path):
    """Existing boxes per task id: {tid: [(ticked, full_text), ...]}, so regeneration keeps ticks
    and any note an implementer appended after ' — ' (e.g. why a box is still open)."""
    if not path.exists():
        return {}
    boxes, tid = {}, None
    for line in path.read_text().splitlines():
        m = re.match(r'^#{2,3} (' + ID + r') — ', line)
        if m:
            tid = m.group(1)
        m = re.match(r'^- \[([ xX])\] (.+)$', line)
        if m:
            boxes.setdefault(tid, []).append((m.group(1) in 'xX', m.group(2)))
    return boxes

def render(track, phases, preamble, done=None):
    done = done or {}
    out = [preamble.rstrip('\n'), '', MARK, '']
    def box(tid, text):
        for ticked, full in done.get(tid, []):
            if full == text or full.startswith(text + NOTE_SEP):
                return f'- [{"x" if ticked else " "}] {full}'
        return f'- [ ] {text}'
    for heading, tasks in phases:
        out.append(f'## {heading}')
        out.append('')
        for tid, title, body in tasks:
            out.append(f'### {tid} — {title}')
            for item in field_items(body, 'Do:'):
                out.append(box(tid, item))
            for item in field_items(body, 'Tests:'):
                out.append(box(tid, f'Test: {item}'))
            for item in field_items(body, 'Done when:'):
                out.append(box(tid, f'Done: {item}'))
            out.append('')
    return '\n'.join(out).rstrip('\n') + '\n'

def preamble_of(path, track):
    if path.exists():
        text = path.read_text()
        cut = len(text)
        for pat in (r'^#{2,3} ' + ID + r' — ', r'^## Phase', re.escape(MARK)):
            m = re.search(pat, text, re.M)
            if m:
                cut = min(cut, m.start())
        return text[:cut]
    return (f'# {track.capitalize()} track checklist\n\n'
            'Tick in the same commit as the work. One block per task; one box per `Do:` / `Tests:` / '
            '`Done when:` item of the track file. The universal checklist applies on top.\n')

def main(argv):
    if any(a in ('-h', '--help') for a in argv[1:]):
        print(__doc__); return 0
    plan = pathlib.Path(argv[1] if len(argv) > 1 and not argv[1].startswith('--') else 'ai-workspace/plan')
    check = '--check' in argv
    if not plan.is_dir():
        sys.exit(f'plan directory not found: {plan}\n\n{__doc__}')
    cl_dir = plan / 'checklists'
    groups = {}
    for f in sorted(plan.glob('[0-9][0-9]-*-track.md')):
        track = re.match(r'\d\d-(.+?)-track\.md', f.name).group(1)
        groups.setdefault(track, []).extend(tasks_by_phase(f.read_text()))
    contract_track = load_cfg(plan).get('contract_track', 'backend')
    for f in sorted(plan.glob('03-*.md')):           # contract package tasks → the contract owner's checklist
        groups.setdefault(contract_track, [])[:0] = tasks_by_phase(f.read_text())
    if not groups:
        sys.exit(f'no track files (NN-<track>-track.md) in {plan}')
    if not check:
        cl_dir.mkdir(exist_ok=True)
    rc = 0
    for track, phases in groups.items():
        path = cl_dir / f'{track}-checklist.md'
        text = render(track, phases, preamble_of(path, track), ticked_lines(path))
        n = len(re.findall(r'^- \[[ xX]\]', text, re.M))
        if check:
            same = path.exists() and path.read_text() == text
            print(f'{path.name}: {"up to date" if same else "STALE"} ({n} boxes)')
            rc |= 0 if same else 1
        else:
            path.write_text(text)
            print(f'wrote {path.name}: {sum(len(t) for _, t in phases)} tasks, {n} boxes')
    return rc

if __name__ == '__main__':
    sys.exit(main(sys.argv))
