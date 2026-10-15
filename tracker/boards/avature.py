"""Avature career sites (Deloitte, Bain), the site's public RSS feed, no key.

The feed lists jobs 20 at a time with their posting date but no place or description, so each new job's
page is opened; its job details (schema.org JobPosting) give the description and places.
companies.toml: feed = "https://apply.deloitte.com/en_US/careers/SearchJobs/feed/", offset = "jobOffset".
"""

import email.utils
import json
import re

from tracker.text import clean, get_text

PAGE = 20
MAX_PAGES = 500


def collect(company, cfg, today=None, since=""):
    rows, offset = {}, 0
    for _ in range(MAX_PAGES):
        sep = "&" if "?" in cfg["feed"] else "?"
        feed = get_text(f"{cfg['feed']}{sep}{cfg.get('offset', 'jobOffset')}={offset}", browser=True)
        page = [parse(company, item) for item in re.findall(r"<item>(.*?)</item>", feed, re.S)]
        fresh = [r for r in page if r["key"] not in rows]
        for row in fresh:
            rows[row["key"]] = row
        offset += PAGE
        if not fresh:  # past the last page, or the site ignores the offset
            break
    return list(rows.values())


def _tag(xml, name):
    m = re.search(rf"<{name}>(.*?)</{name}>", xml, re.S)
    return re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip()) if m else ""


def parse(company, item):
    link = _tag(item, "link")
    stamp = email.utils.parsedate_to_datetime(_tag(item, "pubDate")) if _tag(item, "pubDate") else None
    return {
        "key": f"{company}:av{link.rstrip('/').rsplit('/', 1)[-1]}",
        "company": company,
        "title": clean(_tag(item, "title")),
        "location": "",
        "remote": "",
        "department": "",
        "posted": stamp.date().isoformat() if stamp else "",
        "link": link,
        "board": "avature",
        "detail": link,
    }


def describe(row):
    """Reads the job page's JobPosting details; also fills in the places and country."""
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
            return clean(data.get("description", ""))
    return ""
