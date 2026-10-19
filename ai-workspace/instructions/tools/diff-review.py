#!/usr/bin/env python3
"""Mechanical pre-merge review of an agent's branch — run by the integrator before every merge.

Usage:
  python3 -I ai-workspace/instructions/tools/diff-review.py --range <base>...<branch> \\
          --owned '<regex of paths the task may touch>' [--max-lines 300] [--repo .]
  python3 -I ai-workspace/instructions/tools/diff-review.py --diff <file.diff> \\
          --tree <checkout with the branch's files> --owned '<regex>'

Reports (exit 1 only for a possible secret; otherwise it never blocks — the integrator decides):
  1. files changed, added, deleted or renamed OUTSIDE the owned paths (cross-track edits need a
     reason or a ruling) — paths come from the `diff --git` headers, so deletions and renames count;
  2. added lines with banned patterns: `any` types, lint/type suppressions (TS, Python, Go, Rust,
     Java), TODO/FIXME;
  3. hard-coded third-party API hosts in added lines (fine in adapters, suspicious elsewhere);
  4. changed source files longer than --max-lines (tests excluded);
  5. new dependencies: added entries inside the dependency sections of package.json, pyproject.toml
     (PEP 621 lists, optional-dependencies, poetry, dependency-groups), requirements*.txt, Pipfile,
     go.mod, Cargo.toml, Gemfile, pom.xml, build.gradle(.kts) — each needs a reason, a licence and
     a maintenance check (05 "Boundaries");
  6. POSSIBLE SECRETS in added lines (API keys, private keys, tokens) — exit 1; never merge or push.
     A known fake (a test fixture) is marked on its own line with `secret-scan: allow <reason>`
     (or matched by "secret_allow" in tools.json); allowed hits are printed separately and each
     needs a DECISIONS line.
Dependency detection reads the branch's full manifest (git show / the --tree copy), so an entry
added far below its section header is still found.
Optional `ai-workspace/plan/tools.json` keys (02 Step 0) extend the defaults for the stack:
  "banned" (list of regexes), "host_hints" (regex), "source_ext" (regex on file names),
  "test_file" (regex), "secret_patterns" (list of regexes), "secret_allow" (list of regexes).
Pre-push hook (02 Step 5), robust to a branch without an upstream (first push):
  base=$(git rev-parse -q --verify '@{u}' || git merge-base HEAD <integration branch>) &&
  python3 -I ai-workspace/instructions/tools/diff-review.py --range "$base...HEAD" --owned '.*' || exit 1
A git failure (unknown range, no such branch) exits 2 with git's message, never a traceback.
`--range` runs `git diff --no-color --no-ext-diff -M --src-prefix=a/ --dst-prefix=b/` so a user's
diff.noprefix or external-diff settings cannot hide files.
"""
import re, sys, json, subprocess, pathlib

DEFAULTS = {
    'banned': [r':\s*any\b', r'\bas any\b', r'eslint-disable', r'@ts-ignore', r'@ts-nocheck', r'\bTODO\b', r'\bFIXME\b',
               r'#\s*type:\s*ignore', r'#\s*noqa\b', r'//\s*nolint', r'#\[allow\(', r'@SuppressWarnings', r'\bpragma:\s*no cover'],
    'host_hints': r'https?://[^\s\'"]*(api\.|\.ai/|\.io/v\d)',
    'source_ext': r'\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|kts|rb|swift|cs|php|ex|exs)$',
    'test_file': r'(test|spec|__tests__|fixtures?)',
    'secret_patterns': [r'\bsk-[A-Za-z0-9_-]{20,}', r'\bAKIA[0-9A-Z]{16}\b', r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
                        r'\bxox[abpor]-[A-Za-z0-9-]{10,}', r'\bghp_[A-Za-z0-9]{36}\b', r'\bAIza[0-9A-Za-z_-]{35}\b',
                        r'\bsk_(live|test)_[A-Za-z0-9]{20,}', r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\'"][A-Za-z0-9/+_-]{16,}[\'"]'],
}
ALLOW_MARK = re.compile(r'secret-scan:\s*allow\b')     # inline marker for a known fake (test fixture), with a reason after it
MANIFEST = re.compile(r'(^|/)(package\.json|pyproject\.toml|requirements[^/]*\.txt|Pipfile|go\.mod|Cargo\.toml|Gemfile|pom\.xml|build\.gradle(\.kts)?)$')
NOT_DEP_KEYS = {'name', 'version', 'description', 'main', 'module', 'types', 'typings', 'scripts', 'packageManager', 'license',
                'private', 'type', 'exports', 'engines', 'node', 'npm', 'pnpm', 'yarn', 'files', 'bin', 'repository', 'author',
                'homepage', 'bugs', 'keywords', 'workspaces', 'browserslist', 'sideEffects', 'publishConfig'}

def load_cfg(*starts):
    """Optional ai-workspace/plan/tools.json (02 Step 0) with stack-specific patterns; {} otherwise."""
    for s in starts:
        for d in [pathlib.Path(s)] + list(pathlib.Path(s).resolve().parents):
            for c in (d / 'tools.json', d / 'ai-workspace' / 'plan' / 'tools.json'):
                if c.is_file():
                    try:
                        return json.loads(c.read_text())
                    except json.JSONDecodeError as e:
                        sys.exit(f'{c}: invalid JSON ({e})')
    return {}

def args(argv):
    if not argv or len(argv) % 2 or any(k in ('-h', '--help') for k in argv):
        print(__doc__); sys.exit(0 if any(k in ('-h', '--help') for k in argv) else 2)
    a = {'--max-lines': '300', '--repo': '.'}
    it = iter(argv)
    for k in it:
        a[k] = next(it)
    if not a['--max-lines'].isdigit():
        print('--max-lines needs an integer', file=sys.stderr); sys.exit(2)
    return a

def file_events(diff):
    """[(path_after_or_before, kind)] from the diff headers: kind in modified/added/deleted/renamed."""
    events, binaries = [], []
    blocks = re.split(r'^(?=diff --git )', diff, flags=re.M)
    for b in blocks:
        m = re.match(r'diff --git a/(.+?) b/(.+?)\n', b)
        if not m:
            continue
        a_path, b_path = m.group(1), m.group(2)
        if re.search(r'^deleted file mode', b, re.M):
            kind, path = 'deleted', a_path
        elif re.search(r'^new file mode', b, re.M):
            kind, path = 'added', b_path
        elif re.search(r'^rename from ', b, re.M):
            kind, path = 'renamed', f'{a_path} -> {b_path}'
        else:
            kind, path = 'modified', b_path
        if re.search(r'^Binary files ', b, re.M):
            binaries.append((path, kind))
        else:
            events.append((path, kind))
    if not blocks[0].startswith('diff --git') and not events and not binaries:   # headerless diff (--diff mode with a hand-made file)
        for p in re.findall(r'^\+\+\+ b/(.+)$', diff, re.M):
            events.append((p, 'modified'))
        for p in re.findall(r'^--- a/(.+)\n\+\+\+ /dev/null', diff, re.M):
            events.append((p, 'deleted'))
    return events, binaries

def dependency_entries(text, name):
    """Every dependency entry in a FULL manifest file (state machine per ecosystem, see docstring 5).
    Working on the full file, not the hunk, so a section header far above the change still counts."""
    out, state = set(), {}
    for raw in text.splitlines():
        s = raw.strip()
        hit = None
        if name == 'package.json':
            if re.match(r'"(dependencies|devDependencies|peerDependencies|optionalDependencies)"\s*:\s*\{', s):
                state['in'] = True
            elif s.startswith('}'):
                state['in'] = False
            else:
                m = re.match(r'"([^"]+)"\s*:\s*"([^"]*)"', s)
                if m and m.group(1) not in NOT_DEP_KEYS and (state.get('in') or re.match(r'^([~^><=]*\d|\*$|latest$|(workspace|npm|file|link|git|github|https?):)', m.group(2))):
                    hit = m.group(0)
        elif name == 'pyproject.toml':
            if re.match(r'dependencies\s*=\s*\[', s):
                state['list'] = not s.rstrip().endswith(']')
                for e in re.findall(r'"([^"]+)"', s.split('[', 1)[1]):
                    out.add(e)
            elif state.get('list'):
                if s.startswith(']'):
                    state['list'] = False
                elif s.startswith('"') or s.startswith("'"):
                    hit = s.strip('",\' ')
            elif s.startswith('['):
                state['table'] = bool(re.match(r'\[(project\.optional-dependencies|tool\.poetry\.(group\.\w+\.)?(dev-)?dependencies|dependency-groups)\]', s))
            elif state.get('table') and re.match(r'[A-Za-z0-9_.\-]+\s*=\s*\[', s):
                state['list'] = not s.rstrip().endswith(']')        # a multi-line extra/group list: dev = [ … ]
                for e in re.findall(r'"([^"]+)"', s.split('[', 1)[1]):
                    out.add(e)
            elif state.get('table') and re.match(r'[A-Za-z0-9_.\-]+\s*=', s):
                hit = s
        elif name.startswith('requirements') or name == 'Pipfile':
            if name == 'Pipfile':
                if s.startswith('['):
                    state['table'] = bool(re.match(r'\[(dev-)?packages\]', s))
                elif state.get('table') and re.match(r'[A-Za-z0-9_.\-"]+\s*=', s):
                    hit = s
            elif s and not s.startswith(('#', '-')):
                hit = s
        elif name == 'go.mod':
            if re.match(r'require\s*\(', s):
                state['block'] = True
            elif s.startswith(')'):
                state['block'] = False
            elif re.match(r'require\s+\S+\s+v', s) or (state.get('block') and re.match(r'\S+\s+v\d', s)):
                hit = s
        elif name == 'Cargo.toml':
            if s.startswith('['):
                state['table'] = bool(re.match(r'\[(workspace\.)?(dev-|build-)?dependencies\]|\[target\..*dependencies\]', s))
            elif state.get('table') and re.match(r'[A-Za-z0-9_\-]+\s*=', s):
                hit = s
        elif name == 'Gemfile':
            if re.match(r'gem\s+[\'"]', s):
                hit = s
        elif name == 'pom.xml':
            if '<dependency>' in s:
                state['dep'] = True
            elif '</dependency>' in s:
                state['dep'] = False
            elif state.get('dep') and '<artifactId>' in s:
                hit = s
        elif name.startswith('build.gradle'):
            if re.match(r'(implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly|kapt|annotationProcessor|ksp)\b', s):
                hit = s
        if hit:
            out.add(hit)
    return out

def new_dependencies(diff, full_text_of):
    """Added lines of manifest files that are dependency entries of the file's branch version."""
    out, path, entries = [], None, set()
    for line in diff.splitlines():
        if line.startswith('diff --git ') or line.startswith('+++ '):
            m = re.match(r'(?:diff --git a/.+? b/|\+\+\+ b/)(.+)$', line)
            path = m.group(1) if m and MANIFEST.search(m.group(1)) else None
            entries = dependency_entries(full_text_of(path), pathlib.PurePosixPath(path).name) if path else set()
            continue
        if path and line.startswith('+') and not line.startswith('+++'):
            s = line[1:].strip()
            for e in sorted(entries, key=len, reverse=True):
                if s and (e == s or e in s):
                    out.append(f'{path}: {e[:120]}'); break
    return out

def main(argv):
    a = args(argv)
    cfg = load_cfg(a.get('--repo', '.'), a.get('--tree', '.'))
    banned = [re.compile(b) for b in DEFAULTS['banned'] + cfg.get('banned', [])]
    hosts = re.compile(cfg.get('host_hints', DEFAULTS['host_hints']))
    source = re.compile(cfg.get('source_ext', DEFAULTS['source_ext']))
    testish = re.compile(cfg.get('test_file', DEFAULTS['test_file']), re.I)
    secrets = [re.compile(s) for s in DEFAULTS['secret_patterns'] + cfg.get('secret_patterns', [])]
    owned = re.compile(a.get('--owned', '.*'))
    if '--range' in a:
        cmd = ['git', '-C', a['--repo'], 'diff', '--no-color', '--no-ext-diff', '-M', '--src-prefix=a/', '--dst-prefix=b/', a['--range']]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f'git diff failed for {a["--range"]!r}: {r.stderr.strip()}', file=sys.stderr); sys.exit(2)
        diff = r.stdout
        branch = a['--range'].split('...')[-1].split('..')[-1]
        def full_text(path):
            r = subprocess.run(['git', '-C', a['--repo'], 'show', f'{branch}:{path}'], capture_output=True, text=True)
            return r.stdout if r.returncode == 0 else ''
    elif '--diff' in a:
        diff = pathlib.Path(a['--diff']).read_text()
        tree = pathlib.Path(a.get('--tree', '.'))
        def full_text(path):
            p = tree / path
            return p.read_text(errors='ignore') if p.exists() else ''
    else:
        print(__doc__); sys.exit(2)
    events, binaries = file_events(diff)
    added_lines = [l[1:] for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++')]
    print(f'files: {len(events)} text + {len(binaries)} binary '
          f'({sum(1 for _, k in events if k == "added")} added, {sum(1 for _, k in events if k == "deleted")} deleted, {sum(1 for _, k in events if k == "renamed")} renamed)')
    print('--- outside owned paths ---')
    for path, kind in events + binaries:
        if not all(owned.search(p) for p in path.split(' -> ')):
            print(f'   {kind}: {path}')
    print('--- banned patterns in added lines ---')
    for line in added_lines:
        if any(b.search(line) for b in banned):
            print('  ', line.strip()[:160])
    print('--- third-party hosts in added lines (fine in adapters, suspicious elsewhere) ---')
    for line in added_lines:
        if hosts.search(line):
            print('  ', line.strip()[:160])
    print(f'--- source files over {a["--max-lines"]} lines (tests excluded) ---')
    for path, kind in events:
        f = path.split(' -> ')[-1]
        if kind != 'deleted' and source.search(f) and not testish.search(f):
            n = len(full_text(f).splitlines())
            if n > int(a['--max-lines']):
                print('  ', n, f)
    print('--- new dependencies (check licence, maintenance, need — 05 "Boundaries") ---')
    for d in new_dependencies(diff, full_text):
        print('  ', d)
    allow = [re.compile(s) for s in cfg.get('secret_allow', [])]
    leaks, allowed = [], []
    for line in added_lines:
        if any(s.search(line) for s in secrets):
            (allowed if ALLOW_MARK.search(line) or any(x.search(line) for x in allow) else leaks).append(line.strip()[:80] + ' …')
    print('--- POSSIBLE SECRETS in added lines (S1: never commit, rotate if real) ---')
    for l in leaks:
        print('  ', l)
    if allowed:
        print('--- secret-pattern hits marked allowed (each needs a DECISIONS line naming the fixture) ---')
        for l in allowed:
            print('  ', l)
    sys.exit(1 if leaks else 0)

if __name__ == '__main__':
    main(sys.argv[1:])
