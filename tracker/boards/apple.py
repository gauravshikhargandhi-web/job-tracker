"""jobs.apple.com, the search JSON the site itself uses, no key. US jobs, newest first, 20 a request.

Each new job's page is opened for its full description.
"""

from tracker.text import clean, day, get_json

SEARCH = "https://jobs.apple.com/api/v1/search"
MAX_PAGES = 300


def _post(page):
    body = {"query": "", "filters": {"locations": ["postLocation-USA"]}, "page": page, "locale": "en-us",
            "sort": "newest", "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"}}
    return get_json(SEARCH, body, browser=True)


def collect(company, cfg, today=None, since=""):
    rows = {}
    for page_no in range(1, MAX_PAGES + 1):
        res = _post(page_no).get("res") or {}
        page = [parse(company, j) for j in res.get("searchResults") or []]
        for row in page:
            rows[row["key"]] = row
        if not page or (since and all(r["posted"] < since for r in page)):
            break
    return list(rows.values())


def parse(company, j):
    places = [p.get("name", "") for p in j.get("locations") or []]
    return {
        "key": f"{company}:ap{j.get('positionId') or j['id']}",
        "company": company,
        "title": (j.get("postingTitle") or "").strip(),
        "location": "; ".join(p for p in places if p),
        "country": "United States",  # the search asks for US jobs only
        "remote": "Remote" if j.get("homeOffice") else "",
        "department": (j.get("team") or {}).get("teamName", "") if isinstance(j.get("team"), dict) else "",
        "posted": day(j.get("postDateInGMT")),
        "link": f"https://jobs.apple.com/en-us/details/{j.get('positionId')}/{j.get('transformedPostingTitle', '')}",
        "board": "apple",
        "detail": f"https://jobs.apple.com/api/v1/jobDetails/{j['id']}",
    }


def describe(row):
    d = get_json(row["detail"], browser=True)
    d = d.get("res", d)
    parts = [d.get("jobSummary"), d.get("description"), "Minimum qualifications: " + (d.get("minimumQualifications") or ""),
             "Preferred qualifications: " + (d.get("preferredQualifications") or "")]
    return clean("\n".join(p for p in parts if p))
