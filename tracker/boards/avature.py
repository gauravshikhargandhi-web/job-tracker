"""Avature career sites (Deloitte, Bain), the site's own search pages, no key.

The search page lists jobs 10 at a time, newest first, with no date, place or description, so each job's
page is opened; its job details (schema.org JobPosting) give the posting date, places and description.
Reading stops at the first page whose jobs were all posted before yesterday.
companies.toml: list = "https://apply.deloitte.com/en_US/careers/SearchJobs", words = "job"
(the word the site puts before Sort and Offset in its addresses: jobSort, jobOffset; Bain uses folder).
"""

import json
import re

from tracker.text import clean, get_text

PAGE = 10
MAX_PAGES = 100
LINK = re.compile(r'<a href="(https?://[^"]+/(?:JobDetail|FolderDetail)/[^"]+/(\d+))"[^>]*>\s*([^<]*?)\s*</a>')


def collect(company, cfg, today=None, since=""):
    rows, word = {}, cfg.get("words", "job")
    for page_no in range(MAX_PAGES):
        sep = "&" if "?" in cfg["list"] else "?"
        listing = get_text(f"{cfg['list']}{sep}{word}Sort=postingDate&{word}RecordsPerPage={PAGE}"
                           f"&{word}Offset={page_no * PAGE}", browser=True)
        page = []
        for link, job_id, title in LINK.findall(listing):
            key = f"{company}:av{job_id}"
            if key in rows or not title:
                continue
            row = {"key": key, "company": company, "title": clean(title), "location": "", "country": "",
                   "remote": "", "department": "", "posted": "", "link": link, "board": "avature", "detail": link}
            row["description"] = describe(row)
            rows[key] = row
            page.append(row)
        if not page or (since and all(r["posted"] and r["posted"] < since for r in page)):
            break
    return list(rows.values())


def describe(row):
    """Reads the job page's JobPosting details; also fills in the posting date, places and country."""
    page = get_text(row["detail"], browser=True)
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            places = data.get("jobLocation") or []
            places = places if isinstance(places, list) else [places]
            addresses = [p.get("address") or {} for p in places if isinstance(p, dict)]
            row["location"] = "; ".join(", ".join(filter(None, [a.get("addressLocality"), a.get("addressRegion")]))
                                        for a in addresses if isinstance(a, dict)).strip("; ")
            row["country"] = "; ".join(sorted({str(a.get("addressCountry") or "") for a in addresses
                                               if isinstance(a, dict) and a.get("addressCountry")}))
            row["posted"] = str(data.get("datePosted") or "")[:10]
            return clean(data.get("description", ""))
    return ""
