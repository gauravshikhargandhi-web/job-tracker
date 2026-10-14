"""The common job format every board is normalized into."""

FIELDS = [
    "key",          # company:board_id, unique across boards, used to update rows day to day
    "company",      # as written in companies.toml
    "title",
    "location",     # the board's own location text
    "remote",       # Remote, Hybrid, On-site or blank when the board doesn't say
    "department",   # team or department, when the board gives one
    "posted",       # YYYY-MM-DD when the board gives a date
    "link",         # the job page to apply on
    "board",        # greenhouse, lever, ashby, workday, smartrecruiters, workable, amazon
    "found_by",     # the search word that found it, on boards that are searched rather than read in full
    "first_seen",   # first day the tracker saw the job
    "last_seen",    # last day the job was still open
]

# What the tracker learned from the job description, kept so a description is read only once.
CHECK_FIELDS = [
    "description_read",   # Y once the description has been read
    "description_match",  # e.g. "business_degree: MBA preferred"
    "description_drop",   # e.g. "description: security clearance"
    "sponsor",            # "No sponsorship" when the description says so
    "matched_on",         # first day the job matched profile.toml, so new matches are easy to find
]

JOB_FIELDS = FIELDS + CHECK_FIELDS

MATCH_FIELDS = ["matched_on", "company", "title", "area", "location", "remote", "why", "sponsor", "link",
                "posted", "department", "board", "first_seen", "last_seen", "key"]
