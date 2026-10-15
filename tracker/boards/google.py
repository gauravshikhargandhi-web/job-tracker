"""Google careers (google.com/about/careers), the job data embedded in the search page, no key.

US jobs, newest first, 20 a page, descriptions included.
"""

import json
import re
import urllib.parse

from tracker.text import clean, get_text, seconds_day

SEARCH = "https://www.google.com/about/careers/applications/jobs/results"
MAX_PAGES = 200
DATA = re.compile(r"AF_initDataCallback\(\{key: 'ds:1', hash: '\d+', data:(.*?), sideChannel: \{\}\}\);</script>", re.S)


def collect(company, cfg, today=None, since=""):
    rows = {}
    for page_no in range(1, MAX_PAGES + 1):
        params = urllib.parse.urlencode({"location": "United States", "sort_by": "date", "page": page_no})
        match = DATA.search(get_text(f"{SEARCH}?{params}", browser=True))
        if not match:
            if page_no == 1:
                raise ValueError("job data not found in the Google careers page")
            break
        page = [parse(company, j) for j in json.loads(match.group(1))[0] or []]
        for row in page:
            rows[row["key"]] = row
        if not page or (since and all(r["posted"] < since for r in page)):
            break
    return list(rows.values())


def _html(j, i):
    field = j[i] if len(j) > i else None
    return field[1] if isinstance(field, list) and len(field) > 1 and field[1] else ""


def parse(company, j):
    places = j[9] or []
    return {
        "key": f"{company}:go{j[0]}",
        "company": company,
        "title": (j[1] or "").strip(),
        "location": "; ".join(p[0] for p in places if p and p[0]),
        "country": "; ".join(sorted({p[5] for p in places if p and len(p) > 5 and p[5]})),
        "remote": "",
        "department": "",
        "posted": seconds_day(((j[12] if len(j) > 12 else None) or [None])[0]),
        "link": f"{SEARCH}/{j[0]}",
        "board": "google",
        "description": clean("\n".join([_html(j, 10), _html(j, 3), _html(j, 4), _html(j, 19)])),
    }
