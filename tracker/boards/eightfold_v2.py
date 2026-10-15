"""Older Eightfold career sites (BCG), the jobs JSON the site itself uses, no key. Descriptions included.

companies.toml: host = "experiencedtalent.bcg.com", domain = "bcg.com".
"""

import urllib.parse

from tracker.text import clean, get_json, seconds_day

PAGE = 10
MAX_PAGES = 200


def collect(company, cfg, today=None, since=""):
    rows, start = {}, 0
    for _ in range(MAX_PAGES):
        params = urllib.parse.urlencode({"domain": cfg["domain"], "start": start, "num": PAGE,
                                         "location": cfg.get("location", "United States"), "sort_by": "timestamp"})
        data = get_json(f"https://{cfg['host']}/api/apply/v2/jobs?{params}", browser=True)
        page = [parse(company, p) for p in data.get("positions") or []]
        for row in page:
            rows[row["key"]] = row
        start += PAGE
        if not page or start >= (data.get("count") or 0) or (since and all(r["posted"] < since for r in page)):
            break
    return list(rows.values())


def parse(company, p):
    return {
        "key": f"{company}:ef{p['id']}",
        "company": company,
        "title": (p.get("name") or "").strip(),
        "location": "; ".join(p.get("locations") or [p.get("location", "")]),
        "remote": p.get("work_location_option") or "",
        "department": p.get("department") or "",
        "posted": seconds_day(p.get("t_create")),
        "link": p.get("canonicalPositionUrl", ""),
        "board": "eightfold_v2",
        "description": clean(p.get("job_description", "")),
    }
