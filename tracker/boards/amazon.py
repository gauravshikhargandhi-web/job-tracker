"""amazon.jobs, the public search JSON the site uses, no key. US jobs only, searched per query."""

import urllib.parse

from tracker.text import clean, day, get_json

API = "https://www.amazon.jobs/en/search.json"
PAGE = 100
MAX_PER_QUERY = 500


def collect(company, cfg, queries=()):
    seen = {}
    for query in queries or [""]:
        offset = 0
        while offset < MAX_PER_QUERY:
            params = urllib.parse.urlencode([("base_query", query), ("result_limit", PAGE), ("offset", offset),
                                             ("sort", "recent"), ("normalized_country_code[]", cfg.get("country", "USA"))])
            data = get_json(f"{API}?{params}")
            for job in data.get("jobs") or []:
                row = parse(company, job)
                seen.setdefault(row["key"], dict(row, found_by=query))
            offset += PAGE
            if offset >= (data.get("hits") or 0):
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
        "remote": "",
        "department": job.get("business_category", "") or job.get("job_category", ""),
        "posted": day(job.get("posted_date")),
        "link": "https://www.amazon.jobs" + job.get("job_path", ""),
        "board": "amazon",
        "description": clean("\n".join(parts)),
    }
