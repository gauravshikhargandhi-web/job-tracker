"""Small helpers shared by the board readers."""

import html
import json
import re
import time
import urllib.error
import urllib.request

USER_AGENT = "Mozilla/5.0 (compatible; job-tracker; personal job search, one request per board per day)"

# A few career sites only answer browsers.
BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126 Safari/537.36"}

RETRY_WAIT = 30  # seconds before trying a board again after a server error
RATE_LIMIT_WAITS = [30]  # a site that says "too many requests" (429) gets one more try; longer waits did not help


def fetch(url, data=None, headers=None, timeout=60):
    """Download a URL and return its bytes. Pass data (bytes) to POST.

    A server error (HTTP 5xx) is often a passing hiccup, so it is tried once more after a short wait.
    A rate limit (429) is tried once more too.
    """
    request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
    waits = [RETRY_WAIT]
    for attempt in range(len(RATE_LIMIT_WAITS) + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as error:
            if error.code == 429:
                waits = RATE_LIMIT_WAITS
            elif error.code < 500:
                raise
            if attempt >= len(waits):
                raise
            time.sleep(waits[attempt])


def get_json(url, body=None, browser=False):
    """GET a URL as JSON, or POST body (a dict) as JSON and read the JSON answer."""
    headers = {**(BROWSER if browser else {}), "Accept": "application/json"}
    if body is None:
        return json.loads(fetch(url, headers=headers))
    data = json.dumps(body).encode()
    return json.loads(fetch(url, data=data, headers={**headers, "Content-Type": "application/json"}))


def clean(text):
    """Strip HTML tags and entities and collapse whitespace.

    Greenhouse escapes its HTML once more, so entities are decoded before and after the tags go.
    """
    text = html.unescape(text or "")
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\s*\n\s*", "\n", text).strip()


def day(value):
    """ISO timestamp, epoch milliseconds or 'October 10, 2026' -> 'YYYY-MM-DD'; blank if unknown."""
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        return time.strftime("%Y-%m-%d", time.gmtime(value / 1000))
    match = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
    if match:
        return match.group(1)
    try:
        return time.strftime("%Y-%m-%d", time.strptime(str(value).strip(), "%B %d, %Y"))
    except ValueError:
        return ""


def get_text(url, browser=False):
    headers = {**BROWSER, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.9"} if browser else None
    return fetch(url, headers=headers).decode("utf-8", "replace")


def seconds_day(value):
    """Epoch seconds -> 'YYYY-MM-DD'."""
    return time.strftime("%Y-%m-%d", time.gmtime(int(value))) if value else ""
