"""CSV helpers and the job pool: every open job at the tracked companies, refreshed per company each run."""

import csv
import os

from tracker.schema import CHECK_FIELDS, JOB_FIELDS


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(path, rows, fields=JOB_FIELDS, sort=None):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rows = sorted(rows, key=sort or (lambda r: (r["company"], r["title"], r["key"])))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def closed(previous, company, fresh):
    """Jobs at this company that were open before but are missing from the fresh pull."""
    still_open = {r["key"] for r in fresh}
    return [r for r in previous if r["company"] == company and r["key"] not in still_open]


def merge(previous, company, fresh, today):
    """Replace one company's jobs with a fresh pull, keeping first_seen and what was read from descriptions.

    Other companies' jobs are left as they were, so one failing board never
    wipes the rest of the pool. Jobs missing from the fresh pull have closed.
    """
    before = {r["key"]: r for r in previous if r["company"] == company}
    kept = [r for r in previous if r["company"] != company]
    stamp = today.isoformat()
    for row in fresh:
        old = before.get(row["key"], {})
        row["first_seen"] = old.get("first_seen") or stamp
        row["last_seen"] = stamp
        row["found_by"] = row.get("found_by") or old.get("found_by", "")
        for field in CHECK_FIELDS:
            row.setdefault(field, old.get(field, ""))
    return kept + fresh


def archive(path, rows, fields):
    """Add closed matches to the archive, keeping one row per job."""
    kept = {r["key"]: r for r in load(path)}
    for row in rows:
        kept[row["key"]] = row
    save(path, kept.values(), fields=fields)
    return len(kept)
