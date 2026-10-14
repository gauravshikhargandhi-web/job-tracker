"""Lever job boards (jobs.lever.co/<slug>), public JSON, no key."""

from tracker.text import day, get_json

API = "https://api.lever.co/v0/postings/{slug}?mode=json"
WORKPLACE = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site", "on-site": "On-site"}


def collect(company, cfg, queries=None):
    return [parse(company, job) for job in get_json(API.format(slug=cfg["slug"]))]


def parse(company, job):
    cats = job.get("categories") or {}
    places = cats.get("allLocations") or [cats.get("location", "")]
    lists = "\n".join(f"{item.get('text', '')}\n{item.get('content', '')}" for item in job.get("lists") or [])
    return {
        "key": f"{company}:lv{job['id']}",
        "company": company,
        "title": job.get("text", "").strip(),
        "location": "; ".join(p for p in places if p),
        "remote": WORKPLACE.get((job.get("workplaceType") or "").lower(), ""),
        "department": cats.get("team", "") or cats.get("department", ""),
        "posted": day(job.get("createdAt")),
        "link": job.get("hostedUrl", ""),
        "board": "lever",
        "description": "\n".join(filter(None, [job.get("descriptionPlain", ""), lists,
                                                job.get("additionalPlain", "")])),
    }
