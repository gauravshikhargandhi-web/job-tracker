"""SmartRecruiters career sites (jobs.smartrecruiters.com/<slug>), public JSON, no key. Every US job is read."""

import urllib.parse

from tracker.text import clean, day, get_json

API = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
PAGE = 100
MAX_JOBS = 20000


def collect(company, cfg, today=None, since=""):
    seen, offset = {}, 0
    while offset < MAX_JOBS:
        params = urllib.parse.urlencode({"limit": PAGE, "offset": offset, "country": cfg.get("country", "us")})
        data = get_json(API.format(slug=cfg["slug"]) + "?" + params)
        jobs = data.get("content") or []
        for job in jobs:
            row = parse(company, cfg, job)
            seen[row["key"]] = row
        offset += PAGE
        if not jobs or offset >= (data.get("totalFound") or 0):
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
        "country": loc.get("country", ""),
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
