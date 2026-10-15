"""Avature career sites (Deloitte, Bain), the site's own search pages, no key.

The search page lists jobs 10 at a time, newest first, with no date, place or description, so each job's
page is opened; its job details (schema.org JobPosting) give the posting date, places and description.
Reading stops at the first page whose jobs were all posted before yesterday.
companies.toml: list = "https://apply.deloitte.com/en_US/careers/SearchJobs", words = "job"
(the word the site puts before Sort and Offset in its addresses: jobSort, jobOffset; Bain uses folder).
Some sites ignore the date sort (Bain sorts by title): newest_first = false reads every page of the list,
and only the pages of jobs not seen before are opened, by the daily run.
"""

import json
import re

from tracker.text import clean, get_text

PAGE = 10
MAX_PAGES = 100
LINK = re.compile(r'<a href="(https?://[^"]+/(?:JobDetail|FolderDetail)/[^"]+/(\d+))"[^>]*>\s*([^<]*?)\s*</a>')


def collect(company, cfg, today=None, since=""):
    rows, word, newest_first = {}, cfg.get("words", "job"), cfg.get("newest_first", True)
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
            if newest_first:
                row["description"] = describe(row)
            rows[key] = row
            page.append(row)
        if not page or (newest_first and since and all(r["posted"] and r["posted"] < since for r in page)):
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
            if data.get("description"):
                return clean(data["description"])
    # Bain's details give only the date; the page's own fields give the places and description.
    fields, text = {}, []
    for block in re.findall(r'<div class="article__content__view__field[ "][^>]*>(.*?)</div>\s*</div>', page, re.S):
        label = re.search(r'__label">(.*?)</div>', block, re.S)
        value = re.search(r'__value">(.*)', block, re.S)
        value = clean(value.group(1)) if value else ""
        if label:
            fields[clean(label.group(1))] = value
        elif value:
            text.append(value)
    if fields.get("Location(s)") and not row.get("location"):
        row["location"] = fields["Location(s)"]
    return "\n".join(text)
