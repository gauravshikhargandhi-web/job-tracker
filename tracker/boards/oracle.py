"""Oracle Recruiting Cloud career sites (S&C Electric, UL Solutions), the JSON the site itself uses, no key.

Newest first, 25 jobs a request; each new job's page is opened for its description.
companies.toml: host = "ejia.fa.us6.oraclecloud.com", site = "CX_1001".
"""

import urllib.parse

from tracker.text import clean, day, get_json

PAGE = 25
MAX_PAGES = 200


def _api(cfg):
    return f"https://{cfg['host']}/hcmRestApi/resources/latest"


def collect(company, cfg, today=None, since=""):
    rows, offset = {}, 0
    for _ in range(MAX_PAGES):
        finder = f"findReqs;siteNumber={cfg['site']},sortBy=POSTING_DATES_DESC,limit={PAGE},offset={offset}"
        data = get_json(f"{_api(cfg)}/recruitingCEJobRequisitions?onlyData=true"
                        f"&expand=requisitionList.secondaryLocations&finder={urllib.parse.quote(finder, safe='=;,')}")
        found = (data.get("items") or [{}])[0]
        page = [parse(company, cfg, r) for r in found.get("requisitionList") or []]
        for row in page:
            rows[row["key"]] = row
        offset += PAGE
        if not page or offset >= (found.get("TotalJobsCount") or 0) or (since and all(r["posted"] < since for r in page)):
            break
    return list(rows.values())


def parse(company, cfg, r):
    places = [r.get("PrimaryLocation", "")] + [s.get("Name", "") for s in r.get("secondaryLocations") or []]
    return {
        "key": f"{company}:or{r['Id']}",
        "company": company,
        "title": (r.get("Title") or "").strip(),
        "location": "; ".join(p for p in places if p),
        "country": r.get("PrimaryLocationCountry") or "",
        "remote": r.get("WorkplaceType") or "",
        "department": r.get("JobFamily") or "",
        "posted": day(r.get("PostedDate")),
        "link": f"https://{cfg['host']}/hcmUI/CandidateExperience/en/sites/{cfg['site']}/job/{r['Id']}",
        "board": "oracle",
        "detail": f"{_api(cfg)}/recruitingCEJobRequisitionDetails?expand=all&onlyData=true"
                  f"&finder=ById;Id=%22{r['Id']}%22,siteNumber={cfg['site']}",
    }


def describe(row):
    item = (get_json(row["detail"]).get("items") or [{}])[0]
    parts = [item.get(k) or "" for k in ("ExternalDescriptionStr", "ExternalResponsibilitiesStr",
                                          "ExternalQualificationsStr", "CorporateDescriptionStr")]
    return clean("\n".join(parts))
