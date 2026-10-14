# Job tracker

A daily list of new jobs at my target companies that fit the roles I want. Same pattern as [glia-funding-tracker](https://github.com/gauravshikhargandhi-web/glia-funding-tracker). No LinkedIn.

Every day at 12:00 UTC a GitHub job:

1. reads each company's public job board (no login),
2. keeps the jobs whose title fits my role words, or whose description asks for a business degree,
3. drops the ones a rule rules out (too junior or senior, factory floor, outside the US, clearance),
4. saves everything as CSV in `data/`, with the jobs that started matching today in `new_today.csv`.

## What's in it

| File | What it holds |
| --- | --- |
| [`data/new_today.csv`](data/new_today.csv) | The jobs that started matching today. This is the daily list. |
| [`data/matches.csv`](data/matches.csv) | Every open job that fits, newest match first |
| [`data/filtered_out.csv`](data/filtered_out.csv) | Jobs that matched but a drop rule ruled out, with the reason |
| [`data/jobs.csv`](data/jobs.csv) | Every open job read from every company |
| [`data/archive/`](data/archive) | Matches that closed, one file per year |
| [`data/summary.csv`](data/summary.csv) | Today's counts per company, and which boards failed |
| [`companies.toml`](companies.toml) | The companies and where each posts jobs |
| [`profile.toml`](profile.toml) | Role words, business degree words, drop rules, areas and search words |

## Columns in matches.csv and new_today.csv

| Column | Values |
| --- | --- |
| matched_on | The day the job first matched |
| area | Chicago, New York, Seattle, Bay Area or Remote when the job is there; blank for elsewhere in the US |
| why | The rule that matched, e.g. `program: technical program manager` or `business_degree: MBA preferred` |
| sponsor | "No sponsorship" when the description says the company won't sponsor a visa |

The first run lists every open match as new. From the second day on, `new_today.csv` holds only the day's new ones.

## Boards

| Board | How it's read |
| --- | --- |
| Greenhouse, Lever, Ashby, Workable | The board's public list, every job with its description |
| Workday, SmartRecruiters, amazon.jobs | Searched with the words in `profile.toml` under `[search]`; job pages are opened only when needed, once per job |
| Own careers sites (`board = "not_yet"`) | Not read yet; each needs its own reader |

If one board fails on a given day, the others still update and that company keeps its previous jobs. The run only shows as failed (and GitHub emails you) once a board has failed 3 days in a row.

To add a company, add a block to `companies.toml`. `python -m tracker.find "Company name"` tries the usual Greenhouse, Lever, Ashby and Workable names.

## Run it on your computer

Needs Python 3.11 or newer, nothing to install.

```
python -m tracker.run                 # full run
python -m tracker.run --only Stripe   # one company
python -m unittest discover -s tests -t .
```
