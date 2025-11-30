#!/usr/bin/env python
import os
import re
from datetime import datetime

ROOT = os.path.join(os.path.dirname(__file__), '..', 'docs')

STATUS_RE = re.compile(r'<!--\s*status:\s*([a-zA-Z_]+)\s*-->')
STATUS_LINE_RE = re.compile(r'Status:\s*(.*)', re.IGNORECASE)

rows = []

for dirpath, _, filenames in os.walk(ROOT):
    for name in filenames:
        if not name.endswith('.md'):
            continue
        path = os.path.join(dirpath, name)
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding='utf-8') as f:
            text = f.read()
        status = None
        m = STATUS_RE.search(text)
        if m:
            status = m.group(1)
        else:
            for line in text.splitlines()[:10]:
                m2 = STATUS_LINE_RE.search(line)
                if m2:
                    status = m2.group(1).strip()
                    break
        if status is None:
            status = 'unknown'
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        rows.append((rel, status, mtime))

rows.sort(key=lambda r: r[0])

print('| File | Status | Last Modified |')
print('|------|--------|---------------|')
for rel, status, mtime in rows:
    print(f'| {rel} | {status} | {mtime.isoformat(timespec="seconds")} |')

# 상태별 집계
counts = {}
for _, status, _ in rows:
    counts[status] = counts.get(status, 0) + 1

print('\nSummary by status:')
for status, cnt in sorted(counts.items()):
    print(f'- {status}: {cnt}')
