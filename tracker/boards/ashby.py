"""Ashby job boards (jobs.ashbyhq.com/<slug>), public JSON, no key."""

from tracker.text import day, get_json

API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
WORKPLACE = {"Remote": "Remote", "Hybrid": "Hybrid", "OnSite": "On-site"}


def collect(company, cfg, today=None, since=""):
    data = get_json(API.format(slug=cfg["slug"]))
    return [parse(company, job) for job in data.get("jobs", []) if job.get("isListed", True)]


def parse(company, job):
    places = [job.get("location", "")] + [s.get("location", "") for s in job.get("secondaryLocations") or []]
    remote = WORKPLACE.get(job.get("workplaceType") or "", "Remote" if job.get("isRemote") else "")
    return {
        "key": f"{company}:ab{job['id']}",
        "company": company,
        "title": job.get("title", "").strip(),
        "location": "; ".join(p for p in places if p),
        "remote": remote,
        "department": job.get("department", "") or job.get("team", ""),
        "posted": day(job.get("publishedAt")),
        "link": job.get("jobUrl", ""),
        "board": "ashby",
        "description": job.get("descriptionPlain", ""),
    }
