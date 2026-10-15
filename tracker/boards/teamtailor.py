"""Teamtailor career sites (Mutares: career.mutares.com), the site's public RSS feed, no key.

One request gives every job with its description and places. companies.toml: host = "career.mutares.com".
"""

import email.utils
import re

from tracker.text import clean, get_text


def collect(company, cfg, today=None, since=""):
    feed = get_text(f"https://{cfg['host']}/jobs.rss", browser=True)
    return [parse(company, item) for item in re.findall(r"<item>(.*?)</item>", feed, re.S)]


def _tag(xml, name):
    m = re.search(rf"<{name}>(.*?)</{name}>", xml, re.S)
    return re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip()) if m else ""


def parse(company, item):
    places = re.findall(r"<tt:location>(.*?)</tt:location>", item, re.S)
    cities = ["; ".join(filter(None, [_tag(p, "tt:city"), _tag(p, "tt:country")])) for p in places]
    stamp = email.utils.parsedate_to_datetime(_tag(item, "pubDate")) if _tag(item, "pubDate") else None
    link = _tag(item, "link")
    return {
        "key": f"{company}:tt{_tag(item, 'guid') or link}",
        "company": company,
        "title": clean(_tag(item, "title")),
        "location": "; ".join(c.replace("; ", ", ") for c in cities if c),
        "country": "; ".join(sorted({_tag(p, "tt:country") for p in places if _tag(p, "tt:country")})),
        "remote": _tag(item, "remoteStatus").replace("none", ""),
        "department": _tag(item, "tt:department"),
        "posted": stamp.date().isoformat() if stamp else "",
        "link": link,
        "board": "teamtailor",
        "description": clean(_tag(item, "description")),
    }
