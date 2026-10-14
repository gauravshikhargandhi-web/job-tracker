"""Greenhouse job boards (boards.greenhouse.io/<slug>), public JSON, no key. One call gives every job with its description."""

from tracker.text import clean, day, get_json

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def collect(company, cfg, queries=None):
    data = get_json(API.format(slug=cfg["slug"]) + "?content=true")
    return [parse(company, cfg, job) for job in data.get("jobs", [])]


def parse(company, cfg, job):
    departments = ", ".join(d.get("name", "") for d in job.get("departments") or [])
    return {
        "key": f"{company}:gh{job['id']}",
        "company": company,
        "title": job.get("title", "").strip(),
        "location": (job.get("location") or {}).get("name", ""),
        "remote": "",
        "department": departments,
        "posted": day(job.get("first_published") or job.get("updated_at")),
        "link": job.get("absolute_url", ""),
        "board": "greenhouse",
        "detail": API.format(slug=cfg["slug"]) + f"/{job['id']}",
        "description": clean(job.get("content", "")),
    }


def describe(row):
    return clean(get_json(row["detail"]).get("content", ""))
