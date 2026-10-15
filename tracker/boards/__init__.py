"""One reader per job-board type. Each has collect(company, cfg, today) -> every open job,
and describe(row) -> job description when the list doesn't include it."""

from tracker.boards import (amazon, apple, ashby, avature, eightfold, eightfold_v2, google, greenhouse, jibe, lever,
                            oracle, smartrecruiters, successfactors, teamtailor, workable, workday)

READERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workday": workday,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "amazon": amazon,
    "apple": apple,
    "google": google,
    "eightfold": eightfold,
    "eightfold_v2": eightfold_v2,
    "jibe": jibe,
    "oracle": oracle,
    "avature": avature,
    "teamtailor": teamtailor,
    "successfactors": successfactors,
}


def describe(row):
    """The full job description, reading the job's own page when the list didn't include it."""
    if row.get("description"):
        return row["description"]
    reader = READERS[row["board"]]
    return reader.describe(row) if hasattr(reader, "describe") and row.get("detail") else ""
