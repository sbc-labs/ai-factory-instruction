#!/usr/bin/env python3
"""Performance budget check: latest gate vs budget and vs the previous gate. Run at every gate.

Usage:  python3 -I ai-workspace/instructions/tools/perf-compare.py docs/perf.csv [--threshold 10]

docs/perf.csv (one row per metric per gate; append-only; header required):
  date,gate,metric,value,unit,budget,direction,notes
  2026-10-12,P3,api.items.list.p95,84,ms,200,lower,median of 3 runs; mock mode
  2026-10-12,P3,worker.render.peak_mem,2289,MB,2600,lower,cgroup anon peak
  2026-10-12,P3,web.bundle.initial,182,kB,250,lower,
  2026-10-12,P3,pipeline.items_per_min,1.6,items/min,1.0,higher,load test 2 workers
`direction` is exactly `lower` (smaller is better) or `higher`. `budget` may be empty (tracked
only). A budget may change — or be removed — between gates only with a recorded ruling: the new
row's notes must contain `ruling <YYYY-MM-DD>` (the decisions log holds the reason).
A metric is retired (a feature removed by a CR) with a row whose value is `retired` and whose
notes contain `ruling <YYYY-MM-DD>`: it is not compared and not expected at later gates;
measuring it again later is a failure.

Exit 1 (gate fails) on any of:
  1. OVER BUDGET — latest value worse than the budget;
  2. BUDGET CHANGED without `ruling <date>` in the notes — a silently loosened gate;
  3. a metric measured at the previous gate but missing now — a silently dropped measurement.
Printed but not failing (investigate before tagging; host noise is a reason to re-measure,
not to ignore): REGRESSION — latest value worse than the previous gate's by more than
--threshold percent (default 10); any worsening from a previous value of 0 is a regression.
Exit 2 on unusable input (unknown direction, non-numeric value or budget, missing columns),
naming the row.
"""
import csv, re, sys, pathlib

COLS = ['date', 'gate', 'metric', 'value', 'unit', 'budget', 'direction', 'notes']
RULING = re.compile(r'\bruling \d{4}-\d{2}-\d{2}\b')     # "ruling 2026-10-12 …" — the decisions log holds the reason

def die(msg, code=2):
    print(msg, file=sys.stderr); sys.exit(code)

def worse(a, b, direction):
    return a > b if direction == 'lower' else a < b

def num(text, what, row_no):
    try:
        return float(text)
    except ValueError:
        die(f'row {row_no}: {what} {text!r} is not a number')

def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__); sys.exit(0)
    path = pathlib.Path(argv[0])
    threshold = 10.0
    if '--threshold' in argv:
        i = argv.index('--threshold')
        if i + 1 >= len(argv) or not re.fullmatch(r'\d+(\.\d+)?', argv[i + 1]):
            die('--threshold needs a number (percent)')
        threshold = float(argv[i + 1])
    if not path.is_file():
        die(f'{path} not found')
    reader = csv.DictReader(path.read_text().splitlines())
    if not reader.fieldnames or [c.strip() for c in reader.fieldnames] != COLS:
        die(f'{path}: header must be {",".join(COLS)}')
    rows = []
    for i, r in enumerate(reader, start=2):
        r = {k: (v or '').strip() for k, v in r.items()}
        if r['direction'] not in ('lower', 'higher'):
            die(f'row {i}: direction must be exactly "lower" or "higher", got {r["direction"]!r}')
        r['_retired'] = r['value'] == 'retired'
        if r['_retired']:
            if not RULING.search(r['notes']):
                die(f'row {i}: a retired metric needs "ruling <YYYY-MM-DD>" in its notes')
            r['_v'] = None; r['_b'] = None; rows.append(r); continue
        r['_v'] = num(r['value'], 'value', i)
        r['_b'] = num(r['budget'], 'budget', i) if r['budget'] else None
        rows.append(r)
    if not rows:
        die('no rows in ' + str(path))
    gates = []
    for r in rows:
        if r['gate'] not in gates:
            gates.append(r['gate'])
    latest, prev = gates[-1], (gates[-2] if len(gates) > 1 else None)
    by = lambda g: {r['metric']: r for r in rows if r['gate'] == g}
    cur, old = by(latest), (by(prev) if prev else {})
    print(f'latest gate {latest}' + (f' vs {prev}' if prev else ' (no previous gate)') + f' · threshold {threshold}%')
    failures = []
    retired = {r['metric'] for r in rows if r['_retired']}
    for m, r in sorted(cur.items()):
        if r['_retired']:
            print(f'  {m}: retired ({r["notes"]})'); continue
        if m in retired:
            failures.append(f'{m} measured again after being retired'); print(f'  {m}: <-- RETIRED EARLIER, measured again'); continue
        v, d = r['_v'], r['direction']
        line = f'  {m}: {r["value"]} {r["unit"]}'
        if r['_b'] is not None:
            line += f' (budget {r["budget"]})'
            if worse(v, r['_b'], d):
                failures.append(f'{m} over budget'); line += '  <-- OVER BUDGET'
        if m in old and not old[m]['_retired']:
            o = old[m]
            if o['_b'] is not None and o['_b'] != r['_b'] and not RULING.search(r['notes']):
                failures.append(f'{m} budget changed {o["budget"]} -> {r["budget"] or "(none)"} without a ruling')
                line += f'  <-- BUDGET CHANGED {o["budget"]} -> {r["budget"] or "(none)"} (no "ruling <YYYY-MM-DD>" in notes)'
            pv = o['_v']
            if worse(v, pv, d) and (pv == 0 or abs(v - pv) / abs(pv) * 100 > threshold):
                pct = f'{(v - pv) / abs(pv) * 100:+.0f}%' if pv else 'from 0'
                line += f'  <-- REGRESSION vs {o["value"]} ({pct})'
        print(line)
    dropped = sorted(set(old) - set(cur) - retired)
    if dropped:
        print('--- measured at the previous gate but missing now (a dropped measurement fails the gate):')
        for m in dropped:
            print('  ', m); failures.append(f'{m} not measured')
    if failures:
        print('FAIL: ' + '; '.join(failures))
    sys.exit(1 if failures else 0)

if __name__ == '__main__':
    main(sys.argv[1:])
