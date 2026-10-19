#!/usr/bin/env python3
"""Resolve merge conflicts in APPEND-ONLY logs by keeping both sides (ours, then theirs).

Usage:  python3 -I ai-workspace/instructions/tools/log-union-resolve.py <file> [<file> ...]
        [--pattern '<regex>']   (default: docs/(PROGRESS|DECISIONS|BLOCKERS)\\.md$|docs/perf\\.csv$,
                                 extended by "log_files" in ai-workspace/plan/tools.json)

Why: every agent appends lines to the same logs (progress, decisions, blockers), so almost
every merge conflicts on them, and the right resolution is always "keep both". Prefer the
`.gitattributes` union driver (01 "Append-only logs") so git does this itself; this tool is
the fallback for conflicts that still appear (e.g. a repo without the attribute yet).

Safety: refuses any file that does not match the pattern, so it can never "resolve" code
(checked for every file before any is changed). It removes conflict-marker lines and, for
diff3/zdiff3 conflicts, the common-ancestor section (`||||||| …` up to `=======`), which is
already contained in the sides. Then `git add` the logs, review `git diff --cached`, and
re-read the tail of each log before committing.
"""
import re, sys, json, pathlib

DEFAULT_PATTERN = r'docs/(PROGRESS|DECISIONS|BLOCKERS)\.md$|docs/perf\.csv$'

def load_cfg(start='.'):
    """Optional ai-workspace/plan/tools.json (02 Step 0): "log_files" = list of regexes for logs
    whose names the spec dictates; they extend the default pattern."""
    for d in [pathlib.Path(start)] + list(pathlib.Path(start).resolve().parents):
        for c in (d / 'tools.json', d / 'ai-workspace' / 'plan' / 'tools.json'):
            if c.is_file():
                try:
                    return json.loads(c.read_text())
                except json.JSONDecodeError as e:
                    sys.exit(f'{c}: invalid JSON ({e})')
    return {}

def main(argv):
    pattern = '|'.join([DEFAULT_PATTERN] + load_cfg().get('log_files', []))
    files = []
    it = iter(argv)
    for a in it:
        if a == '--pattern':
            pattern = next(it)
        else:
            files.append(a)
    if not files or any(f in ('-h', '--help') for f in files):
        print(__doc__); sys.exit(0 if files else 2)
    for f in files:                       # check every file before touching any
        if not re.search(pattern, f):
            sys.exit(f'refusing {f}: not an append-only log (pattern {pattern!r}); nothing changed')
    for f in files:
        p = pathlib.Path(f)
        out, n, base = [], 0, False
        for line in p.read_text().splitlines(keepends=True):
            bare = line.rstrip('\r\n')
            if bare.startswith(('|||||||',)):            # diff3/zdiff3: drop the common-ancestor part
                base = True; n += 1
                continue
            if bare == '=======':
                base = False; n += 1
                continue
            if bare.startswith(('<<<<<<< ', '>>>>>>> ')) or bare in ('<<<<<<<', '>>>>>>>'):
                n += 1
                continue
            if not base:
                out.append(line)
        p.write_text(''.join(out))
        print(f'{f}: removed {n} conflict-marker lines (both sides kept)')

if __name__ == '__main__':
    main(sys.argv[1:])
