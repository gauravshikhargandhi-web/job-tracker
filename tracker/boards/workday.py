"""Workday career sites (<tenant>.wdN.myworkdayjobs.com/<site>), the JSON the site itself uses, no key.

The list is read in full, or only the jobs a company's `search` words find when companies.toml sets them. It only says "Posted Today" or "Posted 3 Days Ago", so that gives a
first date; the job's own page then gives the exact posting date, the places and the description.
"""

import datetime
import re

from tracker.text import clean, day, get_json

PAGE = 20          # Workday's largest page size
MAX_JOBS = 20000   # a safety stop; no target company has this many


def api_base(url):
    """'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite' -> its JSON address."""
    match = re.match(r"(https://([^.]+)\.(wd\d+)\.myworkdayjobs\.com)/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", url)
    if not match:
        raise ValueError(f"not a Workday career site address: {url}")
    host, tenant, _, site = match.groups()
    return f"{host}/wday/cxs/{tenant}/{site}", f"{host}/{site}"


def collect(company, cfg, today, since=""):
    api, site = api_base(cfg["url"])
    seen, offset, total = {}, 0, None
    while offset < MAX_JOBS:
        data = get_json(f"{api}/jobs", {"appliedFacets": {}, "limit": PAGE, "offset": offset,
                                       "searchText": cfg.get("search", "")})
        postings = data.get("jobPostings") or []
        total = data.get("total") or total or 0  # Workday gives the total on the first page only
        for job in postings:
            row = parse(company, api, site, job, today)
            seen[row["key"]] = row
        offset += PAGE
        if not postings or offset >= total:
            break
    return list(seen.values())


def posted_on(text, today):
    """'Posted Today' -> today, 'Posted 3 Days Ago' -> 3 days back, '30+ Days Ago' -> blank."""
    text = (text or "").lower()
    if "today" in text:
        return today.isoformat()
    if "yesterday" in text:
        return (today - datetime.timedelta(days=1)).isoformat()
    match = re.search(r"(\d+)(\+?) days? ago", text)
    if match and not match.group(2):
        return (today - datetime.timedelta(days=int(match.group(1)))).isoformat()
    return ""


def parse(company, api, site, job, today):
    path = job.get("externalPath", "")
    job_id = (job.get("bulletFields") or [path.rsplit("_", 1)[-1]])[0]
    return {
        "key": f"{company}:wd{job_id}",
        "company": company,
        "title": job.get("title", "").strip(),
        "location": job.get("locationsText", ""),
        "remote": job.get("remoteType", ""),
        "posted": posted_on(job.get("postedOn"), today),
        "link": site + path,
        "board": "workday",
        "detail": api + path,
    }


def describe(row):
    """The description; also fills in the exact posting date, the real places and the country."""
    info = get_json(row["detail"]).get("jobPostingInfo") or {}
    row["posted"] = day(info.get("startDate")) or row["posted"]
    places = [p for p in [info.get("location", "")] + list(info.get("additionalLocations") or []) if p]
    if places:
        row["location"] = "; ".join(places)
    row["country"] = (info.get("country") or {}).get("descriptor", "")
    return clean(info.get("jobDescription", ""))
