"""amazon.jobs, the public search JSON the site uses, no key. US jobs, newest first, read back to a cutoff date."""

import urllib.parse

from tracker.text import clean, day, get_json

API = "https://www.amazon.jobs/en/search.json"
PAGE = 100
MAX_JOBS = 10000


def collect(company, cfg, today, since=""):
    """Every US job, newest first, stopping once jobs are older than since (YYYY-MM-DD)."""
    seen, offset = {}, 0
    while offset < MAX_JOBS:
        params = urllib.parse.urlencode([("result_limit", PAGE), ("offset", offset), ("sort", "recent"),
                                         ("normalized_country_code[]", cfg.get("country", "USA"))])
        data = get_json(f"{API}?{params}")
        jobs = data.get("jobs") or []
        rows = [parse(company, job) for job in jobs]
        for row in rows:
            seen[row["key"]] = row
        offset += PAGE
        if not jobs or offset >= (data.get("hits") or 0) or (since and all(r["posted"] and r["posted"] < since for r in rows)):
            break
    return list(seen.values())


def parse(company, job):
    parts = [job.get("description", ""),
             "Basic qualifications: " + job.get("basic_qualifications", ""),
             "Preferred qualifications: " + job.get("preferred_qualifications", "")]
    return {
        "key": f"{company}:az{job.get('id_icims') or job.get('id')}",
        "company": company,
        "title": job.get("title", "").strip(),
        "location": job.get("normalized_location") or job.get("location", ""),
        "country": "USA",
        "remote": "",
        "department": job.get("business_category", "") or job.get("job_category", ""),
        "posted": day(job.get("posted_date")),
        "link": "https://www.amazon.jobs" + job.get("job_path", ""),
        "board": "amazon",
        "description": clean("\n".join(parts)),
    }
