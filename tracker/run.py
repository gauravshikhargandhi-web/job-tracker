"""Daily run: read every open job at every company and save the US jobs posted in the last 24 hours.

    python -m tracker.run                  # normal daily run
    python -m tracker.run --only Stripe    # one company, for trying a new line in companies.toml

Nothing is filtered by role or keyword here. The daily Claude report reads the day's file and decides what fits.
"""

import argparse
import csv
import datetime
import os
import re
import tomllib

from tracker import boards
from tracker.us import is_us

DAY_PATH = "data/jobs/{day}.csv"  # the new US jobs found that day, with full descriptions
RECENT_PATH = "data/recent.csv"   # every job from the last KEEP_DAYS daily files, for the daily report
KEEP_DAYS = 3                     # daily files older than this are deleted (GaGa, 2026-10-16)
KNOWN_PATH = "data/known.csv"     # every job ever seen, so each job is saved once
SUMMARY_PATH = "data/summary.csv"
STREAK_PATH = "data/failures.csv"
FAIL_AFTER_DAYS = 3
NOT_READ_YET = "not_yet"  # board value in companies.toml for companies whose own site has no reader yet
MAX_PAGES_OPENED = 3000   # a safety stop on job pages opened per run

JOB_FIELDS = ["key", "company", "title", "location", "country", "remote", "department", "posted", "first_seen",
              "link", "board", "description"]
KNOWN_FIELDS = ["key", "company", "title", "posted", "first_seen"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", help="override today's date (YYYY-MM-DD)")
    parser.add_argument("--companies", default="companies.toml")
    parser.add_argument("--only", help="run one company only")
    args = parser.parse_args()

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.datetime.now(datetime.timezone.utc).date())
    stamp = today.isoformat()
    since = (today - datetime.timedelta(days=1)).isoformat()  # posted today or yesterday = the last 24 hours
    with open(args.companies, "rb") as f:
        companies = tomllib.load(f)["company"]
    if args.only:
        companies = [c for c in companies if c["name"].lower() == args.only.lower()]

    known = {r["key"]: r for r in load(KNOWN_PATH)}
    known_companies = {r["company"] for r in known.values()}
    day_path = DAY_PATH.format(day=stamp)
    saved = {r["key"]: r for r in load(day_path)}  # a second run on the same day adds to the file
    failed, counts, opened = [], {}, 0

    for cfg in companies:
        name = cfg["name"]
        if cfg["board"] == NOT_READ_YET:
            continue
        try:
            rows = boards.READERS[cfg["board"]].collect(name, cfg, today, since)
        except Exception as exc:
            print(f"{name}: FAILED ({exc})")
            failed.append(name)
            continue
        if not rows:
            print(f"{name}: FAILED (no jobs returned)")
            failed.append(name)
            continue
        # Some companies are narrowed to certain roles in companies.toml (titles = [...]).
        if cfg.get("titles"):
            wanted = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in cfg["titles"]) + r")(?!\w)", re.I)
            rows = [r for r in rows if wanted.search(r["title"])]

        first_time = name not in known_companies
        retry, kept, limited = set(), 0, False
        for row in rows:
            if row["key"] in known or row["key"] in saved or not is_new(row, since, first_time):
                continue
            if not row.get("description") and row.get("detail"):
                if opened >= MAX_PAGES_OPENED or limited:
                    retry.add(row["key"])
                    continue
                try:
                    row["description"] = boards.describe(row)
                    opened += 1
                except Exception as exc:
                    print(f"{name}: could not open {row['title']} ({exc}); tried again next run")
                    retry.add(row["key"])
                    # A site that says "too many requests" stops answering for a while: open its other jobs next run.
                    limited = getattr(exc, "code", None) == 429
                    continue
            # The job page can correct the date (Workday) and the places.
            if row["posted"] and row["posted"] < since:
                continue
            if not is_us(row.get("location", ""), row.get("country", "")):
                continue
            row["first_seen"] = stamp
            saved[row["key"]] = row
            kept += 1
        # Remember every job read, so the next run only saves jobs that appear overnight.
        for row in rows:
            if row["key"] not in retry:
                known.setdefault(row["key"], {"key": row["key"], "company": name, "title": row["title"],
                                              "posted": row["posted"], "first_seen": stamp})
        if retry:
            print(f"{name}: {len(retry)} job pages wait for the next run")
        counts[name] = (len(rows), kept)
        print(f"{name}: {len(rows)} open jobs, {kept} new US jobs from the last 24 hours")

    save(day_path, saved.values(), JOB_FIELDS)
    save(RECENT_PATH, keep_recent(today), JOB_FIELDS)
    save(KNOWN_PATH, known.values(), KNOWN_FIELDS)
    streaks = update_streaks(STREAK_PATH, failed)
    save_summary(SUMMARY_PATH, stamp, companies, counts, failed, streaks)
    print(f"saved {len(saved)} new US jobs to {day_path}; {opened} job pages opened; {len(failed)} companies failed")
    broken = [name for name in failed if streaks[name] >= FAIL_AFTER_DAYS]
    if broken:
        raise SystemExit(f"boards failed {FAIL_AFTER_DAYS} days in a row: {', '.join(broken)}")


def is_new(row, since, first_time):
    """Posted in the last 24 hours. A job with no date counts as new the first day it is seen,
    except on a company's first run, when every job is unseen. Workday jobs with no date are older than 30 days."""
    if row["posted"]:
        return row["posted"] >= since
    return row["board"] != "workday" and not first_time


def keep_recent(today):
    """Deletes daily files older than KEEP_DAYS days and returns the jobs in the rest.
    known.csv keeps every job's key, so a deleted job is not saved again."""
    oldest = (today - datetime.timedelta(days=KEEP_DAYS - 1)).isoformat()
    folder = os.path.dirname(DAY_PATH)
    rows = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".csv"):
            continue
        if name[:-4] < oldest:
            os.remove(os.path.join(folder, name))
        else:
            rows += load(os.path.join(folder, name))
    return rows


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(path, rows, fields):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["company"], r["title"], r["key"]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def update_streaks(path, failed):
    """Days in a row each failed board has failed, counting today. Saved for the next run."""
    previous = {r["company"]: int(r["days"]) for r in load(path)}
    streaks = {name: previous.get(name, 0) + 1 for name in failed}
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["company", "days"])
        writer.writerows(sorted(streaks.items()))
    return streaks


def save_summary(path, stamp, companies, counts, failed, streaks):
    """Today's counts per company: open jobs read and new US jobs saved."""
    out = [["company", "board", "open_jobs", "new_us_jobs", "note"],
           ["All companies", "", sum(c[0] for c in counts.values()), sum(c[1] for c in counts.values()),
            f"run {stamp}"]]
    for cfg in companies:
        name = cfg["name"]
        note = ""
        if cfg["board"] == NOT_READ_YET:
            note = "Own careers site; no reader built yet"
        elif name in failed:
            days = streaks.get(name, 1)
            note = f"Failed {days} days in a row" if days > 1 else "Failed today"
        read, new = counts.get(name, ("", ""))
        out.append([name, cfg["board"], read, new, note])
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(out)


if __name__ == "__main__":
    main()
