"""Find which job board a company uses by trying the usual board names.

    python -m tracker.find "Standard Bots" "Fluidstack"

Prints each board and name that answers, with its number of open jobs, so the
right lines can be pasted into companies.toml. Workday sites can't be guessed;
copy their address from the careers page instead.
"""

import re
import sys
import urllib.error

from tracker.boards import ashby, greenhouse, lever, workable
from tracker.text import get_json


def guesses(name):
    words = re.findall(r"[a-z0-9]+", name.lower())
    joined = "".join(words)
    return list(dict.fromkeys([joined, "-".join(words), words[0], joined + "inc", joined + "hq", "join" + joined,
                               "fly" + joined, joined + "ai", joined + "jobs", joined + "careers"]))


def try_board(board, slug):
    try:
        if board == "greenhouse":
            return len(get_json(greenhouse.API.format(slug=slug)).get("jobs", []))
        if board == "lever":
            return len(get_json(lever.API.format(slug=slug)))
        if board == "ashby":
            return len(get_json(ashby.API.format(slug=slug)).get("jobs", []))
        if board == "workable":
            return len(get_json(workable.API.format(slug=slug)).get("jobs", []))
    except (urllib.error.URLError, ValueError):
        return None


def main(names):
    for name in names:
        found = False
        for slug in guesses(name):
            for board in ("greenhouse", "lever", "ashby", "workable"):
                count = try_board(board, slug)
                if count:
                    print(f'{name}: board = "{board}", slug = "{slug}"  ({count} open jobs)')
                    found = True
        if not found:
            print(f"{name}: not found on Greenhouse, Lever, Ashby or Workable; check the careers page address")


if __name__ == "__main__":
    main(sys.argv[1:])
