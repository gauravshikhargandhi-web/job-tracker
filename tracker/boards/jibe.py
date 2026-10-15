"""iCIMS Jibe career sites (Rivian: careers.rivian.com), the jobs JSON the site itself uses, no key.

Newest first, 100 jobs a request, descriptions included. companies.toml: host = "careers.rivian.com".
"""

from tracker.text import clean, day, get_json

PAGE = 100
MAX_PAGES = 100


def collect(company, cfg, today=None, since=""):
    rows = {}
    for page_no in range(1, MAX_PAGES + 1):
        data = get_json(f"https://{cfg['host']}/api/jobs?page={page_no}&limit={PAGE}&sortBy=posted_date"
                        f"&descending=true&internal=false")
        page = [parse(company, cfg, j.get("data") or j) for j in data.get("jobs") or []]
        for row in page:
            rows[row["key"]] = row
        if len(page) < PAGE or (since and all(r["posted"] and r["posted"] < since for r in page)):
            break
    return list(rows.values())


def parse(company, cfg, j):
    return {
        "key": f"{company}:jb{j.get('req_id') or j.get('slug')}",
        "company": company,
        "title": (j.get("title") or "").strip(),
        "location": j.get("full_location") or j.get("location_name") or "",
        "country": j.get("country") or j.get("country_code") or "",
        "remote": "",
        "department": ", ".join(c.strip() for c in j.get("category") or []),
        "posted": day(j.get("posted_date") or j.get("create_date")),
        "link": f"https://{cfg['host']}/careers-home/jobs/{j.get('slug') or j.get('req_id')}",
        "board": "jibe",
        "description": clean(j.get("description", "")),
    }
