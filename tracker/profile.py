"""Reads profile.toml and decides which jobs fit: title words, description words, then the drop rules."""

import re
import tomllib


def load(path="profile.toml"):
    with open(path, "rb") as f:
        prof = tomllib.load(f)
    prof["_titles"] = {group: _words(words) for group, words in prof.get("titles", {}).items()}
    prof["_descriptions"] = {group: _words(words) for group, words in prof.get("descriptions", {}).items()}
    drop = prof.setdefault("drop", {})
    prof["_drop_titles"] = _words(drop.get("titles", []), whole=True)
    prof["_drop_descriptions"] = _words(drop.get("descriptions", []))
    prof["_drop_places"] = _words(drop.get("places", []), whole=True)
    prof["_no_sponsorship"] = _words(prof.get("sponsorship", {}).get("none", []))
    areas = prof.get("areas", {})
    prof["_keep_only_areas"] = areas.pop("keep_only_areas", False)
    prof["_areas"] = {area: _words(words, whole=True) for area, words in areas.items()}
    return prof


def _words(items, whole=False):
    """One pattern for a word list. whole=True matches whole words only, so "India" skips "Indiana"."""
    if not items:
        return None
    end = r"(?!\w)" if whole else ""
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in sorted(items, key=len, reverse=True)) + r")" + end,
                      re.I)


def title_match(prof, title):
    """'program: technical program manager' for the first title group that fits, or ''."""
    for group, pattern in prof["_titles"].items():
        hit = pattern and pattern.search(title)
        if hit:
            return f"{group}: {hit.group(0).lower()}"
    return ""


def description_match(prof, text):
    """'business_degree: MBA preferred' when the description has a description word, or ''."""
    for group, pattern in prof["_descriptions"].items():
        hit = pattern and pattern.search(text or "")
        if hit:
            return f"{group}: {hit.group(0)}"
    return ""


def drop_title(prof, row):
    """Why a job is dropped from its title or location alone, or '' to keep it."""
    hit = prof["_drop_titles"] and prof["_drop_titles"].search(row["title"])
    if hit:
        return f"title: {hit.group(0).lower()}"
    # A job listed in several places is dropped only when every place is outside the US.
    places = [p for p in re.split(r";|\|| / | or ", row.get("location", "")) if p.strip()]
    if prof["_drop_places"] and places and all(prof["_drop_places"].search(p) for p in places):
        return f"location: {row['location']}"
    # Only drop for being outside the areas once the real places are known (not "3 Locations").
    known = places and not re.fullmatch(r"\d+ Locations", row.get("location", ""))
    if prof["_keep_only_areas"] and known and not area(prof, row):
        return f"location: {row['location']}"
    return ""


def drop_description(prof, text):
    """Why the description rules the job out (clearance or citizenship), or ''."""
    hit = prof["_drop_descriptions"] and prof["_drop_descriptions"].search(text or "")
    return f"description: {hit.group(0)}" if hit else ""


def sponsorship(prof, text):
    """'No sponsorship' when the description says the company won't sponsor a visa, else ''."""
    pattern = prof["_no_sponsorship"]
    return "No sponsorship" if pattern and pattern.search(text or "") else ""


def area(prof, row):
    """Chicago, New York, Seattle, Bay Area or Remote when the job is there (several joined by ', ')."""
    place = f"{row.get('location', '')} {row.get('remote', '')}"
    return ", ".join(name for name, pattern in prof["_areas"].items() if pattern and pattern.search(place))
