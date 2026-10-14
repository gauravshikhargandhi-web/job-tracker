"""Daily run: read every company's job board, keep the jobs that fit profile.toml, list the new ones.

    python -m tracker.run                  # normal daily run
    python -m tracker.run --only Stripe    # one company, for trying a new line in companies.toml
"""

import argparse
import collections
import csv
import datetime
import os
import tomllib

from tracker import boards, pool, profile
from tracker.schema import JOB_FIELDS, MATCH_FIELDS

JOBS_PATH = "data/jobs.csv"              # every open job read from every company
MATCHES_PATH = "data/matches.csv"        # every open job that fits, newest match first
NEW_PATH = "data/new_today.csv"          # the jobs that started matching today
FILTERED_PATH = "data/filtered_out.csv"  # jobs that matched but a drop rule ruled out, with the reason
SUMMARY_PATH = "data/summary.csv"
STREAK_PATH = "data/failures.csv"
ARCHIVE_PATH = "data/archive/{year}.csv"  # matches that closed, one file per year
FAIL_AFTER_DAYS = 3
# How many job pages are opened per run to read descriptions the list didn't include; the rest wait a day.
MAX_DESCRIPTIONS = 400
NOT_READ_YET = "not_yet"  # board value in companies.toml for companies whose own site has no reader yet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", help="override today's date (YYYY-MM-DD)")
    parser.add_argument("--profile", default="profile.toml")
    parser.add_argument("--companies", default="companies.toml")
    parser.add_argument("--only", help="run one company only")
    args = parser.parse_args()

    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    stamp = today.isoformat()
    prof = profile.load(args.profile)
    with open(args.companies, "rb") as f:
        companies = tomllib.load(f)["company"]
    if args.only:
        companies = [c for c in companies if c["name"].lower() == args.only.lower()]
    search = prof.get("search", {})
    words = search.get("words", [])

    rows = pool.load(JOBS_PATH)
    failed, closed = [], []
    for cfg in companies:
        name = cfg["name"]
        if cfg["board"] == NOT_READ_YET:
            continue
        try:
            fresh = boards.READERS[cfg["board"]].collect(name, cfg, words)
        except Exception as exc:
            # Keep yesterday's jobs for this company and carry on with the rest.
            print(f"{name}: FAILED ({exc}); keeping previous jobs")
            failed.append(name)
            continue
        gone = pool.closed(rows, name, fresh)
        if not fresh and len(gone) >= 5:
            print(f"{name}: FAILED (no jobs returned); keeping previous jobs")
            failed.append(name)
            continue
        closed += gone
        rows = pool.merge(rows, name, fresh, today)
        print(f"{name}: {len(fresh)} open jobs")

    # Read descriptions: the ones the list included now, the rest from each job's own page (once per job).
    for row in rows:
        if row.get("description"):
            check(prof, row, row["description"])
    waiting = [r for r in rows if needs_description(prof, r)]
    # Title matches first, newest first within each.
    waiting.sort(key=lambda r: r["first_seen"], reverse=True)
    waiting.sort(key=lambda r: not profile.title_match(prof, r["title"]))
    opened = 0
    for row in waiting[:MAX_DESCRIPTIONS]:
        try:
            check(prof, row, boards.describe(row))
            opened += 1
        except Exception as exc:
            print(f"{row['company']}: could not read the description of {row['title']} ({exc})")
    if len(waiting) > MAX_DESCRIPTIONS:
        print(f"descriptions: {len(waiting) - MAX_DESCRIPTIONS} job pages wait for the next run")

    matches, dropped = [], []
    for row in rows:
        why = profile.title_match(prof, row["title"]) or row.get("description_match", "")
        if not why:
            continue
        reason = profile.drop_title(prof, row) or row.get("description_drop", "")
        if reason:
            dropped.append(dict(row, why=why, filtered_reason=reason))
            continue
        row["matched_on"] = row.get("matched_on") or stamp
        matches.append(dict(row, why=why, area=profile.area(prof, row)))
    pool.save(JOBS_PATH, rows)

    new_today = [m for m in matches if m["matched_on"] == stamp]
    newest_first = lambda r: (-int(r["matched_on"].replace("-", "")), not r["area"], r["company"], r["title"])
    pool.save(MATCHES_PATH, matches, fields=MATCH_FIELDS, sort=newest_first)
    pool.save(NEW_PATH, new_today, fields=MATCH_FIELDS, sort=newest_first)
    pool.save(FILTERED_PATH, dropped, fields=JOB_FIELDS + ["why", "filtered_reason"])

    gone_matches = [dict(r, closed_on=stamp) for r in closed if r.get("matched_on")]
    if gone_matches:
        pool.archive(ARCHIVE_PATH.format(year=today.year), gone_matches, fields=JOB_FIELDS + ["closed_on"])

    streaks = update_streaks(STREAK_PATH, failed)
    save_summary(SUMMARY_PATH, today, companies, rows, matches, new_today, dropped, failed, streaks)
    print(f"pool: {len(rows)} jobs, {len(matches)} match {args.profile}, {len(new_today)} new today "
          f"(see {NEW_PATH}), {len(dropped)} dropped by a rule, {len(gone_matches)} matches closed, "
          f"{opened} job pages read")
    broken = [name for name in failed if streaks[name] >= FAIL_AFTER_DAYS]
    if broken:
        raise SystemExit(f"boards failed {FAIL_AFTER_DAYS} days in a row: {', '.join(broken)}")


def check(prof, row, text):
    """Note what the description says, so it never has to be read again."""
    row["description_read"] = "Y"
    row["description_match"] = profile.description_match(prof, text)
    row["description_drop"] = profile.drop_description(prof, text)
    row["sponsor"] = profile.sponsorship(prof, text)


def needs_description(prof, row):
    """A job whose description wasn't in the list and could change whether it matches."""
    if row.get("description_read") or not row.get("detail"):
        return False
    if profile.title_match(prof, row["title"]):
        return not profile.drop_title(prof, row)  # check clearance, citizenship and sponsorship
    # Only jobs a description search word found can match on their description.
    return row.get("found_by", "") in prof.get("search", {}).get("description_words", [])


def update_streaks(path, failed):
    """Days in a row each failed board has failed, counting today. Saved for the next run."""
    previous = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            previous = {row["company"]: int(row["days"]) for row in csv.DictReader(f)}
    streaks = {name: previous.get(name, 0) + 1 for name in failed}
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["company", "days"])
        writer.writerows(sorted(streaks.items()))
    return streaks


def save_summary(path, today, companies, rows, matches, new_today, dropped, failed, streaks):
    """Today's counts per company, for a quick look at what worked."""
    open_by = collections.Counter(r["company"] for r in rows)
    match_by = collections.Counter(r["company"] for r in matches)
    new_by = collections.Counter(r["company"] for r in new_today)
    out = [["section", "name", "board", "open_jobs", "matches", "new_today", "note"],
           ["run", "Last refresh", "", "", "", "", today.isoformat()],
           ["total", "All companies", "", len(rows), len(matches), len(new_today),
            f"{len(companies)} companies, {len(dropped)} dropped by a rule"]]
    for cfg in companies:
        name = cfg["name"]
        note = ""
        if cfg["board"] == NOT_READ_YET:
            note = "Own careers site; no reader built yet"
        elif name in failed:
            days = streaks.get(name, 1)
            note = (f"Board failed {days} days in a row; showing the last jobs it gave" if days > 1
                    else "Board failed today; showing yesterday's jobs")
        elif not open_by[name]:
            note = "No jobs read; check the board name in companies.toml"
        out.append(["company", name, cfg["board"], open_by[name], match_by[name], new_by[name], note])
    for name, n in collections.Counter(m["why"].split(":")[0] for m in matches).most_common():
        out.append(["matched by", name, "", "", n, "", ""])
    for name, n in collections.Counter(d["filtered_reason"].split(":")[0] for d in dropped).most_common():
        out.append(["dropped by", name, "", "", n, "", ""])
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(out)


if __name__ == "__main__":
    main()
