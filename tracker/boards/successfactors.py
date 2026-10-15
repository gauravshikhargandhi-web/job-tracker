"""SAP SuccessFactors career sites (Nestlé: jobdetails.nestle.com), the site's own search pages, no key.

US jobs newest first, 25 a page; each new job's page is opened for its description.
companies.toml: host = "jobdetails.nestle.com".
"""

import html
import re
import time
import urllib.parse

from tracker.text import clean, get_text

PAGE = 25
MAX_PAGES = 200


def collect(company, cfg, today=None, since=""):
    rows, start = {}, 0
    for _ in range(MAX_PAGES):
        params = urllib.parse.urlencode({"q": "", "locationsearch": cfg.get("location", "United States"),
                                         "sortColumn": "referencedate", "sortDirection": "desc", "startrow": start})
        text = get_text(f"https://{cfg['host']}/search/?{params}", browser=True)
        page = [parse(company, cfg, r) for r in re.findall(r'<tr class="data-row">(.*?)</tr>', text, re.S)]
        for row in page:
            rows[row["key"]] = row
        start += len(page)
        if not page or (since and all(r["posted"] and r["posted"] < since for r in page)):
            break
    return list(rows.values())


def _day(text):
    try:
        return time.strftime("%Y-%m-%d", time.strptime(text.strip(), "%b %d, %Y"))
    except ValueError:
        return ""


def parse(company, cfg, row_html):
    link = re.search(r'href="([^"]+)" class="jobTitle-link">([^<]*)<', row_html)
    path, title = (link.group(1), link.group(2)) if link else ("", "")
    place = re.search(r'<span class="jobLocation">\s*([^<]*?)\s*</span>', row_html)
    posted = re.search(r'<span class="jobDate">\s*([^<]*?)\s*</span>', row_html)
    job_id = path.rstrip("/").rsplit("/", 1)[-1]
    location = html.unescape(place.group(1)) if place else ""
    return {
        "key": f"{company}:sf{job_id}",
        "company": company,
        "title": html.unescape(title).strip(),
        "location": location,
        "country": "US" if re.search(r",\s*US\b", location) else "",
        "remote": "",
        "department": "",
        "posted": _day(posted.group(1)) if posted else "",
        "link": f"https://{cfg['host']}{path}",
        "board": "successfactors",
        "detail": f"https://{cfg['host']}{path}",
    }


def describe(row):
    page = get_text(row["detail"], browser=True)
    m = re.search(r'<span class="jobdescription">(.*?)</span>\s*</div>', page, re.S) or \
        re.search(r'itemprop="description"[^>]*>(.*?)</(?:span|div)>\s*</div>', page, re.S)
    return clean(m.group(1)) if m else ""
