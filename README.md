# Job tracker

A daily database of new US jobs at my target companies. Same pattern as [glia-funding-tracker](https://github.com/gauravshikhargandhi-web/glia-funding-tracker). No LinkedIn.

Every day at 12:00 UTC a GitHub job:

1. reads every open job on each company's public job board (no login, no keyword search),
2. keeps the US jobs posted in the last 24 hours (today or yesterday by the site's own date),
3. saves them with their full descriptions to `data/jobs/YYYY-MM-DD.csv`.

Nothing is filtered by role here. A daily Claude report (to be built) reads the day's file and picks what fits, using [`profile.toml`](profile.toml).

## What's in it

| File | What it holds |
| --- | --- |
| `data/jobs/YYYY-MM-DD.csv` | That day's new US jobs: company, title, location, posted date, link and full description |
| [`data/known.csv`](data/known.csv) | Every job ever seen, so each job is saved once |
| [`data/summary.csv`](data/summary.csv) | Today's counts per company, and which boards failed |
| [`companies.toml`](companies.toml) | The companies and where each posts jobs |
| [`profile.toml`](profile.toml) | My role words, business degree words and drop rules, for the Claude report |

**Posting dates.** Most boards give the date in their list. Workday only says "Posted Today" or "Posted 3 Days Ago", so the tracker opens those jobs' pages for the exact date. When a board gives no date for a job, it counts as new on the first day the tracker sees it.

## Boards

| Board | How it's read |
| --- | --- |
| Greenhouse, Lever, Ashby, Workable | The board's public list, every job with its description |
| Workday, SmartRecruiters | The whole list; the pages of new jobs are opened for the description (and, on Workday, the exact date) |
| amazon.jobs, Apple, Google, Microsoft, Starbucks, Kraft Heinz (Eightfold), S&C Electric, UL Solutions (Oracle), Nestlé (SuccessFactors) | Newest first, read back to yesterday; new jobs' pages opened for the description |
| BCG (Eightfold), Rivian (Jibe), Mutares (Teamtailor) | The site's own job list, descriptions included |
| Deloitte, Bain (Avature) | The site's job feed, every page; new jobs' pages give the description and places |
| Alvarez & Marsal, McKinsey, Tesla, mHUB (`board = "not_yet"`) | Not read: their sites block automated reading or aren't job boards |

If one board fails on a given day, the others still update. The run only shows as failed (and GitHub emails you) once a board has failed 3 days in a row.

To add a company, add a block to `companies.toml`. `python -m tracker.find "Company name"` tries the usual Greenhouse, Lever, Ashby and Workable names.

## Run it on your computer

Needs Python 3.11 or newer, nothing to install.

```
python -m tracker.run                 # full run
python -m tracker.run --only Stripe   # one company
python -m unittest discover -s tests -t .
```
