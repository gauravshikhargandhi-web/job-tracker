"""One reader per job-board type. Each has collect(company, cfg, search_words) -> rows,
and describe(row) -> job description when the list doesn't include it."""

from tracker.boards import amazon, ashby, greenhouse, lever, smartrecruiters, workable, workday

READERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workday": workday,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "amazon": amazon,
}


def describe(row):
    """The full job description, reading the job's own page when the list didn't include it."""
    if row.get("description"):
        return row["description"]
    reader = READERS[row["board"]]
    return reader.describe(row) if hasattr(reader, "describe") and row.get("detail") else ""
