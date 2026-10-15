"""Eightfold career sites (Microsoft, Starbucks, Kraft Heinz), the search JSON the site itself uses, no key.

Read newest first, 10 jobs a request, stopping once jobs are older than the cutoff.
companies.toml: host = "apply.careers.microsoft.com", domain = "microsoft.com".
"""

import urllib.parse

from tracker.text import clean, get_json, seconds_day

MAX_PAGES = 300


def collect(company, cfg, today=None, since=""):
    rows, start = {}, 0
    for _ in range(MAX_PAGES):
        params = urllib.parse.urlencode({"domain": cfg["domain"], "query": "", "location": cfg.get("location", "United States"),
                                         "start": start, "sort_by": "timestamp"})
        data = get_json(f"https://{cfg['host']}/api/pcsx/search?{params}", browser=True)["data"]
        page = [parse(company, cfg, p) for p in data.get("positions") or []]
        for row in page:
            rows[row["key"]] = row
        start += len(page)
        if not page or start >= (data.get("count") or 0) or (since and all(r["posted"] < since for r in page)):
            break
    return list(rows.values())


def parse(company, cfg, p):
    places = p.get("standardizedLocations") or []  # e.g. "Chicago, IL, US"
    country = "US" if any(s.endswith("US") for s in places) else ("outside the US" if places else "")
    return {
        "key": f"{company}:ef{p['id']}",
        "company": company,
        "title": (p.get("name") or "").strip(),
        "location": "; ".join(p.get("locations") or []),
        "country": country,
        "remote": p.get("workLocationOption") or "",
        "department": p.get("department") or "",
        "posted": seconds_day(p.get("postedTs") or p.get("creationTs")),
        "link": f"https://{cfg['host']}/careers/job/{p['id']}",
        "board": "eightfold",
        "detail": f"https://{cfg['host']}/api/pcsx/position_details?position_id={p['id']}&domain={cfg['domain']}&hl=en",
    }


def describe(row):
    return clean(get_json(row["detail"], browser=True)["data"].get("jobDescription", ""))
