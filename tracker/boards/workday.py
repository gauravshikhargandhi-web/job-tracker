"""Workday career sites (<tenant>.wdN.myworkdayjobs.com/<site>), the JSON the site itself uses, no key.

Workday sites hold thousands of jobs, so the board is searched once per
word in profile.toml [search] words rather than read in full. The job
description is read later, only for jobs that match the profile.
"""

import re

from tracker.text import clean, get_json

PAGE = 20          # Workday's largest page size
MAX_PER_QUERY = 200


def api_base(url):
    """'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite' -> its JSON address."""
    match = re.match(r"(https://([^.]+)\.(wd\d+)\.myworkdayjobs\.com)/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", url)
    if not match:
        raise ValueError(f"not a Workday career site address: {url}")
    host, tenant, _, site = match.groups()
    return f"{host}/wday/cxs/{tenant}/{site}", f"{host}/{site}"


def collect(company, cfg, queries=()):
    api, site = api_base(cfg["url"])
    seen = {}
    for query in queries or [""]:
        offset = 0
        while offset < MAX_PER_QUERY:
            data = get_json(f"{api}/jobs", {"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": query})
            postings = data.get("jobPostings") or []
            for job in postings:
                row = parse(company, api, site, job)
                seen.setdefault(row["key"], dict(row, found_by=query))
            offset += PAGE
            if len(postings) < PAGE or offset >= (data.get("total") or 0):
                break
    return list(seen.values())


def parse(company, api, site, job):
    path = job.get("externalPath", "")
    job_id = (job.get("bulletFields") or [path.rsplit("_", 1)[-1]])[0]
    return {
        "key": f"{company}:wd{job_id}",
        "company": company,
        "title": job.get("title", "").strip(),
        "location": job.get("locationsText", ""),
        "remote": job.get("remoteType", ""),
        "department": "",
        "posted": "",   # Workday only says "Posted 3 Days Ago"; first_seen covers it
        "link": site + path,
        "board": "workday",
        "detail": api + path,
    }


def describe(row):
    """The description; also swaps a list summary like "3 Locations" for the real places."""
    info = get_json(row["detail"]).get("jobPostingInfo") or {}
    places = [info.get("location", "")] + list(info.get("additionalLocations") or [])
    places = [p for p in places if p]
    if places:
        country = (info.get("country") or {}).get("descriptor", "")
        row["location"] = "; ".join(places) + (f" ({country})" if country and len(places) == 1 else "")
    return clean(info.get("jobDescription", ""))
