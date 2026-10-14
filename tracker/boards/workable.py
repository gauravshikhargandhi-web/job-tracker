"""Workable job boards (apply.workable.com/<slug>), the public widget JSON, no key. Descriptions included."""

from tracker.text import clean, day, get_json

API = "https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true"


def collect(company, cfg, today=None, since=""):
    data = get_json(API.format(slug=cfg["slug"]))
    return [parse(company, cfg, job) for job in data.get("jobs", [])]


def parse(company, cfg, job):
    places = job.get("locations") or [job]
    location = "; ".join(", ".join(p for p in [loc.get("city"), loc.get("region") or loc.get("state"),
                                                loc.get("country")] if p) for loc in places)
    shortcode = job.get("shortcode", "")
    return {
        "key": f"{company}:wk{shortcode}",
        "company": company,
        "title": job.get("title", "").strip(),
        "location": location,
        "country": "; ".join(sorted({loc.get("country", "") for loc in places if loc.get("country")})),
        "remote": "Remote" if job.get("telecommuting") else "",
        "department": job.get("department", ""),
        "posted": day(job.get("published_on") or job.get("created_at")),
        "link": job.get("url") or f"https://apply.workable.com/{cfg['slug']}/j/{shortcode}/",
        "board": "workable",
        "description": clean("\n".join(filter(None, [job.get("description", ""), job.get("requirements", ""),
                                                     job.get("benefits", "")]))),
    }
