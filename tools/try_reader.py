"""Runs the readers for a few companies and prints what each site answered. Saves nothing.

    python tools/try_reader.py Nestlé Deloitte
"""

import collections
import datetime
import sys
import tomllib

sys.path.insert(0, ".")
from tracker import boards, text  # noqa: E402

real_fetch = text.fetch


def logged_fetch(url, *args, **kwargs):
    body = real_fetch(url, *args, **kwargs)
    print(f"  {len(body):>8} bytes  {url[:160]}")
    return body


text.fetch = logged_fetch
today = datetime.datetime.now(datetime.timezone.utc).date()
since = (today - datetime.timedelta(days=1)).isoformat()
with open("companies.toml", "rb") as f:
    companies = {c["name"]: c for c in tomllib.load(f)["company"]}
for name in sys.argv[1:]:
    cfg = companies[name]
    print(f"== {name} ({cfg['board']})")
    rows = boards.READERS[cfg["board"]].collect(name, cfg, today, since)
    print(f"{len(rows)} jobs; posted dates: {sorted(collections.Counter(r['posted'] for r in rows).items())[-8:]}")
    for r in rows[:5]:
        print(f"  {r['posted']} | {r['title'][:50]} | {r['location'][:40]} | {r.get('country', '')} | "
              f"{len(r.get('description') or '')} characters")
