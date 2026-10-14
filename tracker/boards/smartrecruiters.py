"""SmartRecruiters career sites (jobs.smartrecruiters.com/<slug>), public JSON, no key."""

import urllib.parse

from tracker.text import clean, day, get_json

API = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
PAGE = 100
MAX_PER_QUERY = 300


def collect(company, cfg, queries=()):
    seen = {}
    for query in queries or [""]:
        offset = 0
        while offset < MAX_PER_QUERY:
            params = urllib.parse.urlencode({"q": query, "limit": PAGE, "offset": offset, "country": cfg.get("country", "us")})
            data = get_json(API.format(slug=cfg["slug"]) + "?" + params)
            for job in data.get("content") or []:
                row = parse(company, cfg, job)
                seen.setdefault(row["key"], dict(row, found_by=query))
            offset += PAGE
            if offset >= (data.get("totalFound") or 0):
                break
    return list(seen.values())


def parse(company, cfg, job):
    loc = job.get("location") or {}
    place = ", ".join(p for p in [loc.get("city"), loc.get("region"), loc.get("country", "").upper()] if p)
    return {
        "key": f"{company}:sr{job['id']}",
        "company": company,
        "title": job.get("name", "").strip(),
        "location": place,
        "remote": "Remote" if loc.get("remote") else ("Hybrid" if loc.get("hybrid") else ""),
        "department": (job.get("department") or {}).get("label", ""),
        "posted": day(job.get("releasedDate")),
        "link": f"https://jobs.smartrecruiters.com/{cfg['slug']}/{job['id']}",
        "board": "smartrecruiters",
        "detail": job.get("ref") or API.format(slug=cfg["slug"]) + f"/{job['id']}",
    }


def describe(row):
    sections = (get_json(row["detail"]).get("jobAd") or {}).get("sections") or {}
    return "\n".join(clean(s.get("text", "")) for s in sections.values() if isinstance(s, dict))
